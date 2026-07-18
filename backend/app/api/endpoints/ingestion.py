import os
import anyio
import datetime
import hashlib
import multiprocessing
import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, BackgroundTasks
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
# 🆕 Import the isolated core compute function from our new worker file
from app.services.pdf_worker import extract_single_page_compute_task

router = APIRouter(prefix="/ingestion", tags=["Knowledge Ingestion Grid"])

def sanitize_text_payload(text: str) -> str:
    """Removes C-style null characters to prevent database write errors."""
    if not text:
        return ""
    return text.replace("\x00", "").replace("\u0000", "")

async def resolve_document_context(document_id: int, db: AsyncSession) -> KnowledgeDocument:
    """Dual-key lookup fallback protocol to heal frontend state desynchronization."""
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
# ⚙️ OUT-OF-BAND BACKGROUND PIPELINE COORDINATOR WORKER
# =====================================================================
async def orchestrate_background_ingestion(document_id: int, file_path: str, filename: str):
    print(f"📡 BACKGROUND PIPELINE: Initializing core task processing array for ID: {document_id}")
    
    async for db in get_db():
        query = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
        execution = await db.execute(query)
        target_document = execution.scalars().first()
        
        if not target_document:
            print(f"❌ BACKGROUND FAULT: Trace target missing for ID {document_id}")
            return

        try:
            for state_attr in ["PARSED", "parsed"]:
                if hasattr(DocumentStatus, str(state_attr)):
                    target_document.status = getattr(DocumentStatus, str(state_attr))
                    break
            await db.commit()
            
            if not os.path.exists(file_path):
                print(f"❌ BACKGROUND FAULT: Target storage asset absent at: {file_path}")
                target_document.status = getattr(DocumentStatus, "FAILED") if hasattr(DocumentStatus, "FAILED") else "FAILED"
                await db.commit()
                return
                
            # --- STAGE 2: PARSE CONCURRENTLY ---
            import fitz
            total_pages = 0
            with fitz.open(file_path) as doc:
                total_pages = len(doc)
                
            print(f"🚀 MULTI-CORE WORKER: Slicing {total_pages} pages across system cores...")
            
            cpu_cores = multiprocessing.cpu_count()
            target_workers = max(1, cpu_cores - 2)
            
            task_arguments = [(file_path, idx, document_id) for idx in range(total_pages)]
            
            with ProcessPoolExecutor(max_workers=target_workers) as pool:
                native_loop = asyncio.get_running_loop()
                asyncio_tasks = [
                    native_loop.run_in_executor(pool, extract_single_page_compute_task, arg)
                    for arg in task_arguments
                ]
                extracted_pages_list = await asyncio.gather(*asyncio_tasks)
                
            compiled_raw_text = "\n".join(extracted_pages_list)
            compiled_raw_text = sanitize_text_payload(compiled_raw_text)
            
            if not compiled_raw_text.strip():
                raise ValueError("Extraction engines returned an empty text footprint.")
                
            cache_dir = os.path.join("storage", "text_cache")
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, f"doc_{document_id}.txt")
            with open(cache_path, "w", encoding="utf-8") as cache_file:
                cache_file.write(compiled_raw_text)
                
            for attr in ["content", "text", "extracted_content", "raw_text"]:
                if hasattr(target_document, attr):
                    setattr(target_document, attr, compiled_raw_text)
                    break
                    
            await db.commit()
            print(f"🟢 STAGE 2 SUCCESS: Character cache locked on hard disk drive layout: {cache_path}")
            
            # --- STAGE 3: COGNITIVE CHUNKER FRAGMENTATION ---
            hierarchical_manifest = cognitive_chunker.generate_hierarchical_chunks(compiled_raw_text)
            await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id))
            
            global_child_idx = 0
            current_time_stamp = datetime.datetime.now()
            allocated_chunks_models = []
            
            for parent in hierarchical_manifest:
                p_text = sanitize_text_payload(parent["parent_content"])
                for child in parent["children"]:
                    c_text = sanitize_text_payload(child["content"])
                    unified_content_string = f"{c_text} ||| {p_text}"
                    
                    db_chunk = KnowledgeChunk(
                        document_id=document_id,
                        chunk_index=global_child_idx,
                        page_number=1,
                        content=unified_content_string
                    )
                    for time_attr in ["created_at", "updated_at"]:
                        if hasattr(db_chunk, time_attr):
                            setattr(db_chunk, time_attr, current_time_stamp)
                            
                    db.add(db_chunk)
                    allocated_chunks_models.append(db_chunk)
                    global_child_idx += 1
                    
            for state_attr in ["CHUNKED", "chunked", "PARSED", "parsed"]:
                if hasattr(DocumentStatus, str(state_attr)):
                    target_document.status = getattr(DocumentStatus, str(state_attr))
                    break
                    
            await db.commit()
            print(f"🟢 STAGE 3 SUCCESS: Created {global_child_idx} contextual text data segments.")
            
            # --- STAGE 4: VECTOR SPACE RE-INDEXING (ChromaDB) ---
            vector_store_engine.index_document_chunks(
                document_id=document_id,
                filename=filename,
                db_chunks=allocated_chunks_models
            )
            
            for state_attr in ["EMBEDDED", "embedded", "COMPLETED", "completed"]:
                if hasattr(DocumentStatus, str(state_attr)):
                    target_document.status = getattr(DocumentStatus, str(state_attr))
                    break
                    
            await db.commit()
            print("🟢 STAGE 4 SUCCESS: Mathematical vectors successfully pushed to ChromaDB.")
            
            # --- STAGE 5: GRAPH TOPOLOGY SYNC (Neo4j) ---
            chunks_payload_buffer = [{
                "chunk_index": c.chunk_index,
                "page_number": c.page_number,
                "content": c.content
            } for c in allocated_chunks_models]
            
            await anyio.to_thread.run_sync(
                graph_store_engine.sync_document_graph_topology,
                document_id,
                filename,
                chunks_payload_buffer
            )
            
            # 🎯 THE FIX: Since 'EMBEDDED' is the maximum status string allowed by your
            # PostgreSQL schema custom type, we keep it as EMBEDDED to signify total 
            # pipeline completion across both ChromaDB and Neo4j systems.
            for state_attr in ["EMBEDDED", "embedded"]:
                if hasattr(DocumentStatus, str(state_attr)):
                    target_document.status = getattr(DocumentStatus, str(state_attr))
                    break
            else:
                try:
                    target_document.status = "EMBEDDED"
                except Exception:
                    pass
                    
            await db.commit()
            print(f"🏆 BACKGROUND PIPELINE MASTER MATCH: Document {filename} completely ingested successfully!")
            
        except Exception as pipeline_err:
            await db.rollback()
            for state_attr in ["FAILED", "failed"]:
                if hasattr(DocumentStatus, str(state_attr)):
                    target_document.status = getattr(DocumentStatus, str(state_attr))
                    break
            else:
                target_document.status = "FAILED"
            await db.commit()
            print(f"❌ BACKGROUND PIPELINE COLLAPSED: Fatal processing rollback for file {filename}: {str(pipeline_err)}")
        break

