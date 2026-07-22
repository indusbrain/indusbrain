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
from app.security import Permission, require
from app.models.chat_history import ChatMessage
from app.services.agents.graph import compiled_agent_workflow
from app.api.endpoints.conversations import owner_key_dependency

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


# ---------------------------------------------------------------------------
# QUERY VALIDITY GATE
#
# A cross-encoder scores a one-character query like "A" highly against almost any
# passage, because there is nothing in the query for it to contradict. That
# produced 71% "HIGH confidence" answers with four citations for a single letter.
#
# The relevance floor cannot fix this - the scores really are high. The query
# itself has to be rejected as unanswerable before retrieval runs at all.
# ---------------------------------------------------------------------------
STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "am", "do", "does",
    "did", "of", "to", "in", "on", "at", "by", "for", "with", "and", "or", "but",
    "if", "it", "its", "this", "that", "these", "those", "as", "so", "then",
    "there", "here", "i", "you", "he", "she", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "our", "their", "s", "t",
}

MIN_QUERY_LENGTH = 3


def describe_query_problem(query_text: str) -> Optional[str]:
    """
    Returns why a query cannot be answered, or None if it is worth attempting.

    Deliberately permissive about SHORT but meaningful queries: a bare asset tag
    like "PUMP-101" is a legitimate question and must still work.
    """
    cleaned = query_text.strip()

    if len(cleaned) < MIN_QUERY_LENGTH:
        return "That's too short for me to search on. Ask a question, or name an asset tag."

    # Tokens that actually carry meaning: not punctuation, not a stopword.
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-_/]*", cleaned.lower())
    meaningful = [t for t in tokens if len(t) >= 2 and t not in STOPWORDS]

    if not meaningful:
        return (
            "I couldn't find anything to search for in that. "
            "Try naming an asset, a procedure, or a specification — "
            "for example 'What is the discharge pressure limit for PUMP-101?'"
        )

    return None


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
from app.services.asset_tags import ASSET_TAG_PATTERN, ASSET_HEADER_PATTERN  # noqa: E402

WORK_ORDER_PATTERN = re.compile(r"\b(WO-\d{4}-\d{3,4})\b", re.IGNORECASE)

# An explicit "Asset: PUMP-101" header is the authoritative owner of a log entry.


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
                # group(0), not group(1): the shared ASSET_TAG_PATTERN uses
                # non-capturing groups, so the whole match IS the tag. Asking for
                # group(1) raised "IndexError: no such group" and turned every
                # maintenance-history question into a 500.
                asset_tag = inline.group(0) if inline else (nearby if nearby else None)

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


def build_evidence_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts the auditable parts of a response for storage alongside the answer,
    so citations and the decision trace survive a page reload.
    """
    return {
        "confidence_score": payload.get("confidence_score", 0.0),
        "confidence_band": payload.get("confidence_band", "NO_EVIDENCE"),
        "confidence_explanation": payload.get("confidence_explanation", ""),
        "engine": payload.get("engine", ""),
        "grounded": payload.get("grounded", False),
        "notice": payload.get("notice"),
        "citations": payload.get("citations", []),
        "confidence_metadata": payload.get("confidence_metadata", {}),
        "organizational_memory": payload.get("organizational_memory", {}),
        "decision_replay_path": payload.get("decision_replay_path", []),
        "reasoning_path": payload.get("reasoning_path", []),
        "current_agent": payload.get("current_agent", ""),
    }


async def persist_chat_turn(
    session_id: str,
    sender: str,
    content: str,
    owner_key: str = "",
    is_first_turn: bool = False,
    evidence: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Writes a conversation turn to Postgres, creating or updating the parent
    thread so the conversation appears in the history list.

    Failures must never break the reply the operator is waiting for.
    """
    try:
        async with async_session_local() as history_session:
            from app.api.endpoints.conversations import ensure_conversation, touch_conversation

            # Always ensure the thread exists on an operator turn. Gating this on
            # "first turn" meant a browser that had a stored session id — i.e.
            # every returning user — never got a Conversation row, so nothing
            # appeared in the history list.
            # ensure_conversation is idempotent: it returns the existing row.
            if owner_key and sender == "operator":
                await ensure_conversation(history_session, session_id, owner_key, content)

            history_session.add(
                ChatMessage(
                    session_id=session_id,
                    sender=sender,
                    content=content,
                    evidence=evidence,
                )
            )
            await history_session.commit()

            if sender == "agent":
                await touch_conversation(history_session, session_id, content)
    except Exception as history_error:
        print(f"⚠️ CHAT HISTORY: could not persist '{sender}' turn: {history_error}")


