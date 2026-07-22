import asyncio
import json
import re
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session_local
from app.models.chat_history import ChatMessage
from app.services.agents.graph import compiled_agent_workflow

router = APIRouter(prefix="/query", tags=["Industrial AI Agent Core"])


# =====================================================================
# REQUEST / RESPONSE CONTRACTS
# =====================================================================
class QueryRequestPayload(BaseModel):
    query: str = Field(..., description="The operator question from the plant floor.")
    routing_mode: str = Field(default="LOCAL", description="Target engine: LOCAL or FALLBACK.")
    session_id: str = Field(default="", description="Conversation id for history continuity.")


class SourceCitation(BaseModel):
    filename: str
    excerpt: str
    relevance: float
    origin: str
    document_id: Optional[Any] = None
    chunk_index: Optional[Any] = None


class QueryResponsePayload(BaseModel):
    response: str
    confidence_score: float
    confidence_band: str
    confidence_explanation: str
    reasoning_path: List[str]
    current_agent: str
    session_id: str
    engine: str
    grounded: bool
    notice: Optional[str] = None
    citations: List[SourceCitation] = Field(default_factory=list)
    confidence_metadata: Dict[str, Any] = Field(default_factory=dict)
    organizational_memory: Dict[str, Any] = Field(default_factory=dict)
    decision_replay_path: List[Dict[str, Any]] = Field(default_factory=list)


# =====================================================================
# HELPERS - all of these operate on REAL retrieved data only
# =====================================================================
CASUAL_GREETINGS = {
    "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
    "how are you", "how's it going", "yo", "sup",
}


def check_casual_intent_intercept(query_text: str) -> Optional[str]:
    clean_query = query_text.strip().lower().rstrip("?.!")
    if clean_query in CASUAL_GREETINGS:
        return (
            "Hello. I'm IndusBrain, your industrial knowledge assistant.\n\n"
            "I answer questions from the documents you've indexed — equipment manuals, "
            "SOPs, maintenance reports and safety standards. Ask me about an asset tag, "
            "a specification, a past failure, or a compliance requirement."
        )
    return None


