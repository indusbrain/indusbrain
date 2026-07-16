import uuid
import anyio
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.document import KnowledgeDocument, DocumentStatus
from app.schemas.document import DocumentResponse
from app.services.storage import storage_service
from app.services.parser import pdf_parser_service
from app.models.chunk import KnowledgeChunk
from app.services.chunker import cognitive_chunker
from app.services.vector_store import vector_store_engine
from app.services.graph_store import graph_store_engine
import os

router = APIRouter(prefix="/ingestion", tags=["Knowledge Ingestion Grid"])

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # Restrict uploads strictly to 50MB
ALLOWED_MIME_TYPES = ["application/pdf"]

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    print(f"📥 UPLOAD GATEWAY: Receiving asset byte-stream for: {file.filename}")
    
    # 1. Establish your targeted storage path parameters
    target_directory = os.path.join("storage", "documents")
    os.makedirs(target_directory, exist_ok=True)
    file_path = os.path.join(target_directory, file.filename)
    
    # 2. Read incoming binary buffer strings
    content = await file.read()
    
    # 3. Force-Flush Protocol to ensure bytes are fully written to hard disk storage
    with open(file_path, "wb") as f:
        f.write(content)
        f.flush()
        file_descriptor = f.fileno()
        os.fsync(file_descriptor)
        
    print(f"🟢 UPLOAD GATEWAY: Asset securely committed to disk path: {file_path}")
    
    # =====================================================================
    # 🛡️ THE IDEMPOTENT GUARD: Prevents UNIQUE constraint violations (gkpj)
    # =====================================================================
    # Check if this exact file asset has been registered inside SQLite previously
    existing_doc_query = select(KnowledgeDocument).where(KnowledgeDocument.filename == file.filename)
    query_execution = await db.execute(existing_doc_query)
    target_document = query_execution.scalars().first()
    
    if target_document:
        print(f"🔄 UPLOAD GATEWAY: File match identified. Reusing existing row ID: {target_document.id}")
        # Reset the status tracking parameters so it can safely pass through the processing loops again
        target_document.status = DocumentStatus.PENDING
        await db.commit()
        await db.refresh(target_document)
        
        return {
            "id": target_document.id,
            "filename": target_document.filename,
            "status": "pending"
        }
    
    # =====================================================================
    # 🪐 DYNAMIC PASS: Execute fresh row insert for brand-new unique assets
    # =====================================================================
    print("✨ UPLOAD GATEWAY: Launching new dynamic entity registration pass...")
    try:
        new_document_row = KnowledgeDocument(
            filename=file.filename,
            s3_key=file.filename,
            status=DocumentStatus.PENDING
        )
        
        db.add(new_document_row)
        await db.commit()
        await db.refresh(new_document_row)
        
        print(f"🟢 UPLOAD GATEWAY: New row committed successfully. Assigned ID: {new_document_row.id}")
        
        return {
            "id": new_document_row.id,
            "filename": new_document_row.filename,
            "status": "pending"
        }
        
    except Exception as exc:
        await db.rollback()
        print(f"❌ DATABASE COMPILATION FAULT: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Structural ledger initialization failure. Please check terminal console trace logs."
        )

@router.post("/parse/{document_id}", status_code=status.HTTP_200_OK)
async def process_document_structure(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Asynchronous document parsing coordinator path. Retrieves historical 
    metadata rows, maps layout extractors, and transitions ledger states to 'PARSED'.
    """
    # 1. Query the tracking registry for the document target matching our ID parameter
    query = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    query_execution = await db.execute(query)
    target_document = query_execution.scalars().first()

    if not target_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge asset identifier context '{document_id}' is missing from the system."
        )

    # 2. Protect against running the parser twice on an already processed manual
    if target_document.status == DocumentStatus.PARSED:
        return {
            "message": "Asset text data structure already extracted successfully.",
            "document_id": target_document.id,
            "status": target_document.status
        }

    try:
        # 3. Offload the heavy blocking S3 stream parsing processing onto a background thread loop
        extracted_payload_text = await anyio.to_thread.run_sync(
            pdf_parser_service.extract_structured_pdf_text,
            target_document.s3_key
        )
        
        # 4. Transition our ledger index status safely to PARSED state
        target_document.status = DocumentStatus.PARSED
        await db.commit()
        await db.refresh(target_document)

        return {
            "message": "Structural document layout extraction completed successfully.",
            "document_id": target_document.id,
            "status": target_document.status,
            "character_count_processed": len(extracted_payload_text)
        }

    except Exception as exc:
        target_document.status = DocumentStatus.FAILED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Parsing orchestration collapsed: {str(exc)}"
        )
    
@router.post("/chunk/{document_id}", status_code=status.HTTP_201_CREATED)
async def chunk_document(document_id: int, db: AsyncSession = Depends(get_db)):
    print(f"✂️ CHUNKING GATEWAY: Segmenting document context for ID: {document_id}")
    
    # 1. Fetch document reference from SQLite
    document_query = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    document_execution = await db.execute(document_query)
    target_document = document_execution.scalar_one_or_none()
    
    if not target_document:
        raise HTTPException(status_code=404, detail="Target document asset not found.")
    
    # 🛡️ LAYER 1: Dynamic Attribute Scan to look for common text column configurations
    raw_text = None
    for attr in ["content", "text", "extracted_content", "text_content", "raw_text"]:
        if hasattr(target_document, attr) and getattr(target_document, attr):
            raw_text = getattr(target_document, attr)
            break
            
    # 🛡️ LAYER 2: Hard-Disk Fallback Extraction Pass
    if not raw_text:
        file_path = os.path.join("storage", "documents", target_document.filename)
        if os.path.exists(file_path):
            print(f"🔄 PARSER FALLBACK: Re-extracting text layers directly from disk: {file_path}")
            import pdfplumber
            try:
                with pdfplumber.open(file_path) as pdf_canvas:
                    text_layers = [
                        page.extract_text(layout=True) 
                        for page in pdf_canvas.pages 
                        if page.extract_text()
                    ]
                    raw_text = "\n".join(text_layers)
            except Exception as e:
                print(f"❌ Fallback layout extraction failed: {e}")

    if not raw_text or not raw_text.strip():
        raise HTTPException(
            status_code=400, 
            detail="Document text footprint is empty or unreadable. Run layout parsing first."
        )

    # 2. Invoke our hierarchical chunker framework
    from app.services.chunker import cognitive_chunker
    hierarchical_manifest = cognitive_chunker.generate_hierarchical_chunks(raw_text)
    
    # Clean out any old pre-existing chunks to prevent duplicate entries
    from app.models.chunk import KnowledgeChunk
    from sqlalchemy import delete
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id))
    
    # 3. Flatten the hierarchical manifest into database rows
    global_child_index = 0
    for parent_packet in hierarchical_manifest:
        p_content = parent_packet["parent_content"]
        
        for child in parent_packet["children"]:
            c_content = child["content"]
            
            # Combine child and parent blocks using our explicit context separator
            unified_content_string = f"{c_content} ||| {p_content}"
            
            db_chunk = KnowledgeChunk(
                document_id=document_id,
                chunk_index=global_child_index,
                page_number=1,
                content=unified_content_string
            )
            db.add(db_chunk)
            global_child_index += 1
            
    await db.commit()
    print(f"🟢 CHUNKING GATEWAY: Successfully persisted {global_child_index} segments in SQLite.")
    
    return {
        "message": "Hierarchical text segmentation complete.",
        "total_semantic_chunks_generated": global_child_index
    }

@router.post("/embed/{document_id}")
async def embed_document(document_id: int, db: AsyncSession = Depends(get_db)):
    print(f"🧠 EMBEDDING GATEWAY: Beginning vector embedding routines for ID: {document_id}")
    
    # Fetch active document profile details
    document_query = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    document_execution = await db.execute(document_query)
    target_document = document_execution.scalar_one_or_none()
    
    if not target_document:
        raise HTTPException(status_code=404, detail="Target document profile missing.")

    # Fetch all segmented chunks associated with this document from SQLite
    chunks_query = select(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id)
    chunks_execution = await db.execute(chunks_query)
    allocated_chunks = chunks_execution.scalars().all()

    if not allocated_chunks:
        raise HTTPException(status_code=400, detail="No chunks found. Process chunking step first.")

    # Pass rows to our vector engine to compile and persist the indices
    vector_store_engine.index_document_chunks(
        document_id=target_document.id,
        filename=target_document.filename,
        db_chunks=allocated_chunks
    )

    return {
        "message": "ChromaDB vector embedding persistence routines finished successfully.",
        "total_vectors_indexed": len(allocated_chunks)
    }

@router.post("/graph/{document_id}", status_code=status.HTTP_200_OK)
async def map_document_graph_topology(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Asynchronous Graph Ingestion Gate. Pulls segmented text components from disk, 
    maps relational nodes, and loads structural topologies cleanly into Neo4j.
    """
    # 1. Verify existence parameters within our metadata ledger
    query = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    query_execution = await db.execute(query)
    target_document = query_execution.scalars().first()

    if not target_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target knowledge document validation context '{document_id}' is missing."
        )

    # 2. Enforce strict sequential pipeline rules
    if target_document.status == DocumentStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset text must pass parsing and chunking before graph topology mapping can run."
        )

    # 3. Fetch all context segments allocated to this file reference
    chunks_query = select(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id).order_by(KnowledgeChunk.chunk_index)
    chunks_execution = await db.execute(chunks_query)
    allocated_chunks = chunks_execution.scalars().all()

    try:
        chunks_payload_buffer = [{
            "chunk_index": c.chunk_index,
            "page_number": c.page_number,
            "content": c.content
        } for c in allocated_chunks]

        # 4. Offload graph network data transfers to our background worker threads
        await anyio.to_thread.run_sync(
            graph_store_engine.sync_document_graph_topology,
            target_document.id,
            target_document.filename,
            chunks_payload_buffer
        )

        return {
            "message": "Asset structural relationship nodes committed into Neo4j successfully.",
            "document_id": target_document.id,
            "total_nodes_synced": len(chunks_payload_buffer) + 1  # Chunks count + 1 Parent Document Node
        }

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph store mapping coordination collapsed: {str(exc)}"
        )