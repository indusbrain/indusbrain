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

router = APIRouter(prefix="/ingestion", tags=["Knowledge Ingestion Grid"])

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # Restrict uploads strictly to 50MB
ALLOWED_MIME_TYPES = ["application/pdf"]

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Secure HTTP Multipart Form upload gate. Validates physical data bounds, 
    offloads blocking file binary streaming to worker pools, and logs audit trails.
    """
    # 1. Enforce Structural MIME Validation
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{file.content_type}'. Platform only authorizes raw PDF documents."
        )

    # 2. Track Data Bounds and Validate Maximum File Size Constraints
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)  # Reset pointer back to zero index point

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot ingest an empty 0-byte document file context."
        )

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File layout footprint exceeds the 50MB hard boundary security threshold."
        )

    # 3. Formulate a Globally Unique S3 Storage Vault Mapped Key Namespace
    unique_id = uuid.uuid4().hex
    safe_filename = "".join([c if c.isalnum() or c in "._-" else "_" for c in file.filename])
    s3_key = f"documents/{unique_id}_{safe_filename}"

    # 4. Offload the Blocking Cloud Transfer to a Worker Thread Pool
    # 4. Offload the Blocking Cloud Transfer to a Worker Thread Pool
    try:
        await anyio.to_thread.run_sync(
            storage_service.upload_file_sync,
            file.file,
            s3_key
        )
    except Exception as e:
        # 🚨 DIAGNOSTIC INJECTOR: Force print the true root cause directly to your terminal console
        import traceback
        print("\n=== 🚨 INGESTION GATEWAY FAULT TRACE STACK ===")
        traceback.print_exc()
        print("==============================================\n")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Object store upload routine collapsed: {str(e)}"
        )

    # 5. Commit Metadata Tracking Metrics Asynchronously to PostgreSQL Ledger
    new_doc = KnowledgeDocument(
        filename=file.filename,
        s3_key=s3_key,
        mime_type=file.content_type,
        file_size=file_size,
        status=DocumentStatus.PENDING
    )
    
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)

    return new_doc

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