def build_citations(retrieved_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Builds citations from the passages that were ACTUALLY retrieved and used.
    Returns an empty list when nothing was retrieved - never a placeholder.
    """
    citations = []
    for chunk in retrieved_chunks:
        if not isinstance(chunk, dict):
            continue
        excerpt = (chunk.get("matched_excerpt") or chunk.get("content") or "").strip()
        if not excerpt:
            continue
        citations.append({
            "filename": chunk.get("filename") or "Unknown source",
            "excerpt": excerpt[:400],
            "relevance": round(float(chunk.get("confidence_score", 0.0)), 4),
            "origin": chunk.get("origin_source", "UNKNOWN"),
            "document_id": chunk.get("document_id"),
            "chunk_index": chunk.get("chunk_index"),
        })
    return citations


# Matches dates that genuinely appear in source text. We only ever report a date
# if the document actually contains one - we never estimate or invent it.
DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"),
    re.compile(
        r"\b(\d{1,2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\.?\s+\d{4})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b((?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\.?\s+\d{1,2},?\s+\d{4})\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(Q[1-4]\s*[-/]?\s*(?:FY)?\d{2,4})\b", re.IGNORECASE),
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
]

# Restricted to real equipment classes so part numbers (JC-5620, SKF-7310) and
# document references (ERN-2024, SOP-014) are not reported as plant assets.
ASSET_TAG_PATTERN = re.compile(
    r"\b((?:PUMP|VALVE|PSV|COMP|MTR|BRG|HX|TK|FAN|BLR|ENG|SYS)-\d{2,4}[A-Z]?)\b"
)

WORK_ORDER_PATTERN = re.compile(r"\b(WO-\d{4}-\d{3,4})\b", re.IGNORECASE)

# An explicit "Asset: PUMP-101" header is the authoritative owner of a log entry.
ASSET_HEADER_PATTERN = re.compile(
    r"Asset:\s*((?:PUMP|VALVE|PSV|COMP|MTR|BRG|HX|TK|FAN|BLR|ENG|SYS)-\d{2,4}[A-Z]?)",
    re.IGNORECASE,
)

MAINTENANCE_EVENT_TERMS = (
    "REPLACED", "REPAIRED", "SERVICED", "OVERHAUL", "FAILED", "FAILURE",
    "BREAKDOWN", "INSPECTED", "CALIBRATED", "REBUILT", "TIGHTENED",
    "LUBRICATED", "SHUTDOWN", "TRIPPED", "LEAK", "FLUSHED", "REPACKED",
    "CLEANED", "REALIGNED", "REINSTATED",
)

# Phrases that indicate advisory or hypothetical text rather than a record of
# something that actually happened. These must not be logged as history.
NON_EVENT_MARKERS = (
    "WILL CAUSE", "MUST BE", "MUST NOT", "SHOULD BE", "IF ANY", "DO NOT",
    "REQUIRED", "ENSURE", "VERIFY THAT", "SHALL ", "MAY CAUSE", "CAN CAUSE",
)

# How far back to look for the date/asset/work-order header of a log entry.
# Maintenance logs put "Date:" and "Asset:" on separate lines above the event.
RECORD_CONTEXT_WINDOW = 420


def extract_organizational_memory(retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Surfaces past maintenance events that are ACTUALLY WRITTEN in the retrieved
    documents.

    Rules:
      - The event sentence is quoted verbatim from the source.
      - A date is reported only if it literally appears in that text.
      - The source filename is the real document the text came from.
      - If nothing qualifies, returns an empty result with an honest reason.
    """
    past_actions: List[Dict[str, Any]] = []
    seen_signatures = set()

    def last_match(pattern, text):
        """Returns the LAST match in the text - i.e. the nearest header above the event."""
        found = pattern.findall(text)
        return found[-1] if found else None

    for chunk in retrieved_chunks:
        if not isinstance(chunk, dict):
            continue

        body = (chunk.get("content") or chunk.get("matched_excerpt") or "").strip()
        if not body:
            continue

        source_name = chunk.get("filename") or "Unknown source"

        for sentence_match in re.finditer(r"[^\n.!?]+[.!?]?", body):
            sentence = sentence_match.group(0).strip()
            if len(sentence) < 25:
                continue

            upper_sentence = sentence.upper()

            if not any(term in upper_sentence for term in MAINTENANCE_EVENT_TERMS):
                continue

            # Skip instructions, warnings and conditional statements - these describe
            # what SHOULD happen, not what DID happen, and must never be logged as
            # organizational history.
            if any(marker in upper_sentence for marker in NON_EVENT_MARKERS):
                continue

            # A log entry's date and asset usually sit on lines ABOVE the event text,
            # so search a window of preceding context rather than the sentence alone.
            window_start = max(0, sentence_match.start() - RECORD_CONTEXT_WINDOW)
            context_window = body[window_start:sentence_match.end()]

            found_date = None
            for pattern in DATE_PATTERNS:
                candidate = last_match(pattern, context_window)
                if candidate:
                    found_date = candidate
                    break

            # Resolution order, most authoritative first:
            #   1. an explicit "Asset: TAG" header for this log entry
            #   2. a tag named in the event sentence itself
            #   3. the nearest tag anywhere in the preceding context
            asset_header = last_match(ASSET_HEADER_PATTERN, context_window)
            if asset_header:
                asset_tag = asset_header.upper()
            else:
                inline = ASSET_TAG_PATTERN.search(upper_sentence)
                nearby = last_match(ASSET_TAG_PATTERN, context_window.upper())
                asset_tag = inline.group(1) if inline else (nearby if nearby else None)

            work_order = last_match(WORK_ORDER_PATTERN, context_window)

            signature = sentence[:80].lower()
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)

            past_actions.append({
                "date": found_date,                 # None => UI shows "date not recorded"
                "date_known": found_date is not None,
                "asset": asset_tag,                 # None => UI shows "asset not identified"
                "work_order": work_order.upper() if work_order else None,
                "action": sentence[:320],           # verbatim from the document
                "source": source_name,
                "verbatim": True,
            })

            if len(past_actions) >= 8:
                break
        if len(past_actions) >= 8:
            break

    if not past_actions:
        return {
            "repair_history_found": False,
            "past_actions": [],
            "empty_reason": (
                "No maintenance events were found in the retrieved passages. "
                "Either these documents contain no service history, or none was "
                "relevant to this question."
            ),
        }

    return {
        "repair_history_found": True,
        "past_actions": past_actions,
        "empty_reason": None,
    }


async def persist_chat_turn(session_id: str, sender: str, content: str) -> None:
    """Writes a conversation turn to Postgres. Failures must never break the reply."""
    try:
        async with async_session_local() as history_session:
            history_session.add(
                ChatMessage(session_id=session_id, sender=sender, content=content)
            )
            await history_session.commit()
    except Exception as history_error:
        print(f"⚠️ CHAT HISTORY: could not persist '{sender}' turn: {history_error}")


