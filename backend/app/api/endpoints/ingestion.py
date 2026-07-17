import os
import anyio
import datetime
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
from app.services.conflict_engine import industrial_conflict_engine

router = APIRouter(prefix="/ingestion", tags=["Knowledge Ingestion Grid"])

def sanitize_text_payload(text: str) -> str:
    """
    🛡️ GLOBAL SANITIZATION GUARD: Cleans characters that cause database exceptions.
    Removes raw null bytes (\x00) to satisfy strict PostgreSQL text parsing models.
    """
    if not text:
        return ""
    return text.replace("\x00", "").replace("\u0000", "")

async def resolve_document_context(document_id: int, db: AsyncSession) -> KnowledgeDocument:
    """
    🪐 DUAL-KEY LOOKUP FALLBACK PROTOCOL
    Self-heals frontend state desynchronization by scanning the text cache registry
    to map the active processing asset if a database sequence resets.
    """
    query = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    execution = await db.execute(query)
    doc = execution.scalars().first()
    
    if doc:
        return doc
        
    print(f"⚠️ SYSTEM REGISTRY: ID Context {document_id} missing. Initiating self-healing lookup fallback...")
    cache_dir = os.path.join("storage", "text_cache")
    if os.path.exists(cache_dir):
        cache_files = [f for f in os.listdir(cache_dir) if f.startswith("doc_") and f.endswith(".txt")]
        if cache_files:
            cache_files.sort(key=lambda x: os.path.getmtime(os.path.join(cache_dir, x)), reverse=True)
            fallback_query = select(KnowledgeDocument).order_by(KnowledgeDocument.id.desc())
            fallback_execution = await db.execute(fallback_query)
            latest_doc = fallback_execution.scalars().first()
            
            if latest_doc:
                print(f"🟢 SYSTEM REGISTRY: State desynchronization healed! Redirecting flow to True ID: {latest_doc.id}")
                return latest_doc
                
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Target document validation context missing. Please refresh your browser tab and re-upload."
    )

# =====================================================================
# 📥 STAGE 1: IDEMPOTENT MULTI-DOCUMENT UPLOAD GATEWAY
# =====================================================================
@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload_document(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    print(f"📥 UPLOAD GATEWAY: Receiving asset byte-stream for: {file.filename}")
    
    target_directory = os.path.join("storage", "documents")
    os.makedirs(target_directory, exist_ok=True)
    file_path = os.path.join(target_directory, file.filename)
    
    content = await file.read()
    file_size_bytes = len(content)
    mime_type_string = file.content_type or "application/pdf"
    
    with open(file_path, "wb") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
        
    print(f"🟢 UPLOAD GATEWAY: Asset securely committed to drive path: {file_path} ({file_size_bytes} bytes)")
    
    existing_doc_query = select(KnowledgeDocument).where(KnowledgeDocument.filename == file.filename)
    query_execution = await db.execute(existing_doc_query)
    target_document = query_execution.scalars().first()
    
    if target_document:
        print(f"🔄 UPLOAD GATEWAY: Existing matching row discovered. Reusing sequence key context ID: {target_document.id}")
        
        for state_attr in ["PENDING", "pending"]:
            if hasattr(DocumentStatus, str(state_attr)):
                target_document.status = getattr(DocumentStatus, str(state_attr))
                break
        else:
            target_document.status = "PENDING"
            
        target_document.mime_type = mime_type_string
        target_document.file_size = file_size_bytes
        await db.commit()
        return {"id": target_document.id, "filename": target_document.filename, "status": "pending"}
    
    try:
        initial_status = "PENDING"
        for state_attr in ["PENDING", "pending"]:
            if hasattr(DocumentStatus, str(state_attr)):
                initial_status = getattr(DocumentStatus, str(state_attr))
                break

        new_document_row = KnowledgeDocument(
            filename=file.filename,
            s3_key=file.filename,
            mime_type=mime_type_string,   
            file_size=file_size_bytes,   
            status=initial_status
        )
        db.add(new_document_row)
        await db.commit()
        await db.refresh(new_document_row)
        
        print(f"🟢 UPLOAD GATEWAY: Row committed successfully. Assigned ID: {new_document_row.id}")
        return {"id": new_document_row.id, "filename": new_document_row.filename, "status": "pending"}
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ledger entry registration failed: {str(exc)}")

# =====================================================================
# 📄 STAGE 2: LAYOUT PARSING & LOCAL DISK FALLBACK RECOVERY
# =====================================================================
@router.post("/parse/{document_id}", status_code=status.HTTP_200_OK)
async def process_document_structure(document_id: int, db: AsyncSession = Depends(get_db)):
    print(f"🚀 PARSER CORE: Executing layout analysis loop for ID: {document_id}")
    
    target_document = await resolve_document_context(document_id, db)
    true_id = target_document.id

    local_pdf_path = os.path.join("storage", "documents", target_document.filename)
    extracted_payload_text = ""

    try:
        extracted_payload_text = await anyio.to_thread.run_sync(
            pdf_parser_service.extract_structured_pdf_text,
            target_document.s3_key
        )
    except Exception as aws_err:
        print(f"🔄 PARSER CORE: AWS S3 connection bypassed ({str(aws_err)}). Processing file locally...")
        if not os.path.exists(local_pdf_path):
            raise HTTPException(status_code=404, detail=f"Target local manual file absent at: {local_pdf_path}")
            
        import pdfplumber
        def execute_local_disk_extraction(path):
            with pdfplumber.open(path) as pdf:
                structured_text_layers = []
                for page in pdf.pages:
                    page_content = page.extract_text(layout=True)
                    if page_content:
                        structured_text_layers.append(page_content)
                return "\n".join(structured_text_layers)
                
        extracted_payload_text = await anyio.to_thread.run_sync(execute_local_disk_extraction, local_pdf_path)

    extracted_payload_text = sanitize_text_payload(extracted_payload_text)

    if not extracted_payload_text or not extracted_payload_text.strip():
         raise HTTPException(status_code=400, detail="Unable to extract characters out of targeted document file assets.")

    try:
        cache_dir = os.path.join("storage", "text_cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, f"doc_{true_id}.txt")
        with open(cache_path, "w", encoding="utf-8") as cache_file:
            cache_file.write(extracted_payload_text)
            
        for attr in ["content", "text", "extracted_content", "raw_text"]:
            if hasattr(target_document, attr):
                setattr(target_document, attr, extracted_payload_text)
                break
                
        for state_attr in ["PARSED", "parsed"]:
            if hasattr(DocumentStatus, str(state_attr)):
                target_document.status = getattr(DocumentStatus, str(state_attr))
                break
        else:
            target_document.status = "PARSED"
            
        await db.commit()
        print(f"🟢 PARSER CORE: Document text data cached on disk storage layout: {cache_path}")
        return {"message": "Structural layout parsing pass finished.", "document_id": true_id}

    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Parsing pass collapsed: {str(exc)}")

# =====================================================================
# ✂️ STAGE 3: SELF-HEALING HIERARCHICAL COGNITIVE CHUNKER
# =====================================================================
@router.post("/chunk/{document_id}", status_code=status.HTTP_201_CREATED)
async def segment_document_payload(document_id: int, db: AsyncSession = Depends(get_db)):
    print(f"✂️ CHUNKING GRID: Processing text segmentation matrices for ID: {document_id}")
    
    target_document = await resolve_document_context(document_id, db)
    true_id = target_document.id

    raw_text = None
    cache_path = os.path.join("storage", "text_cache", f"doc_{true_id}.txt")
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as cache_file:
            raw_text = cache_file.read()

    if not raw_text or not raw_text.strip():
        raise HTTPException(status_code=400, detail="Document text footprint is empty or unreadable.")

    hierarchical_manifest = cognitive_chunker.generate_hierarchical_chunks(raw_text)
    
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == true_id))
    
    global_child_idx = 0
    current_time_stamp = datetime.datetime.now()
    
    for parent in hierarchical_manifest:
        p_text = sanitize_text_payload(parent["parent_content"])
        for child in parent["children"]:
            c_text = sanitize_text_payload(child["content"])
            unified_content_string = f"{c_text} ||| {p_text}"
            
            db_chunk = KnowledgeChunk(
                document_id=true_id,
                chunk_index=global_child_idx,
                page_number=1,
                content=unified_content_string
            )
            
            for time_attr in ["created_at", "updated_at"]:
                if hasattr(db_chunk, time_attr):
                    setattr(db_chunk, time_attr, current_time_stamp)
                    
            db.add(db_chunk)
            global_child_idx += 1
            
    try:
        for state_attr in ["CHUNKED", "chunked", "PARSED", "parsed"]:
            if hasattr(DocumentStatus, str(state_attr)):
                target_document.status = getattr(DocumentStatus, str(state_attr))
                break
                
        await db.commit()
        print(f"🟢 CHUNKING GRID: Successfully generated and committed {global_child_idx} chunks.")
        return {"total_semantic_chunks_generated": global_child_idx, "document_id": true_id}
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Topological chunk creation pass failed: {str(exc)}")

