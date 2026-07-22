"""
Evidence-based operational impact assessment.

WHAT CHANGED AND WHY
--------------------
The previous implementation matched a handful of keywords ("delay", "increase",
"reduce") and emitted fixed engineering figures — +8.5% production, 2.3x risk,
75/100 compliance exposure. Those numbers were invented. Nothing in the corpus
produced them, and a scenario of literal gibberish ("adas") still returned a
confident-looking metric set because it fell through to the "general baseline".

Presenting fabricated numbers as engineering analysis is the most dangerous thing
this product could do, so the heuristic engine has been removed entirely.

This module now:
  1. Retrieves what the indexed documents actually say about the asset and the
     proposed change.
  2. Refuses when there is no supporting evidence, rather than guessing.
  3. Reports the REAL limits, warnings and open actions found in those documents,
     each traceable to its source.

It no longer emits any invented percentage. A number appears only if a document
states it.
"""

import re
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security import Permission, require
from app.services.llm_provider import llm_gateway
from app.services.reranker import industrial_reranker
from app.services.retrieval_hub import industrial_retrieval_hub

router = APIRouter(prefix="/simulator", tags=["Decision Impact Simulator Core"])

# Same floor the chat pipeline uses: below this the cross-encoder is telling us
# the passage does not actually relate to the question.
RELEVANCE_FLOOR = 0.01

# A scenario must express an operational action to be assessable.
OPERATIONAL_INTENT = re.compile(
    r"\b(delay|defer|postpone|extend|skip|reduce|cut|increase|raise|lower|"
    r"exceed|overload|bypass|disable|remove|replace|repair|shutdown|shut down|"
    r"restart|operate|run|continue|schedule|reschedule|advance|omit|"
    r"maintenance|inspection|calibration|overhaul|outage|pressure|temperature|"
    r"speed|load|flow|interval|frequency)\b",
    re.IGNORECASE,
)

# Real numeric statements found in retrieved passages.
MEASUREMENT_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(PSI|BAR|RPM|GPM|KW|HZ|MM/S|MM|CELSIUS|°C)\b", re.IGNORECASE
)

WARNING_MARKERS = (
    "WARNING", "CAUTION", "DANGER", "MUST NOT", "SHALL NOT", "PROHIBITED",
    "WILL CAUSE", "MAY CAUSE", "RISK OF", "FAILURE", "HAZARD", "VIOLATION",
)

OPEN_ACTION_MARKERS = ("NOT RESET", "NOT COMPLETED", "OPEN ACTION", "NOT PERFORMED", "OUTSTANDING", "PENDING")


class SimulationRequest(BaseModel):
    scenario: str = Field(..., description="The operational decision to assess.")
    asset_tag: str = Field(default="", description="Optional equipment tag to focus on.")


def _extract_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.strip()) > 25]


def _collect_findings(chunks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, str]]]:
    """Pulls real limits, warnings and open actions out of the retrieved passages."""
    limits: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    open_actions: List[Dict[str, str]] = []
    seen = set()

    for chunk in chunks:
        source = chunk.get("filename", "Unknown source")
        body = chunk.get("content") or chunk.get("matched_excerpt") or ""

        for sentence in _extract_sentences(body):
            key = sentence[:70].lower()
            if key in seen:
                continue
            upper = sentence.upper()

            if MEASUREMENT_PATTERN.search(sentence) and len(limits) < 8:
                seen.add(key)
                limits.append({"statement": sentence[:280], "source": source})
            elif any(marker in upper for marker in WARNING_MARKERS) and len(warnings) < 6:
                seen.add(key)
                warnings.append({"statement": sentence[:280], "source": source})
            elif any(marker in upper for marker in OPEN_ACTION_MARKERS) and len(open_actions) < 6:
                seen.add(key)
                open_actions.append({"statement": sentence[:280], "source": source})

    return {"limits": limits, "warnings": warnings, "open_actions": open_actions}


def _insufficient(scenario: str, asset_tag: str, reason: str, guidance: str) -> Dict[str, Any]:
    """A refusal. Carries no metrics, because none could be derived."""
    return {
        "scenario": scenario,
        "target_asset": asset_tag or "No specific asset",
        "has_sufficient_evidence": False,
        "refusal_reason": reason,
        "guidance": guidance,
        "assessment": None,
        "applicable_limits": [],
        "safety_warnings": [],
        "open_actions": [],
        "citations": [],
        "engine": "No assessment produced",
    }