async def run_agent_workflow(query_text: str, routing_mode: str) -> Dict[str, Any]:
    """Invokes the compiled LangGraph workflow with a clean, honest initial state."""
    initial_graph_state = {
        "query": query_text,
        "routing_mode": routing_mode,
        "current_agent": "orchestrator",
        "extracted_docs": [],      # starts EMPTY - no seeded placeholder documents
        "graph_entities": [],
        "compliance_violations": [],
        "failure_logs": [],
        "reasoning_path": [],
        "decision_trace": [],
        "retrieval_stats": {},
        "confidence_score": 0.0,
        "final_response": "",
    }
    return await compiled_agent_workflow.ainvoke(initial_graph_state)


def assemble_response_payload(
    final_state: Dict[str, Any], session_id: str
) -> Dict[str, Any]:
    """Maps the graph's real terminal state onto the API contract. No invented values."""
    retrieved_chunks = [c for c in (final_state.get("extracted_docs") or []) if isinstance(c, dict)]
    stats = final_state.get("retrieval_stats") or {}
    confidence = stats.get("confidence") or {}
    components = confidence.get("components") or {}

    citations = build_citations(retrieved_chunks)

    return {
        "response": final_state.get("final_response", "").strip(),
        "confidence_score": float(confidence.get("score", 0.0)),
        "confidence_band": confidence.get("band", "NO_EVIDENCE"),
        "confidence_explanation": confidence.get(
            "explanation", "No retrieval was performed for this question."
        ),
        "reasoning_path": final_state.get("reasoning_path", []),
        "current_agent": final_state.get("current_agent", "compiler_node"),
        "session_id": session_id,
        "engine": stats.get("engine", "No inference performed"),
        "grounded": bool(stats.get("grounded", False)),
        "notice": stats.get("notice"),
        "citations": citations,
        "confidence_metadata": {
            "score": float(confidence.get("score", 0.0)),
            "band": confidence.get("band", "NO_EVIDENCE"),
            "explanation": confidence.get("explanation", ""),
            "sources": sorted({c["filename"] for c in citations}),
            "top_relevance": components.get("top_relevance", 0.0),
            "mean_relevance": components.get("mean_relevance", 0.0),
            "graph_verified": bool(components.get("graph_verified", False)),
            "distinct_sources": components.get("distinct_sources", 0),
            "candidates_considered": components.get("candidates_considered", 0),
            "vector_candidates": stats.get("vector_candidates", 0),
            "graph_candidates": stats.get("graph_candidates", 0),
        },
        "organizational_memory": extract_organizational_memory(retrieved_chunks),
        # The genuine node-by-node trace, written by the nodes as they executed.
        "decision_replay_path": final_state.get("decision_trace", []),
    }


def casual_response_payload(reply_text: str, session_id: str) -> Dict[str, Any]:
    """Response for small talk: explicitly zero-evidence, with nothing fabricated."""
    return {
        "response": reply_text,
        "confidence_score": 0.0,
        "confidence_band": "NOT_APPLICABLE",
        "confidence_explanation": "Conversational reply. No documents were searched.",
        "reasoning_path": ["intent_intercept"],
        "current_agent": "conversational_node",
        "session_id": session_id,
        "engine": "Intent intercept (no retrieval, no inference)",
        "grounded": False,
        "notice": None,
        "citations": [],
        "confidence_metadata": {
            "score": 0.0,
            "band": "NOT_APPLICABLE",
            "explanation": "Conversational reply. No documents were searched.",
            "sources": [],
            "top_relevance": 0.0,
            "mean_relevance": 0.0,
            "graph_verified": False,
            "distinct_sources": 0,
            "candidates_considered": 0,
            "vector_candidates": 0,
            "graph_candidates": 0,
        },
        "organizational_memory": {
            "repair_history_found": False,
            "past_actions": [],
            "empty_reason": "No document search was performed for a conversational message.",
        },
        "decision_replay_path": [{
            "step": 1,
            "node": "intent_intercept",
            "title": "Conversational Intercept",
            "status": "COMPLETED",
            "detail": "Recognised as small talk. The retrieval pipeline was not invoked.",
            "metrics": {},
        }],
    }