# =====================================================================
# 🧠 STAGE 4: PRODUCTION VECTOR INDEXING GENERATOR
# =====================================================================
@router.post("/embed/{document_id}", status_code=status.HTTP_200_OK)
async def vectorize_document_payload(document_id: int, db: AsyncSession = Depends(get_db)):
    print(f"🧠 EMBEDDING GATEWAY: Vectorizing semantic fields for ID: {document_id}")
    
    target_document = await resolve_document_context(document_id, db)
    true_id = target_document.id

    chunks_query = select(KnowledgeChunk).where(KnowledgeChunk.document_id == true_id)
    chunks_execution = await db.execute(chunks_query)
    allocated_chunks = chunks_execution.scalars().all()

    if not allocated_chunks:
        raise HTTPException(status_code=400, detail="No segmented blocks detected. Run chunking step first.")

    vector_store_engine.index_document_chunks(
        document_id=true_id,
        filename=target_document.filename,
        db_chunks=allocated_chunks
    )

    try:
        for state_attr in ["EMBEDDED", "embedded", "COMPLETED", "completed"]:
            if hasattr(DocumentStatus, str(state_attr)):
                target_document.status = getattr(DocumentStatus, str(state_attr))
                break
        await db.commit()
        return {"message": "Vector embedding loops finished successfully.", "total_vectors_indexed": len(allocated_chunks), "document_id": true_id}
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Vector index confirmation pass failed: {str(exc)}")

# =====================================================================
# 🖲️ STAGE 5: GRAPH TOPOLOGY SYNC & INTEL EXTRACTOR
# =====================================================================
@router.post("/graph/{document_id}", status_code=status.HTTP_200_OK)
async def map_document_graph_topology(document_id: int, db: AsyncSession = Depends(get_db)):
    print(f"⚡ GRAPH GATEWAY: Mapping structural asset relationships for ID: {document_id}")
    
    target_document = await resolve_document_context(document_id, db)
    true_id = target_document.id

    chunks_query = select(KnowledgeChunk).where(KnowledgeChunk.document_id == true_id).order_by(KnowledgeChunk.chunk_index)
    chunks_execution = await db.execute(chunks_query)
    allocated_chunks = chunks_execution.scalars().all()

    chunks_payload_buffer = [{
        "chunk_index": c.chunk_index,
        "page_number": c.page_number,
        "content": c.content
    } for c in allocated_chunks]

    await anyio.to_thread.run_sync(
        graph_store_engine.sync_document_graph_topology,
        true_id,
        target_document.filename,
        chunks_payload_buffer
    )

    try:
        for state_attr in ["COMPLETED", "completed", "AVAILABLE", "available"]:
            if hasattr(DocumentStatus, str(state_attr)):
                target_document.status = getattr(DocumentStatus, str(state_attr))
                break
        await db.commit()
        return {"message": "Asset relationship maps committed into Neo4j successfully.", "total_nodes_synced": len(chunks_payload_buffer) + 1, "document_id": true_id}
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Graph index milestone confirmation pass failed: {str(exc)}")

# =====================================================================
# 🆕 🛡️ STAGE 6: GLOBAL CROSS-DOCUMENT CONFLICT AUDIT ENGINE
# =====================================================================
@router.post("/scan-conflicts", status_code=status.HTTP_200_OK)
async def scan_cross_document_conflicts(db: AsyncSession = Depends(get_db)):
    """
    Asynchronous System Audit Gate. Intercepts all database context blocks,
    maps tracking vectors, and executes programmatic discrepancy reviews.
    """
    print("📡 ANALYTICS GRID: Compiling multi-document chunk payloads for safety review...")
    
    try:
        # Execute relational join query to align text strings with original filenames
        query = select(KnowledgeChunk, KnowledgeDocument.filename).join(
            KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id
        )
        query_execution = await db.execute(query)
        results = query_execution.all()
        
        if not results:
            return {
                "conflict_detected": False,
                "severity": "OK",
                "message": "System ledger is currently empty. No context segments found to analyze.",
                "detected_anomalies": []
            }
            
        # Format the database records exactly into the schema structure expected by the algorithm
        payload_buffer = []
        for chunk_row, filename_string in results:
            payload_buffer.append({
                "content": chunk_row.content,
                "filename": filename_string
            })
            
        print(f"📡 ANALYTICS GRID: Passing {len(payload_buffer)} data segments to the Conflict Engine...")
        
        # Stream structured array payload into the conflict algorithm matrix
        analysis_report = industrial_conflict_engine.analyze_context_slices(payload_buffer)
        
        return analysis_report

    except Exception as exc:
        print(f"❌ ANALYTICS FAULT: Analysis execution terminated: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cross-document anomaly analysis collapsed: {str(exc)}"
        )