async def load_conversation_context(session_id: str, max_turns: int = 6) -> List[Dict[str, str]]:
    """
    Loads recent turns so the assistant has continuity within a thread.

    Only the last few turns are used: the retrieved passages are what the answer
    must be grounded in, and a long history would crowd them out of the context
    window.
    """
    try:
        async with async_session_local() as history_session:
            result = await history_session.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.id.desc())
                .limit(max_turns)
            )
            recent = list(reversed(result.scalars().all()))
            return [{"sender": m.sender, "content": m.content} for m in recent]
    except Exception as context_error:
        print(f"⚠️ CHAT CONTEXT: could not load history: {context_error}")
        return []


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


def unanswerable_payload(reason: str, session_id: str) -> Dict[str, Any]:
    """
    Response for a query that cannot be searched on at all.

    Carries zero confidence and zero citations, because no retrieval was run.
    """
    return {
        "response": reason,
        "confidence_score": 0.0,
        "confidence_band": "NO_EVIDENCE",
        "confidence_explanation": "No search was performed, so there is no evidence to score.",
        "reasoning_path": ["query_rejected"],
        "current_agent": "input_guard",
        "session_id": session_id,
        "engine": "Input validation (no retrieval, no inference)",
        "grounded": False,
        "notice": None,
        "citations": [],
        "confidence_metadata": {
            "score": 0.0,
            "band": "NO_EVIDENCE",
            "explanation": "No search was performed.",
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
            "empty_reason": "No search was performed for this input.",
        },
        "decision_replay_path": [{
            "step": 1,
            "node": "input_guard",
            "title": "Input Validation",
            "status": "REFUSED",
            "detail": reason,
            "metrics": {},
        }],
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
@router.post(
    "/submit",
    response_model=QueryResponsePayload,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require(Permission.ASK_QUESTIONS))],
)
async def submit_operator_query(
    payload: QueryRequestPayload,
    db: AsyncSession = Depends(get_db),
    owner_key: str = Depends(owner_key_dependency),
):
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    active_session_id = payload.session_id.strip() or str(uuid.uuid4())
    target_mode = payload.routing_mode.upper().strip()
    if target_mode in ("INTERNAL", "FALLBACK"):
        target_mode = "FALLBACK"

    is_new_thread = not payload.session_id.strip()
    await persist_chat_turn(
        active_session_id, "operator", payload.query.strip(),
        owner_key=owner_key, is_first_turn=is_new_thread,
    )

    # Reject unanswerable input BEFORE retrieval. Without this a one-character
    # query scored 71% "HIGH confidence" with four citations.
    query_problem = describe_query_problem(payload.query)
    if query_problem:
        await persist_chat_turn(
            active_session_id, "agent", query_problem,
            evidence=build_evidence_record(unanswerable_payload(query_problem, active_session_id)),
        )
        return QueryResponsePayload(**unanswerable_payload(query_problem, active_session_id))

    casual_reply = check_casual_intent_intercept(payload.query)
    if casual_reply:
        await persist_chat_turn(
            active_session_id, "agent", casual_reply,
            evidence=build_evidence_record(casual_response_payload(casual_reply, active_session_id)),
        )
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
    await persist_chat_turn(
        active_session_id, "agent", response_payload["response"],
        evidence=build_evidence_record(response_payload),
    )
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


@router.post(
    "/stream",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require(Permission.ASK_QUESTIONS))],
)
async def stream_operator_query_loop(
    payload: QueryRequestPayload,
    owner_key: str = Depends(owner_key_dependency),
):
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

            await persist_chat_turn(
                active_session_id, "operator", user_input_raw,
                owner_key=owner_key, is_first_turn=not payload.session_id.strip(),
            )

            # Same input guard as /submit: reject unanswerable queries before
            # any retrieval runs, so they cannot score confidence or cite sources.
            query_problem = describe_query_problem(user_input_raw)
            if query_problem:
                yield sse_event("metadata", unanswerable_payload(query_problem, active_session_id))
                yield sse_event("token", {"text": query_problem})
                yield sse_event("done", {"session_id": active_session_id})
                await persist_chat_turn(
            active_session_id, "agent", query_problem,
            evidence=build_evidence_record(unanswerable_payload(query_problem, active_session_id)),
        )
                return

            casual_reply = check_casual_intent_intercept(user_input_raw)
            if casual_reply:
                payload_out = casual_response_payload(casual_reply, active_session_id)
                yield sse_event("metadata", payload_out)
                for line in casual_reply.split("\n"):
                    yield sse_event("token", {"text": line + "\n"})
                    await asyncio.sleep(0.01)
                yield sse_event("done", {"session_id": active_session_id})
                await persist_chat_turn(
            active_session_id, "agent", casual_reply,
            evidence=build_evidence_record(casual_response_payload(casual_reply, active_session_id)),
        )
                return

            # PROGRESS REPORTING
            #
            # The pipeline can take 40-90s on CPU inference, and previously the UI
            # showed one static line for the whole wait, so it looked frozen.
            #
            # The graph runs as a single awaited call, so we cannot interleave
            # status events with its internal steps. Instead a background task
            # advances the stage labels on a timeline matched to the real pipeline,
            # and it is CANCELLED the moment the graph returns — so it can never
            # claim a stage the run has already passed, and never outlives it.
            stage_queue: asyncio.Queue = asyncio.Queue()

            # Ask the REAL supervisor which specialist this question routes to, so
            # the progress panel names the agent that is actually about to run
            # rather than guessing. Classification is pure regex over the query -
            # it costs nothing and is deterministic, so running it here and again
            # inside the graph gives the same answer.
            from app.services.agents.supervisor import supervisor_orchestrator
            from app.services.agents.workers import AGENT_PROFILES

            AGENT_DISPLAY = {
                "conflict_agent": "Conflict Agent",
                "compiler_node": "Response Compiler",
            }

            try:
                routed_to = supervisor_orchestrator.classify_intent_node(
                    {"query": user_input_raw}
                )["current_agent"]
            except Exception:
                routed_to = "knowledge_agent"

            selected_agent_label = AGENT_DISPLAY.get(routed_to) or (
                AGENT_PROFILES.get(routed_to, {}).get("label", "specialist agent")
            )

            async def report_progress():
                # Retrieval and generation timings only. The supervisor and agent
                # stages are emitted immediately below, BEFORE the workflow starts,
                # because their outcome is already known — putting them on a timer
                # meant a fast retrieval-only run finished before they ever fired.
                timeline = [
                    (0.0, "retrieving", "Searching indexed documents…"),
                    (1.2, "graph", "Walking the knowledge graph…"),
                    (2.4, "ranking", "Ranking passages by relevance…"),
                    (3.8, "reasoning", "Reading the retrieved passages…"),
                    (8.0, "reasoning", "Composing a grounded answer…"),
                    (26.0, "reasoning", "Still working — local model inference is slow on CPU…"),
                ]
                previous = 0.0
                for delay, stage, message in timeline:
                    await asyncio.sleep(delay - previous)
                    previous = delay
                    await stage_queue.put({"stage": stage, "message": message})

            # Emit the routing decision straight away so the operator always sees
            # which specialist was selected, however fast the run completes.
            yield sse_event("status", {"stage": "supervisor", "message": "Classifying the question…"})
            yield sse_event(
                "status",
                {"stage": "agent", "message": f"Running the {selected_agent_label}…"},
            )

            progress_task = asyncio.create_task(report_progress())
            workflow_task = asyncio.create_task(run_agent_workflow(user_input_raw, target_mode))

            # Forward stage updates until the workflow finishes.
            while not workflow_task.done():
                queue_get = asyncio.create_task(stage_queue.get())
                done, _ = await asyncio.wait(
                    {queue_get, workflow_task}, return_when=asyncio.FIRST_COMPLETED
                )
                if queue_get in done:
                    yield sse_event("status", queue_get.result())
                else:
                    queue_get.cancel()

            progress_task.cancel()
            final_state = await workflow_task
            response_payload = assemble_response_payload(final_state, active_session_id)

            # Send the full audit payload first so the UI can render citations,
            # confidence and the decision trace alongside the streaming answer.
            yield sse_event("metadata", response_payload)

            answer_text = response_payload["response"]
            for line in answer_text.split("\n"):
                yield sse_event("token", {"text": line + "\n"})
                await asyncio.sleep(0.012)

            yield sse_event("done", {"session_id": active_session_id})
            await persist_chat_turn(
                active_session_id, "agent", answer_text,
                evidence=build_evidence_record(response_payload),
            )

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
@router.get(
    "/history/{session_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require(Permission.ASK_QUESTIONS))],
)
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
                "evidence": m.evidence,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }
