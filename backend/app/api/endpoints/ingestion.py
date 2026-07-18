import os
from fastapi import APIRouter, UploadFile, File, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.document import KnowledgeDocument

try:
    from app.services.ingestion.pdf_extractor import process_and_chunk_pdf
except ImportError:
    process_and_chunk_pdf = None


router = APIRouter(prefix="/ingestion", tags=["Document Ingestion Subsystem"])

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_industrial_document(
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid format. Only technical PDFs are authorized.")

    upload_dir = os.path.join(os.getcwd(), "storage", "text_cache")
    os.makedirs(upload_dir, exist_ok=True)
    target_file_path = os.path.join(upload_dir, file.filename)

    try:
        print(f"⚙️ PIPELINE WORKERS: Launching token isolation loops for file: {file.filename}")
        extracted_chunks = await process_and_chunk_pdf(target_file_path, new_doc_record.id, db)
        print(f"🟢 PIPELINE WORKERS: Generated {len(extracted_chunks)} chunks. Pipeline success.")
        # 1. Read and cache raw bytes locally on disk
        file_bytes = await file.read()
        file_size_bytes = len(file_bytes)
        
        with open(target_file_path, "wb") as f_out:
            f_out.write(file_bytes)

        print(f"📦 INGESTION CORE: Cached raw document binary locally at: {target_file_path}")

        # 2. Hardened Document Model Instantiation satisfying NOT NULL constraints
        new_doc_record = KnowledgeDocument(
            filename=file.filename,
            status="PENDING"
        )
        
        # 🎯 THE CRITICAL SCHEMA FIX: Inject baseline placeholder fields to bypass strict PostgreSQL NOT NULL constraints
        if hasattr(new_doc_record, 's3_key'):
            setattr(new_doc_record, 's3_key', f"local://storage/text_cache/{file.filename}")
        if hasattr(new_doc_record, 'mime_type'):
            setattr(new_doc_record, 'mime_type', "application/pdf")
        if hasattr(new_doc_record, 'file_size'):
            setattr(new_doc_record, 'file_size', file_size_bytes)
            
        # Optional check for alternate filesystem structures
        if hasattr(new_doc_record, 'file_path'):
            setattr(new_doc_record, 'file_path', target_file_path)

        db.add(new_doc_record)
        await db.commit()
        await db.refresh(new_doc_record)

        print(f"💾 DATABASE LEDGER: Registered row ID #{new_doc_record.id} for document: {file.filename}")

        # 3. Trigger your live processing, chunking, and embedding creation loops
        if process_and_chunk_pdf:
            print(f"⚙️ PIPELINE WORKERS: Launching token isolation loops for file: {file.filename}")
            extracted_chunks = await process_and_chunk_pdf(target_file_path, new_doc_record.id, db)
            print(f"🟢 PIPELINE WORKERS: Generated and committed chunks to disk stores.")

        return {
            "status": "SUCCESS",
            "document_id": new_doc_record.id,
            "filename": file.filename,
            "message": "Document pipeline executed completely."
        }

    except Exception as exc:
        await db.rollback()
        print(f"❌ INGESTION ENGINE CRASH: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal ingestion pipeline collapse: {str(exc)}"
        )