# =====================================================================
# 📥 STAGE 1: ASYNC BULK STREAMING UPLOAD ENDPOINT (RAM-DEFENDED)
# =====================================================================
@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_multiple_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...), 
    db: AsyncSession = Depends(get_db)
):
    print(f"📥 UPLOAD GATEWAY: Received array injection containing {len(files)} target file assets.")
    response_manifest = []
    tasks_to_schedule = []
    
    safe_pending_status = "PENDING"
    for state_attr in ["PENDING", "pending"]:
        if hasattr(DocumentStatus, str(state_attr)):
            safe_pending_status = getattr(DocumentStatus, str(state_attr))
            break

    for file in files:
        target_directory = os.path.join("storage", "documents")
        os.makedirs(target_directory, exist_ok=True)
        file_path = os.path.join(target_directory, file.filename)
        
        file_size_bytes = 0
        sha256_hasher = hashlib.sha256()
    
    for file in files:
        target_directory = os.path.join("storage", "documents")
        os.makedirs(target_directory, exist_ok=True)
        # 🎯 THE FIX: Enforce the existence of the static assets folder directory
        os.makedirs("static", exist_ok=True) 
        
        file_path = os.path.join(target_directory, file.filename)
        
        try:
            with open(file_path, "wb") as buffer_drive:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    file_size_bytes += len(chunk)
                    sha256_hasher.update(chunk)
                    buffer_drive.write(chunk)
                
                buffer_drive.flush()
                os.fsync(buffer_drive.fileno())
        except Exception as stream_err:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=f"Socket streaming buffer crash: {str(stream_err)}")
            
        mime_type_string = file.content_type or "application/pdf"
        
        existing_doc_query = select(KnowledgeDocument).where(KnowledgeDocument.filename == file.filename)
        query_execution = await db.execute(existing_doc_query)
        target_document = query_execution.scalars().first()
        
        if target_document:
            print(f"🔄 IDEMPOTENCY GUARD: Duplicate caught for {file.filename}. Re-queuing active key ID: {target_document.id}")
            target_document.status = safe_pending_status
            target_document.file_size = file_size_bytes
            target_document.mime_type = mime_type_string
            
            tasks_to_schedule.append((target_document.id, file_path, file.filename))
            response_manifest.append({"id": target_document.id, "filename": file.filename, "status": "PENDING"})
            continue
            
        try:
            new_document_row = KnowledgeDocument(
                filename=file.filename,
                s3_key=file.filename,
                mime_type=mime_type_string,   
                file_size=file_size_bytes,   
                status=safe_pending_status
            )
            db.add(new_document_row)
            await db.flush()  
            
            tasks_to_schedule.append((new_document_row.id, file_path, file.filename))
            response_manifest.append({"id": new_document_row.id, "filename": file.filename, "status": "PENDING"})
        except Exception as exc:
            print(f"❌ DATABASE INSERTION FAULT: {str(exc)}")
            raise HTTPException(status_code=500, detail=f"Ledger registration failed: {str(exc)}")
            
    try:
        await db.commit()
    except Exception as commit_exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database transaction commit failed: {str(commit_exc)}")
        
    for doc_id, f_path, f_name in tasks_to_schedule:
        background_tasks.add_task(orchestrate_background_ingestion, doc_id, f_path, f_name)
        
    return {"message": "Bulk transmission accepted. Background processing pipelines triggered.", "queue_manifest": response_manifest}

# =====================================================================
# 📊 LIVE PROCESSING STATE MONITOR API ROUTE
# =====================================================================
@router.get("/status/{document_id}", status_code=status.HTTP_200_OK)
async def fetch_document_processing_status(document_id: int, db: AsyncSession = Depends(get_db)):
    query = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    execution = await db.execute(query)
    doc = execution.scalars().first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Requested asset missing from historical registers.")
        
    # 🎯 THE FIX: Use .value or .name to extract pure text strings (e.g. "PENDING") 
    # instead of stringifying the raw Enum object context wrapper
    stage_string = doc.status.value if hasattr(doc.status, "value") else str(doc.status)
    if "DocumentStatus." in stage_string:
        stage_string = stage_string.replace("DocumentStatus.", "")

    return {
        "id": doc.id,
        "filename": doc.filename,
        "current_pipeline_stage": stage_string,
        "file_size_bytes": doc.file_size,
        "last_updated": datetime.datetime.now().isoformat()
    }

# =====================================================================
# 🛡️ GLOBAL CROSS-DOCUMENT CONFLICT AUDIT ENGINE
# =====================================================================
@router.post("/scan-conflicts", status_code=status.HTTP_200_OK)
async def scan_cross_document_conflicts(db: AsyncSession = Depends(get_db)):
    print("📡 ANALYTICS GRID: Compiling multi-document chunk payloads for safety review...")
    try:
        query = select(KnowledgeChunk, KnowledgeDocument.filename).join(
            KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id
        )
        query_execution = await db.execute(query)
        results = query_execution.all()
        
        if not results:
            return {"conflict_detected": False, "severity": "OK", "detected_anomalies": []}
            
        payload_buffer = []
        for chunk_row, filename_string in results:
            payload_buffer.append({"content": chunk_row.content, "filename": filename_string})
            
        analysis_report = industrial_conflict_engine.analyze_context_slices(payload_buffer)
        return analysis_report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Cross-document anomaly analysis collapsed: {str(exc)}")