SIMULATOR_DIRECTIVE = (
    "DOMAIN FOCUS — OPERATIONAL IMPACT ASSESSMENT.\n"
    "The engineer is proposing a change. Assess it using ONLY the sources.\n"
    "Structure the answer as:\n"
    "1. Whether the sources permit or prohibit the proposed change, and under what conditions.\n"
    "2. The specific limits or requirements it would affect, quoted with their values and units.\n"
    "3. Any warning or consequence the sources state about this kind of change.\n"
    "4. What the engineer must verify before proceeding.\n"
    "Do NOT estimate percentages, risk multipliers, costs or failure rates. "
    "If the sources do not quantify an impact, say that it is not quantified in the "
    "available documentation rather than supplying a figure."
)


@router.post(
    "/simulate",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require(Permission.RUN_SIMULATION))],
)
async def execute_decision_simulation_model(
    payload: SimulationRequest, db: AsyncSession = Depends(get_db)
):
    """
    Assesses a proposed operational decision against the indexed documents.

    Returns `has_sufficient_evidence: false` with an explicit reason whenever the
    corpus cannot support an assessment. It never fabricates engineering figures.
    """
    scenario_text = payload.scenario.strip()
    asset_tag = payload.asset_tag.strip().upper()
    if asset_tag in ("SELECT ASSET", "NO SPECIFIC ASSET"):
        asset_tag = ""

    # ---------------------------------------------------------------- guard 1
    # A structured refusal rather than an HTTP error: the UI can render the
    # explanation inline, and the caller learns what to supply instead.
    if len(scenario_text) < 8:
        return _insufficient(
            scenario_text,
            asset_tag,
            "That is too short to assess.",
            (
                "Describe the change you are considering as a sentence — for example "
                "'delay the bearing replacement by two weeks'."
            ),
        )

    # ---------------------------------------------------------------- guard 2
    # Gibberish or a bare noun is not an assessable decision. The old engine
    # happily scored "adas"; this refuses and says what is missing.
    if not OPERATIONAL_INTENT.search(scenario_text):
        return _insufficient(
            scenario_text,
            asset_tag,
            "This does not describe an operational decision I can assess.",
            (
                "Describe a specific change and its direction — for example "
                "'delay the bearing replacement by two weeks' or "
                "'increase discharge pressure above the rated limit'."
            ),
        )

    # ---------------------------------------------------------------- retrieve
    retrieval_query = f"{asset_tag} {scenario_text}".strip()
    raw_candidates = await industrial_retrieval_hub.retrieve_hybrid_context(retrieval_query, limit=8)
    scored = industrial_reranker.filter_and_rerank_context(
        query_string=retrieval_query, all_raw_candidates=raw_candidates, top_n=5
    )

    best_score = max((float(c.get("confidence_score", 0.0)) for c in scored), default=0.0)
    if not scored or best_score < RELEVANCE_FLOOR:
        return _insufficient(
            scenario_text,
            asset_tag,
            "I don't have enough evidence to simulate this scenario.",
            (
                f"Nothing in the indexed documents relates to this change"
                f"{' for ' + asset_tag if asset_tag else ''}. "
                "Upload the relevant manual, procedure or safety standard, then try again."
            ),
        )

    # ---------------------------------------------------------------- assess
    findings = _collect_findings(scored)

    generation = await llm_gateway.execute_reasoning_pass(
        query=(
            f"An engineer proposes the following change"
            f"{' to ' + asset_tag if asset_tag else ''}: {scenario_text}\n"
            "Assess the operational and safety impact using only the sources."
        ),
        context_chunks=scored,
        mode="LOCAL",
        agent_directive=SIMULATOR_DIRECTIVE,
    )

    citations = [
        {
            "filename": c.get("filename", "Unknown source"),
            "excerpt": (c.get("matched_excerpt") or c.get("content", ""))[:400],
            "relevance": round(float(c.get("confidence_score", 0.0)), 4),
            "origin": c.get("origin_source", "UNKNOWN"),
        }
        for c in scored
    ]

    return {
        "scenario": scenario_text,
        "target_asset": asset_tag or "No specific asset",
        "has_sufficient_evidence": True,
        "refusal_reason": None,
        "guidance": None,
        "assessment": generation["text"],
        "applicable_limits": findings["limits"],
        "safety_warnings": findings["warnings"],
        "open_actions": findings["open_actions"],
        "citations": citations,
        "engine": generation["engine"],
        "evidence_strength": round(best_score, 4),
    }
