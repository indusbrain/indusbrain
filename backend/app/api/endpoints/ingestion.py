import os
import uuid
import anyio
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db
from app.models.document import KnowledgeDocument, DocumentStatus
from app.models.chunk import KnowledgeChunk
from app.services.storage import storage_service
from app.services.parser import pdf_parser_service
from app.services.chunker import cognitive_chunker
from app.services.vector_store import vector_store_engine
from app.services.graph_store import graph_store_engine

router = APIRouter(prefix="/ingestion", tags=["Knowledge Ingestion Grid"])

# =====================================================================
# 📥 STAGE 1: IDEMPOTENT MULTI-DOCUMENT UPLOAD GATEWAY
# =====================================================================
@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    print(f"📥 UPLOAD GATEWAY: Receiving asset byte-stream for: {file.filename}")
    
    target_directory = os.path.join("storage", "documents")
    os.makedirs(target_directory, exist_ok=True)
    file_path = os.path.join(target_directory, file.filename)
    
    # Read incoming binary stream
    content = await file.read()
    
    # Force-Flush Disk Synced Write Loop to clear Windows file buffers
    with open(file_path, "wb") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
        
    print(f"🟢 UPLOAD GATEWAY: Asset safely committed to system drive: {file_path}")
    
    # Idempotency Guard: Check if this file has been uploaded previously
    existing_doc_query = select(KnowledgeDocument).where(KnowledgeDocument.filename == file.filename)
    query_execution = await db.execute(existing_doc_query)
    target_document = query_execution.scalars().first()
    
    if target_document:
        print(f"🔄 UPLOAD GATEWAY: Duplicate caught. Reusing existing ledger entity ID: {target_document.id}")
        target_document.status = DocumentStatus.PENDING
        await db.commit()
        return {"id": target_document.id, "filename": target_document.filename, "status": "pending"}
    
    # New File Entry Pass
    try:
        new_document_row = KnowledgeDocument(
            filename=file.filename,
            s3_key=file.filename,
            status=DocumentStatus.PENDING
        )
        db.add(new_document_row)
        await db.commit()
        await db.refresh(new_document_row)
        
        print(f"🟢 UPLOAD GATEWAY: Dynamic entry confirmed inside ledger table. Assigned ID: {new_document_row.id}")
        return {"id": new_document_row.id, "filename": new_document_row.filename, "status": "pending"}
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ledger entry registration failed: {str(exc)}")

# =====================================================================
# 📄 STAGE 2: LAYOUT PARSING & LOCAL TEXT CACHE PRESERVATION
# =====================================================================
@router.post("/parse/{document_id}", status_code=status.HTTP_200_OK)
async def process_document_structure(document_id: int, db: AsyncSession = Depends(get_db)):
    print(f"🚀 PARSER CORE: Executing layout analysis loop for ID: {document_id}")
    
    query = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    query_execution = await db.execute(query)
    target_document = query_execution.scalars().first()

    if not target_document:
        raise HTTPException(status_code=404, detail="Target document context missing from ledger.")

    try:
        # Trigger pdfplumber/Tesseract OCR extraction channel
        extracted_payload_text = await anyio.to_thread.run_sync(
            pdf_parser_service.extract_structured_pdf_text,
            target_document.s3_key
        )
        
        # 🛡️ FIX A: WRITE EXTRACTED PAYLOAD TEXT DIRECTLY TO SYSTEM DRIVE FILE CACHE
        cache_dir = os.path.join("storage", "text_cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, f"doc_{document_id}.txt")
        with open(cache_path, "w", encoding="utf-8") as cache_file:
            cache_file.write(extracted_payload_text)
            
        # FIX B: Dynamically map text to any available column attribute on the object model
        for attr in ["content", "text", "extracted_content", "raw_text"]:
            if hasattr(target_document, attr):
                setattr(target_document, attr, extracted_payload_text)
                break
                
        target_document.status = DocumentStatus.PARSED
        await db.commit()
        
        print(f"🟢 PARSER CORE: Character payload successfully preserved in local cache drive: {cache_path}")
        return {"message": "Structural text pass completed successfully.", "document_id": document_id}

    except Exception as exc:
        target_document.status = DocumentStatus.FAILED
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Parsing pass collapsed: {str(exc)}")

# =====================================================================
# ✂️ STAGE 3: SELF-HEALING HIERARCHICAL COGNITIVE CHUNKER
# =====================================================================
@router.post("/chunk/{document_id}", status_code=status.HTTP_201_CREATED)
async def chunk_document(document_id: int, db: AsyncSession = Depends(get_db)):
    print(f"✂️ CHUNKING GRID: Processing text segmentation matrices for ID: {document_id}")
    
    query = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    query_execution = await db.execute(query)
    target_document = query_execution.scalars().first()

    if not target_document:
        raise HTTPException(status_code=404, detail="Target asset context not found.")

    # Fetch text from the local persistent file cache first
    raw_text = None
    cache_path = os.path.join("storage", "text_cache", f"doc_{document_id}.txt")
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as cache_file:
            raw_text = cache_file.read()

    # Fallback to database reflection or raw file pass if file cache is empty
    if not raw_text:
        for attr in ["content", "text", "extracted_content", "raw_text"]:
            if hasattr(target_document, attr) and getattr(target_document, attr):
                raw_text = getattr(target_document, attr)
                break
                
    if not raw_text:
        # Final programmatic vector text fallback extraction check
        file_path = os.path.join("storage", "documents", target_document.filename)
        if os.path.exists(file_path):
            import pdfplumber
            with pdfplumber.open(file_path) as pdf_canvas:
                text_layers = [p.extract_text(layout=True) for p in pdf_canvas.pages if p.extract_text()]
                raw_text = "\n".join(text_layers)

    if not raw_text or not raw_text.strip():
        raise HTTPException(status_code=400, detail="Document text footprint remains unreadable. Verify Tesseract is running.")

    # Slice text using our Parent-Child Chunking Engine
    hierarchical_manifest = cognitive_chunker.generate_hierarchical_chunks(raw_text)
    
    # Wipe any old pre-existing items to maintain strict dataset sanity
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id))
    
    global_child_idx = 0
    for parent in hierarchical_manifest:
        p_text = parent["parent_content"]
        for child in parent["children"]:
            c_text = child["content"]
            
            # Anchor text blocks together using our explicit relational layout token separator
            unified_content_string = f"{c_text} ||| {p_text}"
            
            db_chunk = KnowledgeChunk(
                document_id=document_id,
                chunk_index=global_child_idx,
                page_number=1,
                content=unified_content_string
            )
            db.add(db_chunk)
            global_child_idx += 1
            
    await db.commit()
    print(f"🟢 CHUNKING GRID: Successfully generated and committed {global_child_idx} segments to SQLite.")
    return {"total_semantic_chunks_generated": global_child_idx}

# =====================================================================
# 🧠 STAGE 4: ADVANCED VECTOR INDEXING GENERATOR
# =====================================================================
@router.post("/embed/{document_id}")
async def embed_document(document_id: int, db: AsyncSession = Depends(get_db)):
    print(f"🧠 EMBEDDING GATEWAY: Vectorizing semantic fields for ID: {document_id}")
    
    query = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    query_execution = await db.execute(query)
    target_document = query_execution.scalars().first()
    
    if not target_document:
        raise HTTPException(status_code=404, detail="Target document context missing.")

    chunks_query = select(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id)
    chunks_execution = await db.execute(chunks_query)
    allocated_chunks = chunks_execution.scalars().all()

    if not allocated_chunks:
        raise HTTPException(status_code=400, detail="No segmented blocks detected. Run chunking step first.")

    # Extract child features and store parents into ChromaDB metadata blocks
    vector_store_engine.index_document_chunks(
        document_id=target_document.id,
        filename=target_document.filename,
        db_chunks=allocated_chunks
    )

    return {"message": "ChromaDB vector embedding persistence loops finished successfully.", "total_vectors_indexed": len(allocated_chunks)}

# =====================================================================
# 🖲️ STAGE 5: GRAPH TOPOLOGY SYNC & INTEL EXTRACTOR
# =====================================================================
@router.post("/graph/{document_id}")
async def map_document_graph_topology(document_id: int, db: AsyncSession = Depends(get_db)):
    print(f"⚡ GRAPH GATEWAY: Mapping structural asset relationships for ID: {document_id}")
    
    query = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    query_execution = await db.execute(query)
    target_document = query_execution.scalars().first()

    if not target_document:
        raise HTTPException(status_code=404, detail="Target document reference missing.")

    chunks_query = select(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id).order_by(KnowledgeChunk.chunk_index)
    chunks_execution = await db.execute(chunks_query)
    allocated_chunks = chunks_execution.scalars().all()

    chunks_payload_buffer = [{
        "chunk_index": c.chunk_index,
        "page_number": c.page_number,
        "content": c.content
    } for c in allocated_chunks]

    # Map entity relationship networks inside Neo4j container
    await anyio.to_thread.run_sync(
        graph_store_engine.sync_document_graph_topology,
        target_document.id,
        target_document.filename,
        chunks_payload_buffer
    )

    return {"message": "Asset relationship maps committed into Neo4j successfully.", "total_nodes_synced": len(chunks_payload_buffer) + 1}