# =====================================================================
# PORTAL A: UNARY REST SUBMIT GATEWAY
# =====================================================================
@router.post("/submit", response_model=QueryResponsePayload, status_code=status.HTTP_200_OK)
async def submit_operator_query(payload: QueryRequestPayload, db: AsyncSession = Depends(get_db)):
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    active_session_id = payload.session_id.strip() or str(uuid.uuid4())
    target_mode = payload.routing_mode.upper().strip()
    if target_mode in ("INTERNAL", "FALLBACK"):
        target_mode = "FALLBACK"

    await persist_chat_turn(active_session_id, "operator", payload.query.strip())

    casual_reply = check_casual_intent_intercept(payload.query)
    if casual_reply:
        await persist_chat_turn(active_session_id, "agent", casual_reply)
        return QueryResponsePayload(**casual_response_payload(casual_reply, active_session_id))

    try:
        final_state = await run_agent_workflow(payload.query, target_mode)
    except Exception as workflow_error:
        print(f"🚨 AGENT WORKFLOW FAILURE: {type(workflow_error).__name__}: {workflow_error}")
        raise HTTPException(
            status_code=500,
            detail=f"The reasoning pipeline failed: {type(workflow_error).__name__}",
        )

    response_payload = assemble_response_payload(final_state, active_session_id)
    await persist_chat_turn(active_session_id, "agent", response_payload["response"])
    return QueryResponsePayload(**response_payload)


# =====================================================================
# PORTAL B: ASYNCHRONOUS SSE STREAM GATEWAY
# =====================================================================
def sse_event(event_name: str, data: Any) -> str:
    """
    Encodes a proper Server-Sent Event with JSON.

    The previous implementation emitted a Python dict repr and split answers on
    spaces, which destroyed newlines and could not be parsed reliably by the UI.
    """
    return f"event: {event_name}\ndata: {json.dumps(data, default=str)}\n\n"


@router.post("/stream", status_code=status.HTTP_200_OK)
async def stream_operator_query_loop(payload: QueryRequestPayload):
    user_input_raw = payload.query.strip()
    if not user_input_raw:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    active_session_id = payload.session_id.strip() or str(uuid.uuid4())
    target_mode = payload.routing_mode.upper().strip()
    if target_mode in ("INTERNAL", "FALLBACK"):
        target_mode = "FALLBACK"

    async def token_stream_generator():
        try:
            yield sse_event("session", {"session_id": active_session_id})

            await persist_chat_turn(active_session_id, "operator", user_input_raw)

            casual_reply = check_casual_intent_intercept(user_input_raw)
            if casual_reply:
                payload_out = casual_response_payload(casual_reply, active_session_id)
                yield sse_event("metadata", payload_out)
                for line in casual_reply.split("\n"):
                    yield sse_event("token", {"text": line + "\n"})
                    await asyncio.sleep(0.01)
                yield sse_event("done", {"session_id": active_session_id})
                await persist_chat_turn(active_session_id, "agent", casual_reply)
                return

            yield sse_event("status", {"stage": "retrieving", "message": "Searching indexed documents..."})

            # Real pipeline run - no seeded placeholder documents.
            final_state = await run_agent_workflow(user_input_raw, target_mode)
            response_payload = assemble_response_payload(final_state, active_session_id)

            # Send the full audit payload first so the UI can render citations,
            # confidence and the decision trace alongside the streaming answer.
            yield sse_event("metadata", response_payload)

            answer_text = response_payload["response"]
            for line in answer_text.split("\n"):
                yield sse_event("token", {"text": line + "\n"})
                await asyncio.sleep(0.012)

            yield sse_event("done", {"session_id": active_session_id})
            await persist_chat_turn(active_session_id, "agent", answer_text)

        except Exception as stream_error:
            print(f"🚨 STREAM FAILURE: {type(stream_error).__name__}: {stream_error}")
            yield sse_event("error", {
                "message": "The reasoning pipeline failed while streaming.",
                "detail": type(stream_error).__name__,
            })

    return StreamingResponse(
        token_stream_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# =====================================================================
# CONVERSATION HISTORY
# =====================================================================
@router.get("/history/{session_id}", status_code=status.HTTP_200_OK)
async def fetch_session_history(session_id: str, db: AsyncSession = Depends(get_db)):
    """Returns the stored turns for a conversation, oldest first."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.asc())
    )
    messages = result.scalars().all()
    return {
        "session_id": session_id,
        "message_count": len(messages),
        "messages": [
            {
                "id": m.id,
                "sender": m.sender,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }
