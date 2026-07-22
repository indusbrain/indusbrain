from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security import Permission, require
from app.models.chat_history import ChatMessage
from app.models.chunk import KnowledgeChunk
from app.models.document import KnowledgeDocument
from app.api.endpoints.telemetry_dashboard import (
    get_dashboard_payload,
    invalidate_dashboard_cache,
)

router = APIRouter(prefix="/telemetry", tags=["System Telemetry Subsystem"])


@router.get(
    "/dashboard",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require(Permission.VIEW_DASHBOARD))],
)
async def fetch_live_dashboard_telemetry(
    refresh: bool = False, db: AsyncSession = Depends(get_db)
):
    """
    Live operational telemetry for the dashboard.

    Every figure is a direct database count or an explicitly-defined ratio of
    counts. Pass ?refresh=true to bypass the short-lived cache.
    """
    return await get_dashboard_payload(db, force_refresh=refresh)


@router.delete(
    "/document/{doc_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require(Permission.DELETE_DOCUMENTS))],
)
async def manual_purge_document_record(doc_id: int, db: AsyncSession = Depends(get_db)):
    """
    Deletes a document from ALL three stores.

    Previously only Postgres rows were removed, leaving orphaned vectors in Chroma
    and orphaned nodes in Neo4j that could still surface as citations for a
    document the user believed was deleted.
    """
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
    target_doc = result.scalars().first()
    if not target_doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    filename = target_doc.filename

    try:
        await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == doc_id))
        await db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
        await db.commit()
    except Exception as db_error:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database delete failed: {db_error}")

    # Best-effort cleanup of the derived stores. A failure here must not resurrect
    # the Postgres row, but it must be reported rather than silently ignored.
    cleanup_warnings = []

    try:
        from app.services.vector_store import vector_store_engine
        vector_store_engine.purge_document_vectors(doc_id)
    except Exception as vector_error:
        cleanup_warnings.append(f"Chroma cleanup failed: {vector_error}")

    try:
        from app.services.graph_store import graph_store_engine
        graph_store_engine.purge_document_graph(doc_id)
    except Exception as graph_error:
        cleanup_warnings.append(f"Neo4j cleanup failed: {graph_error}")

    invalidate_dashboard_cache()

    return {
        "status": "DELETED",
        "document_id": doc_id,
        "filename": filename,
        "warnings": cleanup_warnings,
    }


@router.delete("/session/{session_id}", status_code=status.HTTP_200_OK)
async def manual_purge_chat_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes all stored conversation turns for a session."""
    try:
        result = await db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
        await db.commit()
        return {"status": "PURGED", "session_id": session_id, "messages_deleted": result.rowcount}
    except Exception as purge_error:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(purge_error))
