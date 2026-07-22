import os
import re
import anyio
import datetime
import subprocess
import asyncio
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db
from app.security import Permission, require
from app.models.document import KnowledgeDocument, DocumentStatus
from app.models.chunk import KnowledgeChunk
from app.services.parser import pdf_parser_service
from app.services.chunker import cognitive_chunker

router = APIRouter(prefix="/ingestion", tags=["Knowledge Ingestion Grid"])

# ---------------------------------------------------------------------------
# Ingestion concurrency limits
#
# Two independent limits, because a batch upload multiplies them together:
#   PAGE_WORKER_LIMIT     - threads extracting pages WITHIN one document
#   DOCUMENT_CONCURRENCY  - documents being ingested AT THE SAME TIME
#
# Without the second limit, uploading N files started N full pipelines at once,
# each competing for memory with the embedding and reranking models already
# resident in the parent process.
# ---------------------------------------------------------------------------
PAGE_WORKER_LIMIT = int(os.getenv("INGEST_PAGE_WORKERS", "8"))
DOCUMENT_CONCURRENCY = int(os.getenv("INGEST_DOCUMENT_CONCURRENCY", "2"))

_document_ingestion_semaphore = asyncio.Semaphore(DOCUMENT_CONCURRENCY)

def extract_single_page_compute_task(args: tuple) -> str:
    file_path, page_idx, document_id = args
    page_text = ""
    try:
        import fitz
        with fitz.open(file_path) as doc:
            if page_idx < len(doc):
                page_text = doc[page_idx].get_text("text")
    except Exception:
        pass
    if not page_text or not page_text.strip():
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                if page_idx < len(pdf.pages):
                    page_text = pdf.pages[page_idx].extract_text()
        except Exception:
            pass
    if not page_text or not page_text.strip():
        # Resolved centrally so every OCR entry point agrees on one binary.
        # This runs inside a ProcessPoolExecutor worker, so the import must happen
        # here rather than being inherited from the parent process.
        from app.services.ocr_config import resolve_tesseract_binary
        resolved_binary = resolve_tesseract_binary()
        tess_executables = [resolved_binary] if resolved_binary else []
        temp_dir = os.path.join("storage", "temp_ocr")
        os.makedirs(temp_dir, exist_ok=True)
        try:
            import fitz
            with fitz.open(file_path) as doc:
                if page_idx < len(doc):
                    page = doc[page_idx]
                    pix = page.get_pixmap(dpi=150)
                    tmp_img_path = os.path.join(temp_dir, f"mp_{document_id}_{page_idx}.png")
                    pix.save(tmp_img_path)
                    out_base_path = os.path.join(temp_dir, f"txt_{document_id}_{page_idx}")
                    for exe in tess_executables:
                        try:
                            subprocess.run(
                                [exe, tmp_img_path, out_base_path],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, timeout=25, check=True
                            )
                            txt_file = out_base_path + ".txt"
                            if os.path.exists(txt_file):
                                with open(txt_file, "r", encoding="utf-8") as f:
                                    page_text = f.read()
                                os.remove(txt_file)
                                break
                        except Exception:
                            continue
                    if os.path.exists(tmp_img_path):
                        os.remove(tmp_img_path)
        except Exception:
            pass
    return page_text if page_text else ""

def count_pdf_pages(file_path: str) -> int:
    """
    Returns the page count using PyMuPDF, falling back to pdfplumber.
    Returns 0 only if the file cannot be opened by either engine.
    """
    try:
        import fitz
        with fitz.open(file_path) as doc:
            return len(doc)
    except Exception as mupdf_error:
        print(f"⚠️ PAGE COUNT: PyMuPDF unavailable or failed ({mupdf_error}). Trying pdfplumber...")

    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            return len(pdf.pages)
    except Exception as plumber_error:
        print(f"🚨 PAGE COUNT: pdfplumber also failed ({plumber_error}).")

    return 0


def sanitize_text_payload(text: str) -> str:
    if not text: return ""
    return text.replace("\x00", "").replace("\u0000", "")

async def orchestrate_background_ingestion(document_id: int, file_path: str, filename: str):
    """Ingests one document. Bounded so a batch upload cannot swamp the process."""
    async with _document_ingestion_semaphore:
        await _ingest_single_document(document_id, file_path, filename)


async def _ingest_single_document(document_id: int, file_path: str, filename: str):
    print(f"📡 BACKGROUND PIPELINE: Initializing core task processing array for ID: {document_id}")
    async for db in get_db():
        query = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
        execution = await db.execute(query)
        target_document = execution.scalars().first()
        if not target_document: return
        try:
            target_document.status = DocumentStatus.PARSED
            await db.commit()
            if not os.path.exists(file_path):
                target_document.status = DocumentStatus.FAILED
                await db.commit()
                return
            # Page count drives the parallel extraction fan-out. PyMuPDF is the fast
            # path, but we must not hard-fail the whole ingestion if it is absent -
            # pdfplumber can count pages too, and the per-page workers have their
            # own independent cascade.
            total_pages = count_pdf_pages(file_path)
            if total_pages <= 0:
                raise ValueError("Could not determine the page count for this PDF.")
            # PAGE EXTRACTION FAN-OUT
            #
            # This previously used a ProcessPoolExecutor sized at (cpu_count - 2)
            # PER DOCUMENT. On a 16-core machine that is 14 processes per file, so
            # a 3-file batch spawned 42 processes - and on Windows each one uses
            # `spawn`, re-importing the entire application. That exhausted memory
            # and file handles, which is why uploads intermittently FAILED, and it
            # is also how orphaned workers ended up holding the server's socket.
            #
            # Threads are the right tool here: PyMuPDF releases the GIL during page
            # rendering and text extraction, and the OCR fallback shells out to a
            # subprocess. We get the parallelism without duplicating the process.
            task_arguments = [(file_path, idx, document_id) for idx in range(total_pages)]
            worker_count = min(PAGE_WORKER_LIMIT, max(1, total_pages))

            with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="pdf-page") as pool:
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
                        document_id=document_id, chunk_index=global_child_idx,
                        page_number=1, content=unified_content_string
                    )
                    for time_attr in ["created_at", "updated_at"]:
                        if hasattr(db_chunk, time_attr):
                            setattr(db_chunk, time_attr, current_time_stamp)
                    db.add(db_chunk)
                    allocated_chunks_models.append(db_chunk)
                    global_child_idx += 1
            await db.commit()
            from app.services.vector_store import vector_store_engine
            vector_store_engine.index_document_chunks(document_id=document_id, filename=filename, db_chunks=allocated_chunks_models)
            from app.services.graph_store import graph_store_engine
            chunks_payload_buffer = [{"chunk_index": c.chunk_index, "page_number": c.page_number, "content": c.content} for c in allocated_chunks_models]
            if graph_store_engine.is_online:
                await anyio.to_thread.run_sync(graph_store_engine.sync_document_graph_topology, document_id, filename, chunks_payload_buffer)
            else:
                # Do not fail the whole ingestion - vector search still works. But say so
                # loudly, and expose /reindex-graph so this can be repaired without
                # re-uploading the document.
                print(
                    f"🚨 GRAPH SYNC SKIPPED for document {document_id}: Neo4j was unreachable. "
                    f"Vector search will work but graph retrieval will be degraded. "
                    f"Run POST /api/v1/ingestion/reindex-graph once Neo4j is up."
                )
            # EMBEDDED is the terminal success state: text extracted, chunks written,
            # vectors indexed in Chroma and topology synced into Neo4j.
            target_document.status = DocumentStatus.EMBEDDED
            await db.commit()

            # Make the new document visible on the dashboard immediately rather
            # than waiting for the cache window to expire.
            from app.api.endpoints.telemetry_dashboard import invalidate_dashboard_cache
            invalidate_dashboard_cache()

            print(f"✅ BACKGROUND PIPELINE: Document {document_id} fully ingested ({global_child_idx} chunks).")
        except Exception as e:
            # Record WHY a document failed instead of silently swallowing it -
            # otherwise a failed upload is undiagnosable from the dashboard.
            print(f"🚨 INGESTION FAILURE for document {document_id}: {type(e).__name__}: {e}")
            traceback.print_exc()
            await db.rollback()
            target_document.status = DocumentStatus.FAILED
            await db.commit()
        break

@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require(Permission.UPLOAD_DOCUMENTS))],
)
async def upload_multiple_documents(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...), db: AsyncSession = Depends(get_db)):
    response_manifest = []
    tasks_to_schedule = []
    safe_pending_status = DocumentStatus.PENDING
    for target_file in files:
        target_directory = os.path.join("storage", "documents")
        os.makedirs(target_directory, exist_ok=True)
        file_path = os.path.join(target_directory, target_file.filename)
        file_size_bytes = 0
        try:
            with open(file_path, "wb") as buffer_drive:
                while True:
                    chunk = await target_file.read(1024 * 1024)
                    if not chunk: break
                    file_size_bytes += len(chunk)
                    buffer_drive.write(chunk)
                buffer_drive.flush()
        except Exception as stream_err:
            if os.path.exists(file_path): os.remove(file_path)
            raise HTTPException(status_code=500, detail=str(stream_err))
        mime_type_string = target_file.content_type or "application/pdf"
        existing_doc_query = select(KnowledgeDocument).where(KnowledgeDocument.filename == target_file.filename)
        query_execution = await db.execute(existing_doc_query)
        target_document = query_execution.scalars().first()
        if target_document:
            target_document.status = safe_pending_status
            target_document.file_size = file_size_bytes
            tasks_to_schedule.append((target_document.id, file_path, target_file.filename))
            response_manifest.append({"id": target_document.id, "filename": target_file.filename, "status": "PENDING"})
            continue
        try:
            local_s3_key_placeholder = f"local://storage/documents/{target_file.filename}"
            new_document_row = KnowledgeDocument(
                filename=target_file.filename, s3_key=local_s3_key_placeholder,
                mime_type=mime_type_string, file_size=file_size_bytes, status=safe_pending_status
            )
            db.add(new_document_row)
            await db.flush()  
            tasks_to_schedule.append((new_document_row.id, file_path, target_file.filename))
            response_manifest.append({"id": new_document_row.id, "filename": target_file.filename, "status": "PENDING"})
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
    await db.commit()
    for doc_id, f_path, f_name in tasks_to_schedule:
        background_tasks.add_task(orchestrate_background_ingestion, doc_id, f_path, f_name)
    return {"message": "Bulk transmission accepted.", "queue_manifest": response_manifest}

@router.get(
    "/document/{document_id}/file",
    dependencies=[Depends(require(Permission.VIEW_DOCUMENTS))],
)
async def serve_document_file(
    document_id: int, download: bool = False, db: AsyncSession = Depends(get_db)
):
    """
    Streams the original PDF so it can be read inside IndusBrain.

    `inline` lets the browser render it in an embedded viewer; `?download=true`
    switches to `attachment` to save it instead. Serving from the stored path
    rather than a client-supplied one prevents path traversal.
    """
    from fastapi.responses import FileResponse

    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == document_id))
    document = result.scalars().first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Resolve from the stored filename only, then confirm the result is still
    # inside the documents directory.
    documents_root = os.path.abspath(os.path.join("storage", "documents"))
    file_path = os.path.abspath(os.path.join(documents_root, os.path.basename(document.filename)))
    if not file_path.startswith(documents_root + os.sep):
        raise HTTPException(status_code=400, detail="Invalid document path.")

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"The source file for '{document.filename}' is no longer on disk.",
        )

    disposition = "attachment" if download else "inline"
    return FileResponse(
        file_path,
        media_type=document.mime_type or "application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{os.path.basename(document.filename)}"'
        },
    )


@router.get(
    "/document/{document_id}/detail",
    dependencies=[Depends(require(Permission.VIEW_DOCUMENTS))],
)
async def document_detail(document_id: int, db: AsyncSession = Depends(get_db)):
    """
    Metadata plus the extracted passages for one document, so its content can be
    inspected inside the app without opening the PDF.
    """
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == document_id))
    document = result.scalars().first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    chunk_result = await db.execute(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.document_id == document_id)
        .order_by(KnowledgeChunk.chunk_index)
    )
    chunks = chunk_result.scalars().all()

    file_path = os.path.join("storage", "documents", os.path.basename(document.filename))

    passages = []
    for chunk in chunks:
        raw = chunk.content or ""
        # Chunks are stored as "child ||| parent"; show the child, which is the
        # precise passage that gets matched during retrieval.
        child = raw.split(" ||| ", 1)[0] if " ||| " in raw else raw
        passages.append({
            "chunk_index": chunk.chunk_index,
            "page_number": chunk.page_number,
            "text": child.strip(),
        })

    return {
        "id": document.id,
        "filename": document.filename,
        "status": str(document.status).split(".")[-1].upper(),
        "mime_type": document.mime_type,
        "file_size": document.file_size,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        "chunk_count": len(passages),
        "file_available": os.path.exists(file_path),
        "passages": passages,
    }


@router.post(
    "/retry/{document_id}",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require(Permission.UPLOAD_DOCUMENTS))],
)
async def retry_failed_ingestion(
    document_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)
):
    """
    Re-runs ingestion for a document that previously failed.

    The uploaded file is kept on disk, so a retry never requires the user to
    locate and re-upload the original.
    """
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == document_id))
    document = result.scalars().first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = os.path.join("storage", "documents", document.filename)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=409,
            detail=(
                f"The source file for '{document.filename}' is no longer on disk, "
                "so it cannot be reprocessed. Please upload it again."
            ),
        )

    document.status = DocumentStatus.PENDING
    await db.commit()

    background_tasks.add_task(orchestrate_background_ingestion, document.id, file_path, document.filename)
    return {"status": "RETRY_QUEUED", "document_id": document.id, "filename": document.filename}


@router.post(
    "/retry-all-failed",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require(Permission.UPLOAD_DOCUMENTS))],
)
async def retry_all_failed(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Queues every FAILED document for reprocessing."""
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.status == DocumentStatus.FAILED)
    )
    failed_documents = result.scalars().all()

    queued, skipped = [], []
    for document in failed_documents:
        file_path = os.path.join("storage", "documents", document.filename)
        if not os.path.exists(file_path):
            skipped.append({"id": document.id, "filename": document.filename, "reason": "source file missing"})
            continue
        document.status = DocumentStatus.PENDING
        background_tasks.add_task(
            orchestrate_background_ingestion, document.id, file_path, document.filename
        )
        queued.append({"id": document.id, "filename": document.filename})

    await db.commit()
    return {"status": "RETRY_QUEUED", "queued": queued, "skipped": skipped}


@router.post(
    "/reindex-graph",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require(Permission.REBUILD_INDEX))],
)
async def rebuild_knowledge_graph(db: AsyncSession = Depends(get_db)):
    """
    Rebuilds the Neo4j knowledge graph from the chunks already stored in Postgres.

    Needed because Neo4j can be unavailable at ingestion time (container still
    starting). Postgres remains the source of truth, so the graph can always be
    reconstructed without re-uploading or re-OCRing anything.
    """
    from app.services.graph_store import graph_store_engine

    if not graph_store_engine.is_online:
        raise HTTPException(
            status_code=503,
            detail="Neo4j is not reachable. Start the graph database and retry.",
        )

    documents_result = await db.execute(select(KnowledgeDocument))
    documents = documents_result.scalars().all()

    rebuilt_manifest = []
    for document in documents:
        chunks_result = await db.execute(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.document_id == document.id)
            .order_by(KnowledgeChunk.chunk_index)
        )
        chunk_rows = chunks_result.scalars().all()
        if not chunk_rows:
            continue

        payload = [
            {"chunk_index": c.chunk_index, "page_number": c.page_number, "content": c.content}
            for c in chunk_rows
        ]
        await anyio.to_thread.run_sync(
            graph_store_engine.sync_document_graph_topology,
            document.id,
            document.filename,
            payload,
        )
        rebuilt_manifest.append({
            "document_id": document.id,
            "filename": document.filename,
            "chunks_synced": len(payload),
        })

    return {
        "status": "REBUILT",
        "documents_processed": len(rebuilt_manifest),
        "manifest": rebuilt_manifest,
    }


@router.get(
    "/status/{document_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require(Permission.VIEW_DOCUMENTS))],
)
async def fetch_document_processing_status(document_id: int, db: AsyncSession = Depends(get_db)):
    query = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    execution = await db.execute(query)
    doc = execution.scalars().first()
    if not doc: raise HTTPException(status_code=404, detail="Requested asset missing.")
    return {"id": doc.id, "filename": doc.filename, "current_pipeline_stage": str(doc.status)}

# =====================================================================
# 🎯 THE FIX: UPGRADED AUTONOMOUS KNOWLEDGE CONFLICT DETECTION ENGINE
# =====================================================================
@router.post(
    "/scan-conflicts",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require(Permission.SCAN_CONFLICTS))],
)
async def scan_cross_document_conflicts(db: AsyncSession = Depends(get_db)):
    """
    Detects genuine cross-document contradictions in the indexed corpus.

    Delegates to the dedicated conflict engine, which only reports a finding when
    two DIFFERENT documents state materially different values for the same
    parameter on the same asset. If nothing conflicts, it returns an empty result
    rather than an illustrative example.
    """
    from app.services.conflict_engine import industrial_conflict_engine

    query = select(KnowledgeChunk.content, KnowledgeDocument.filename).join(
        KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id
    )
    query_execution = await db.execute(query)
    rows = query_execution.all()

    if not rows:
        return {
            "conflict_detected": False,
            "severity": "OK",
            "detected_anomalies": [],
            "chunks_scanned": 0,
            "empty_reason": "No documents have been indexed yet.",
        }

    # Chunks are stored as "child ||| parent"; scan the parent block, which holds
    # the fuller context and therefore the complete parameter statements.
    scan_payload = []
    for content, filename in rows:
        text = content or ""
        if " ||| " in text:
            text = text.split(" ||| ", 1)[1]
        scan_payload.append({"content": text, "filename": filename})

    result = industrial_conflict_engine.analyze_context_slices(scan_payload)

    if not result["detected_anomalies"]:
        result["empty_reason"] = (
            f"Scanned {result['chunks_scanned']} passages across "
            f"{len({r[1] for r in rows})} documents. No contradictory parameter "
            f"values were found between documents."
        )

    return result
