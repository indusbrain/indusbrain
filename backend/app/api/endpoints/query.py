import anyio
import asyncio
import uuid
import re
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, engine
from app.models.chat_history import ChatMessage
from app.services.agents.graph import compiled_agent_workflow

router = APIRouter(prefix="/query", tags=["Industrial AI Agent Core"])

class QueryRequestPayload(BaseModel):
    query: str = Field(..., description="The operator question from the plant floor.")
    routing_mode: str = Field(default="LOCAL", description="Target engine brain choice mapping.")
    session_id: str = Field(default="", description="Optional tracking string parameter identifier.")

class QueryResponsePayload(BaseModel):
    response: str = Field(..., description="The compiled final response report.")
    confidence_score: float = Field(..., description="Data assurance index value metrics.")
    reasoning_path: List[str] = Field(..., description="Auditable node trail matrix.")
    current_agent: str = Field(..., description="Target node tag matching termination states.")
    session_id: str = Field(..., description="Returned active workspace session context verification tracking key.")

def sanitize_historical_content_stream(raw_text: str) -> str:
    """ Strips out heavy markdown layouts and headers to prevent recursive mirror loops """
    clean_lines = []
    exclude_patterns = [
        r"⚙️ Industrial Intelligence Report",
        r"====================",
        r"📖 Technical Specifications",
        r"🛡️ Operational Safety",
        r"🔧 Asset Maintenance History",
        r"💡 Executive Action Directive"
    ]
    
    for line in raw_text.split('\n'):
        line_strip = line.strip()
        if not line_strip or line_strip.startswith("---") or line_strip.startswith("- *No direct"):
            continue
        if any(re.search(pat, line_strip) for pat in exclude_patterns):
            continue
        clean_line = line_strip.replace("CURRENT OPERATOR QUERY:", "").replace("PREVIOUS CONVERSATION HISTORY:", "")
        clean_lines.append(clean_line.strip())
        
    return " ".join(clean_lines)[:300]

# =====================================================================
# 🔌 PORTAL A: UNARY REST SUBMIT GATEWAY
# =====================================================================
@router.post("/submit", response_model=QueryResponsePayload, status_code=status.HTTP_200_OK)
async def submit_operator_query(payload: QueryRequestPayload, db: AsyncSession = Depends(get_db)):
    if not payload.query.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty.")

    active_session_id = payload.session_id.strip() if payload.session_id.strip() else str(uuid.uuid4())

    try:
        history_query = select(ChatMessage).where(ChatMessage.session_id == active_session_id).order_by(ChatMessage.created_at.asc())
        history_records = await db.execute(history_query)
        past_messages = history_records.scalars().all()

        dialogue_history_context = ""
        if past_messages:
            dialogue_history_context = "PREVIOUS CHAT HISTORY CONTEXT:\n"
            for m in past_messages:
                sanitized_body = sanitize_historical_content_stream(m.content)
                dialogue_history_context += f"   • [{m.sender.upper()}]: {sanitized_body}\n"
            dialogue_history_context += "\n"

        augmented_query = f"{dialogue_history_context}CURRENT PROMPT QUESTION: {payload.query}"

        initial_graph_state = {
            "query": augmented_query,
            "routing_mode": payload.routing_mode.upper(),
            "current_agent": "orchestrator",
            "extracted_docs": [],
            "graph_entities": [],
            "compliance_violations": [],
            "failure_logs": [],
            "reasoning_path": [],
            "confidence_score": 0.0,
            "final_response": ""
        }

        # 🎯 THE FIX: Await the async workflow execution pipeline natively using .ainvoke
        final_processed_state = await compiled_agent_workflow.ainvoke(initial_graph_state)
        compiled_answer = final_processed_state.get("final_response", "Failed to compile final report.")

        operator_msg = ChatMessage(session_id=active_session_id, sender="operator", content=payload.query)
        agent_msg = ChatMessage(session_id=active_session_id, sender="agent", content=compiled_answer)
        db.add_all([operator_msg, agent_msg])
        await db.commit()

        return QueryResponsePayload(
            response=compiled_answer,
            confidence_score=final_processed_state.get("confidence_score", 0.0),
            reasoning_path=final_processed_state.get("reasoning_path", []),
            current_agent=final_processed_state.get("current_agent", "compiler_node"),
            session_id=active_session_id
        )
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Graph runtime error: {str(exc)}")

# =====================================================================
# 🌊 PORTAL B: ASYNCHRONOUS SSE STREAM GATEWAY
# =====================================================================
@router.post("/stream", status_code=status.HTTP_200_OK)
async def stream_operator_query_loop(payload: QueryRequestPayload, db: AsyncSession = Depends(get_db)):
    user_input_raw = payload.query.strip()
    if not user_input_raw:
        raise HTTPException(status_code=400, detail="Query text cannot be blank.")

    active_session_id = payload.session_id.strip() if payload.session_id.strip() else str(uuid.uuid4())

    history_query = select(ChatMessage).where(ChatMessage.session_id == active_session_id).order_by(ChatMessage.created_at.asc())
    history_records = await db.execute(history_query)
    past_messages = history_records.scalars().all()

    dialogue_history_context = ""
    if past_messages:
        dialogue_history_context = "PREVIOUS CHAT HISTORY CONTEXT:\n"
        for m in past_messages:
            sanitized_body = sanitize_historical_content_stream(m.content)
            dialogue_history_context += f"   • [{m.sender.upper()}]: {sanitized_body}\n"
        dialogue_history_context += "\n"

    augmented_query = f"{dialogue_history_context}CURRENT PROMPT QUESTION: {user_input_raw}"

    async def token_stream_generator():
        async with AsyncSession(engine) as local_async_db:
            try:
                initial_graph_state = {
                    "query": augmented_query,
                    "routing_mode": payload.routing_mode.upper(),
                    "current_agent": "orchestrator",
                    "extracted_docs": [],
                    "graph_entities": [],
                    "compliance_violations": [],
                    "failure_logs": [],
                    "reasoning_path": [],
                    "confidence_score": 0.0,
                    "final_response": ""
                }

                # 🎯 THE FIX: Await the async workflow execution pipeline natively using .ainvoke
                final_processed_state = await compiled_agent_workflow.ainvoke(initial_graph_state)
                compiled_report_text = final_processed_state.get("final_response", "Failed to compile final report.")

                yield f"data: __SESSION_ID__:{active_session_id} \n\n"
                await asyncio.sleep(0.01)

                word_tokens_list = compiled_report_text.split(" ")
                for token in word_tokens_list:
                    yield f"data: {token} \n\n"
                    await asyncio.sleep(0.01)

                operator_msg = ChatMessage(session_id=active_session_id, sender="operator", content=user_input_raw)
                agent_msg = ChatMessage(session_id=active_session_id, sender="agent", content=compiled_report_text)
                local_async_db.add_all([operator_msg, agent_msg])
                await local_async_db.commit()

            except Exception as exc:
                await local_async_db.rollback()
                yield f"data: ❌ CRITICAL STREAM GATEWAY EXCEPTION: {str(exc)} \n\n"

    return StreamingResponse(
        token_stream_generator(), 
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )