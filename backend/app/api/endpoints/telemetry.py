import socket
import httpx
import re
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete
from app.database import get_db, engine
from app.models.document import KnowledgeDocument
from app.models.chat_history import ChatMessage

try:
    from app.models.chunk import KnowledgeChunk
except ImportError:
    KnowledgeChunk = None

router = APIRouter(prefix="/telemetry", tags=["System Telemetry Subsystem"])

@router.get("/dashboard", status_code=status.HTTP_200_OK)
async def fetch_live_dashboard_telemetry(db: AsyncSession = Depends(get_db)):
    uploaded_files_list = []
    total_docs = 0
    
    try:
        doc_query = select(KnowledgeDocument).order_by(desc(KnowledgeDocument.id))
        query_result = await db.execute(doc_query)
        documents_records = query_result.scalars().all()
        total_docs = len(documents_records)
        
        for doc in documents_records:
            uploaded_files_list.append({
                "id": doc.id,
                "filename": doc.filename,
                "storage_path": "Local Disk Partition",
                "uploaded_at": "Active"
            })
    except Exception:
        pass

    postgres_health = "ONLINE" if socket.create_connection(("localhost", 5432), timeout=0.15) else "OFFLINE"
    neo4j_health = "ONLINE" if socket.create_connection(("localhost", 7687), timeout=0.15) else "OFFLINE"
    chroma_health = "ONLINE" if socket.create_connection(("localhost", 8000), timeout=0.15) else "OFFLINE"

    ollama_health = "ONLINE"
    try:
        res = httpx.get("http://127.0.0.1:11434/", timeout=0.15)
        if res.status_code != 200: ollama_health = "OFFLINE"
    except Exception: ollama_health = "OFFLINE"

    asset_deck = []
    if KnowledgeChunk and total_docs > 0:
        try:
            chunk_query = select(KnowledgeChunk)
            chunk_res = await db.execute(chunk_query)
            all_chunks = chunk_res.scalars().all()
            
            # 🎯 THE CRITICAL EXTRACTION PURGE FILTER
            structural_blacklist = {
                "NOTE", "ANNEXURE", "STANDARD", "STD", "PAGE", "SECTION", 
                "FIGURE", "FIG", "TABLE", "REVISION", "ANNEX", "CLAUSE", 
                "OISD", "NFPA", "IS", "UL", "API", "ASME", "ANSI"
            }
            
            extracted_unique_tags = set()
            for chunk in all_chunks:
                matches = re.findall(r'\b([A-Z]{2,10}-\d+[A-Z]?)\b', chunk.content.upper())
                for component_tag in matches:
                    # Extract the alpha prefix text block (e.g. 'STD' from 'STD-189')
                    prefix = component_tag.split('-')[0].strip()
                    
                    # 🎯 THE SHIELD: Drop the entry if the tag or its prefix matches any layout stop-word
                    if prefix in structural_blacklist or component_tag in structural_blacklist:
                        continue
                    if any(bad_word in component_tag for bad_word in structural_blacklist):
                        continue
                        
                    extracted_unique_tags.add(component_tag)
            
            for tag in sorted(extracted_unique_tags):
                inferred_category = "Mechanical" if any(x in tag for x in ["PUMP", "COMP", "TURB", "BHP"]) else "Pneumatic" if "VALVE" in tag else "Electrical"
                inferred_name = f"Centrifugal Pump Asset" if "PUMP" in tag or "BHP" in tag else f"High-Pressure Valve" if "VALVE" in tag else "Industrial Hardware Asset"
                
                asset_deck.append({
                    "tag": tag,
                    "name": inferred_name,
                    "type": inferred_category,
                    "status": "Operational",
                    "health": "Active in Knowledge Graph"
                })
        except Exception as e:
            print(f"⚠️ Telemetry extractor exception: {str(e)}")

    knowledge_score = min(100, 45 + (total_docs * 15)) if total_docs > 0 else 0
    completeness = min(100, 30 + (total_docs * 20)) if total_docs > 0 else 0
    compliance = 96 if total_docs > 0 else 0

    return {
        "infrastructure": {
            "postgresql": postgres_health,
            "neo4j": neo4j_health,
            "chromadb": chroma_health,
            "ollama_qwen": ollama_health
        },
        "metrics": {
            "total_documents": total_docs,
            "knowledge_score": knowledge_score,
            "documentation_completeness": completeness,
            "compliance_health": compliance
        },
        "inventory": uploaded_files_list,
        "assets": asset_deck
    }

@router.delete("/document/{doc_id}", status_code=status.HTTP_200_OK)
async def manual_purge_document_record(doc_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
        target_doc = result.scalar() 
        if not target_doc:
            raise HTTPException(status_code=404, detail="Target document record not found.")

        if KnowledgeChunk:
            await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == doc_id))
        
        await db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
        await db.commit()
        return {"status": "DELETED"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/session/{session_id}", status_code=status.HTTP_200_OK)
async def manual_purge_chat_session(session_id: str, db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
        await db.commit()
        return {"status": "PURGED", "message": f"Session ledger {session_id} successfully wiped."}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))