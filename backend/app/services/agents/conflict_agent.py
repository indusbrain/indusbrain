"""
Conflict agent.

Some questions are ABOUT the corpus rather than answerable FROM a single passage:
"are there conflicting pressure values?", "do any documents contradict each other?".

Passage retrieval cannot answer these, because no individual passage states that a
contradiction exists - the contradiction is an emergent property of two documents
compared together. Routing such questions through normal RAG produced a
(correct but unhelpful) "not found" response.

This node answers them from the real conflict engine instead.
"""

from typing import Any, Dict, List

from sqlalchemy import select

from app.database import async_session_local
from app.models.chunk import KnowledgeChunk
from app.models.document import KnowledgeDocument
from app.services.conflict_engine import industrial_conflict_engine


async def load_corpus_for_conflict_scan() -> List[Dict[str, str]]:
    """Reads every indexed passage with its source filename."""
    async with async_session_local() as session:
        result = await session.execute(
            select(KnowledgeChunk.content, KnowledgeDocument.filename).join(
                KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id
            )
        )
        rows = result.all()

    payload = []
    for content, filename in rows:
        text = content or ""
        # Chunks are stored as "child ||| parent"; the parent holds fuller context.
        if " ||| " in text:
            text = text.split(" ||| ", 1)[1]
        payload.append({"content": text, "filename": filename})
    return payload


def render_conflict_report(findings: List[Dict[str, Any]], documents_scanned: int) -> str:
    """Formats real conflict findings as an operator-facing answer."""
    if not findings:
        return (
            "No contradictions were found.\n\n"
            f"I compared every parameter value across {documents_scanned} indexed passages. "
            "No two documents state materially different values for the same parameter on "
            "the same asset."
        )

    lines = [
        f"**{len(findings)} contradiction{'s' if len(findings) != 1 else ''} found between your documents.**",
        "",
    ]

    for index, finding in enumerate(findings, start=1):
        lines.append(
            f"**{index}. {finding['asset_tag']} — {finding['parameter']} "
            f"({finding['severity'].lower()})**"
        )
        lines.append("")
        lines.append(
            f"- `{finding['low_source']}` states **{finding['low_value']} {finding['unit']}**"
        )
        lines.append(
            f"- `{finding['high_source']}` states **{finding['high_value']} {finding['unit']}**"
        )
        lines.append(
            f"- Difference of {finding['variance']} {finding['unit']} exceeds the "
            f"acceptable tolerance."
        )
        lines.append("")
        lines.append(f"> {finding['recommended_action']}")
        lines.append("")

    lines.append(
        "Each value above is quoted from the documents themselves. "
        "Until an engineer formally resolves a conflict, apply the lower limit."
    )
    return "\n".join(lines)


class ConflictAgentNode:
    """LangGraph node that answers corpus-level contradiction questions."""

    async def detect_conflicts_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        print("⚖️ CONFLICT AGENT: Running cross-document contradiction analysis...")

        corpus = await load_corpus_for_conflict_scan()
        document_names = {chunk["filename"] for chunk in corpus}
        report = industrial_conflict_engine.analyze_context_slices(corpus)
        findings = report["detected_anomalies"]

        answer = render_conflict_report(findings, len(corpus))

        # Cite the documents that actually participate in each contradiction.
        citations: List[Dict[str, Any]] = []
        for finding in findings:
            for source_key, context_key, value_key in (
                ("low_source", "low_context", "low_value"),
                ("high_source", "high_context", "high_value"),
            ):
                citations.append({
                    "content": finding[context_key],
                    "matched_excerpt": finding[context_key],
                    "filename": finding[source_key],
                    "document_id": None,
                    "chunk_index": None,
                    "origin_source": "CONFLICT_ANALYSIS",
                    # Deterministic analysis, not a probabilistic match.
                    "confidence_score": 1.0,
                })

        confidence = {
            "score": 90.0 if findings else 75.0,
            "band": "HIGH" if findings else "MODERATE",
            "explanation": (
                "Derived by directly comparing parameter values across documents, "
                "not by semantic similarity. Every figure is quoted from the source."
                if findings
                else "The full corpus was compared and no contradictory values were found."
            ),
            "components": {
                "top_relevance": 1.0 if findings else 0.0,
                "mean_relevance": 1.0 if findings else 0.0,
                "graph_verified": False,
                "distinct_sources": len(
                    {c["filename"] for c in citations}
                ) if citations else 0,
                "candidates_considered": len(corpus),
            },
        }

        trace = [
            {
                "step": 2,
                "node": "conflict_agent",
                "title": "Cross-Document Conflict Analysis",
                "status": "COMPLETED",
                "detail": (
                    f"Compared parameter values across {len(corpus)} passages from "
                    f"{len(document_names)} documents. Found {len(findings)} contradiction(s)."
                ),
                "metrics": {
                    "passages_scanned": len(corpus),
                    "documents_scanned": len(document_names),
                    "conflicts_found": len(findings),
                },
            },
            {
                "step": 3,
                "node": "generation",
                "title": "Conflict Report Assembly",
                "status": "COMPLETED",
                "detail": "Report built directly from measured values — no language model inference.",
                "metrics": {"engine": "Deterministic conflict engine", "grounded": True},
            },
        ]

        return {
            "final_response": answer,
            "extracted_docs": citations,
            "reasoning_path": ["conflict_agent"],
            "decision_trace": trace,
            "current_agent": "compiler_node",
            "confidence_score": confidence["score"],
            "retrieval_stats": {
                "confidence": confidence,
                "engine": "Deterministic conflict engine (no model inference)",
                "engine_id": "conflict_engine",
                "grounded": True,
                "notice": None,
                "vector_candidates": 0,
                "graph_candidates": 0,
                "total_candidates": len(corpus),
            },
        }


conflict_agent = ConflictAgentNode()
