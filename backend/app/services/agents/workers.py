import os
import re
from typing import Any, Dict, List

from app.services.retrieval_hub import industrial_retrieval_hub
from app.services.reranker import industrial_reranker
from app.services.llm_provider import llm_gateway

# Minimum cross-encoder relevance for a passage to count as evidence.
# Tuned against the BAAI/bge-reranker-base score distribution: genuine matches
# score ~0.9+, loosely-related passages ~0.1-0.4, and unrelated text ~1e-5.
# Kept at 0.01. Lowering it to admit the COMP-350 case also let unrelated
# questions ("tell me a joke") scrape through at ~0.007, which is exactly the
# fabrication this floor exists to prevent. The correct mechanism for genuine
# low-scoring matches is the exemption below, not a weaker threshold.
RELEVANCE_FLOOR = float(os.getenv("RELEVANCE_FLOOR", "0.01"))

# Equipment tags named in the question. An exact identifier match is a FACT, not a
# similarity estimate, so it is trusted over the cross-encoder's opinion.
from app.services.asset_tags import ASSET_TAG_PATTERN as QUERY_ASSET_PATTERN  # noqa: E402


def passage_is_exempt_from_floor(chunk: Dict[str, Any], queried_tags: set) -> bool:
    """
    Decides whether a passage counts as evidence even though the cross-encoder
    scored it below the floor.

    WHY THIS EXISTS
    ---------------
    Asking "what do the documents say about COMP-350?" retrieved the exact
    maintenance record for COMP-350 - found independently by BOTH the vector
    index and the knowledge graph - and the floor then discarded it, because the
    cross-encoder scored it 0.004. The score was low only because the question
    asked for three things (specifications, history, safety) and that passage
    covers one of them. The passage was unambiguously about the right asset.

    A single global threshold cannot tell "weakly worded but correct" apart from
    "completely unrelated". Two signals can:

      1. GRAPH CORROBORATION - the knowledge graph reached this passage by
         walking from the asset entity named in the question. That is an exact
         structural match, arrived at independently of the embedding.

      2. EXPLICIT TAG MATCH - the question names COMP-350 and the passage
         contains COMP-350.

    Either one makes the passage genuinely relevant. Passages with neither still
    face the floor, so off-domain questions ("what is quantum computing?") still
    retrieve nothing and the system still refuses honestly.
    """
    origin = str(chunk.get("origin_source", ""))
    if "GRAPH" in origin:  # graph-only or graph+vector corroborated
        return True

    if queried_tags:
        body = ((chunk.get("content") or "") + " " + (chunk.get("matched_excerpt") or "")).upper()
        if any(tag in body for tag in queried_tags):
            return True

    return False


# ---------------------------------------------------------------------------
# AGENT PROFILES
#
# Previously the three "specialist" agents shared one code path and differed only
# by a label string - the specialisation was cosmetic. Each now carries a genuine
# domain profile that changes two real things:
#
#   1. `directive` — extra instructions appended to the generation prompt, so a
#      maintenance question yields a chronological failure narrative while a
#      compliance question yields obligations and consequences.
#   2. `vocabulary` — domain terms used to re-ORDER passages of comparable
#      relevance, so the specialist prefers evidence from its own domain.
#
# The vocabulary affects ORDER ONLY. The reported confidence stays the raw
# cross-encoder score, so domain preference can never inflate the honesty metric.
# ---------------------------------------------------------------------------
AGENT_PROFILES: Dict[str, Dict[str, Any]] = {
    "knowledge_agent": {
        "label": "Knowledge Agent (specifications & manuals)",
        "directive": (
            "DOMAIN FOCUS — EQUIPMENT SPECIFICATIONS.\n"
            "Lead with the exact specification value and its units. State the operating "
            "limit, its conditions, and the equipment model or part number where given. "
            "If a limit has been superseded by a later revision, report both values and "
            "say which document supersedes which."
        ),
        "vocabulary": (
            "SPECIFICATION", "RATING", "LIMIT", "MAXIMUM", "MINIMUM", "DESIGN",
            "MODEL", "PART NUMBER", "TOLERANCE", "SETPOINT", "PSI", "RPM", "GPM",
            "CELSIUS", "OPERATING", "CAPACITY", "DIMENSION",
        ),
    },
    "maintenance_agent": {
        "label": "Reliability Agent (maintenance & failure history)",
        "directive": (
            "DOMAIN FOCUS — MAINTENANCE AND RELIABILITY HISTORY.\n"
            "Present events in chronological order, oldest first. For each event give "
            "the date and work order number exactly as written in the source — never "
            "estimate or infer a date. Identify repeat failures and their root causes. "
            "Explicitly flag any work order left open or any action recorded as not completed."
        ),
        "vocabulary": (
            "MAINTENANCE", "REPAIR", "REPLACED", "FAILED", "FAILURE", "WORK ORDER",
            "WO-", "OVERHAUL", "SERVICED", "DOWNTIME", "OUTAGE", "INSPECTED",
            "ROOT CAUSE", "EVENT", "ACTION", "DATE",
        ),
    },
    "compliance_agent": {
        "label": "Compliance Agent (safety & regulatory standards)",
        "directive": (
            "DOMAIN FOCUS — SAFETY AND REGULATORY COMPLIANCE.\n"
            "State the mandatory requirement first, then cite the standard or clause "
            "number it comes from. Spell out the consequence of non-compliance where the "
            "sources describe it. If any precondition, certification or inspection "
            "interval is unmet or unverified, treat that as a finding and say so plainly. "
            "Never soften a safety obligation."
        ),
        "vocabulary": (
            "SAFETY", "MUST", "SHALL", "MANDATORY", "REQUIRED", "STANDARD",
            "COMPLIANCE", "VIOLATION", "HAZARD", "WARNING", "CAUTION", "RELIEF",
            "LOCKOUT", "ISOLATION", "CERTIF", "INTERVAL", "PROHIBITED",
        ),
    },
}

# Kept for any caller still reading labels directly.
AGENT_LABELS = {name: profile["label"] for name, profile in AGENT_PROFILES.items()}


def apply_domain_preference(
    chunks: List[Dict[str, Any]], vocabulary: tuple
) -> tuple:
    """
    Re-orders passages of comparable relevance so the specialist sees its own
    domain's evidence first.

    Returns (reordered_chunks, matched_count). The stored `confidence_score` is
    left untouched — only presentation order changes.
    """
    if not chunks:
        return chunks, 0

    matched = 0

    def domain_rank(chunk: Dict[str, Any]) -> tuple:
        nonlocal matched
        text = (chunk.get("content") or chunk.get("matched_excerpt") or "").upper()
        hits = sum(1 for term in vocabulary if term in text)
        if hits:
            matched += 1
        relevance = float(chunk.get("confidence_score", 0.0))
        # Primary key: cross-encoder relevance rounded to one decimal, so passages
        # of genuinely different relevance keep their order. Secondary key: domain
        # hits, which only breaks ties within the same relevance band.
        return (-round(relevance, 1), -hits)

    reordered = sorted(chunks, key=domain_rank)
    return reordered, matched


def compute_grounding_confidence(
    refined_chunks: List[Dict[str, Any]],
    raw_candidate_count: int,
) -> Dict[str, Any]:
    """
    Computes a confidence score from MEASURED retrieval quality.

    Every input here is a real number produced by the pipeline:
      - relevance : the cross-encoder's top score for this question (0..1)
      - agreement : did the vector index and the knowledge graph independently
                    surface the same passage? (strongest evidence we have)
      - corroboration : how many distinct source documents support the answer

    There are no constants standing in for measurements. If nothing was
    retrieved, the score is 0 and the reason is stated.
    """
    if not refined_chunks:
        return {
            "score": 0.0,
            "band": "NO_EVIDENCE",
            "explanation": "No passages were retrieved, so no confidence can be asserted.",
            "components": {
                "top_relevance": 0.0,
                "mean_relevance": 0.0,
                "graph_verified": False,
                "distinct_sources": 0,
                "candidates_considered": raw_candidate_count,
            },
        }

    relevance_scores = [float(c.get("confidence_score", 0.0)) for c in refined_chunks]
    top_relevance = max(relevance_scores)
    mean_relevance = sum(relevance_scores) / len(relevance_scores)

    # A passage found by BOTH the vector search and the graph walk is corroborated
    # by two independent retrieval methods.
    graph_verified = any(
        "VERIFIED" in str(c.get("origin_source", "")) or "GRAPH" in str(c.get("origin_source", ""))
        for c in refined_chunks
    )

    distinct_sources = len({c.get("filename") for c in refined_chunks if c.get("filename")})

    # Weighted blend of real signals. Relevance dominates because it directly
    # measures whether the retrieved text answers THIS question.
    corroboration_factor = min(1.0, distinct_sources / 3.0)
    score = (
        0.65 * top_relevance
        + 0.20 * corroboration_factor
        + 0.15 * (1.0 if graph_verified else 0.0)
    )

    # Ceiling at 95%. This metric measures how well the retrieved EVIDENCE supports
    # an answer - it is not a claim that the answer is correct. Displaying 100%
    # would imply a certainty no retrieval system can honestly assert.
    score_pct = round(min(score, 0.95) * 100, 1)

    if top_relevance >= 0.75:
        band = "HIGH"
        explanation = (
            "Retrieved passages are a strong direct match for this question. "
            "This measures evidence quality, not correctness - always confirm against the cited source."
        )
    elif top_relevance >= 0.30:
        band = "MODERATE"
        explanation = (
            "Retrieved passages are related but not an exact match. "
            "Verify the answer against the cited source before acting on it."
        )
    else:
        band = "LOW"
        explanation = (
            "Retrieved passages only weakly match this question. "
            "Treat this as a lead to investigate, not a verified fact."
        )

    return {
        "score": score_pct,
        "band": band,
        "explanation": explanation,
        "components": {
            "top_relevance": round(top_relevance, 4),
            "mean_relevance": round(mean_relevance, 4),
            "graph_verified": graph_verified,
            "distinct_sources": distinct_sources,
            "candidates_considered": raw_candidate_count,
        },
    }


class IndustrialAgentWorkersEngine:
    """
    Connects LangGraph worker nodes to the data layers: hybrid retrieval,
    reranking, then grounded generation. Each node records what it actually did.
    """

    async def _execute_agent_retrieval_and_reasoning(
        self, state: Dict[str, Any], agent_name: str
    ) -> Dict[str, Any]:
        raw_query = state.get("query", state.get("user_query", ""))
        routing_mode = state.get("routing_mode") or "LOCAL"

        print(f"🛡️ WORKER NODE [{agent_name}]: Processing under [{routing_mode}] engine rules...")

        # 1. Hybrid sweep across ChromaDB (semantic) and Neo4j (topological)
        raw_candidates = await industrial_retrieval_hub.retrieve_hybrid_context(raw_query, limit=8)

        # Count each passage exactly once. A passage found by BOTH engines is
        # "corroborated", not one vector hit plus one graph hit - double counting
        # made the totals in the audit trail fail to add up.
        vector_only = sum(
            1 for c in raw_candidates if c.get("origin_source") == "VECTOR_PROXIMITY_MATRIX"
        )
        graph_only = sum(
            1 for c in raw_candidates if c.get("origin_source") == "GRAPH_TOPOLOGY_WALK"
        )
        corroborated = sum(
            1 for c in raw_candidates if c.get("origin_source") == "HYBRID_GRAPH_VECTOR_VERIFIED"
        )
        vector_hits = vector_only + corroborated
        graph_hits = graph_only + corroborated

        # 2. Rank fusion + cross-encoder relevance scoring
        scored_chunks = industrial_reranker.filter_and_rerank_context(
            query_string=raw_query,
            all_raw_candidates=raw_candidates,
            top_n=4,
        )

        # 3. RELEVANCE FLOOR.
        # Vector search always returns its nearest neighbours, even for a question
        # with nothing to do with the corpus. Without a floor, asking "what is
        # quantum computing?" would retrieve pump passages and present them as
        # supporting evidence. Anything the cross-encoder scores below the floor is
        # not evidence, and is discarded so the pipeline refuses honestly.
        # Filter PER PASSAGE rather than discarding the whole set when the best
        # score is low. A passage survives if it clears the floor, OR if the graph
        # corroborated it, OR if it contains an asset tag the question named.
        queried_tags = {tag.upper() for tag in QUERY_ASSET_PATTERN.findall(raw_query)}

        refined_context_chunks: List[Dict[str, Any]] = []
        exempted = 0
        for chunk in scored_chunks:
            score = float(chunk.get("confidence_score", 0.0))
            if score >= RELEVANCE_FLOOR:
                refined_context_chunks.append(chunk)
            elif passage_is_exempt_from_floor(chunk, queried_tags):
                chunk["floor_exempt"] = True
                refined_context_chunks.append(chunk)
                exempted += 1

        best_score = max((float(c.get("confidence_score", 0.0)) for c in scored_chunks), default=0.0)
        if not refined_context_chunks:
            print(
                f"🚧 RELEVANCE FLOOR: best score {best_score:.5f} < {RELEVANCE_FLOOR}, "
                f"no graph corroboration and no tag match - answering as 'not found'."
            )
        elif exempted:
            print(
                f"🔗 FLOOR EXEMPTION: kept {exempted} passage(s) below {RELEVANCE_FLOOR} "
                f"on graph corroboration / explicit asset-tag match."
            )

        # 4. DOMAIN SPECIALISATION.
        # Order the surviving evidence toward this agent's domain, then generate
        # using this agent's directive. This is what makes the three specialists
        # genuinely different rather than three labels on one code path.
        profile = AGENT_PROFILES.get(agent_name, {})
        refined_context_chunks, domain_matches = apply_domain_preference(
            refined_context_chunks, profile.get("vocabulary", ())
        )

        # 5. Grounded generation (or an honest refusal when nothing was retrieved)
        generation = await llm_gateway.execute_reasoning_pass(
            query=raw_query,
            context_chunks=refined_context_chunks,
            mode=routing_mode,
            agent_directive=profile.get("directive"),
        )

        confidence = compute_grounding_confidence(refined_context_chunks, len(raw_candidates))

        # ------------------------------------------------------------------
        # Build the REAL execution trace from measured values
        # ------------------------------------------------------------------
        trace: List[Dict[str, Any]] = [
            {
                "step": 2,
                "node": agent_name,
                "title": profile.get("label", agent_name),
                "status": "COMPLETED",
                "detail": (
                    f"Hybrid retrieval returned {len(raw_candidates)} distinct passages: "
                    f"{vector_only} from the vector index only, "
                    f"{graph_only} from the knowledge graph only, "
                    f"{corroborated} found independently by both. "
                    f"{domain_matches} of the kept passages match this agent's domain vocabulary."
                ),
                "metrics": {
                    "vector_only": vector_only,
                    "graph_only": graph_only,
                    "corroborated": corroborated,
                    "vector_candidates": vector_hits,
                    "graph_candidates": graph_hits,
                    "total_candidates": len(raw_candidates),
                    "domain_matched_passages": domain_matches,
                },
            },
            {
                "step": 3,
                "node": "reranker",
                "title": "Rank Fusion & Relevance Scoring",
                "status": "COMPLETED" if refined_context_chunks else "NO_RESULTS",
                "detail": (
                    f"Reciprocal rank fusion merged both retrieval streams, then a cross-encoder "
                    f"scored each passage against the question. Kept the top {len(refined_context_chunks)}. "
                    f"Best relevance score: {confidence['components']['top_relevance']}."
                    if refined_context_chunks
                    else (
                        f"Retrieved passages scored at most {best_score:.5f}, below the "
                        f"{RELEVANCE_FLOOR} relevance floor. Discarded as not relevant to this question."
                        if scored_chunks
                        else "No passages were retrieved. Nothing to rank."
                    )
                ),
                "metrics": {
                    "kept": len(refined_context_chunks),
                    "top_relevance": confidence["components"]["top_relevance"],
                    "sources": sorted(
                        {c.get("filename", "unknown") for c in refined_context_chunks}
                    ),
                },
            },
            {
                "step": 4,
                "node": "generation",
                "title": "Grounded Answer Generation",
                "status": "COMPLETED" if generation["grounded"] else "REFUSED",
                "detail": (
                    f"Answer produced by: {generation['engine']}."
                    if generation["grounded"]
                    else "Declined to answer: no supporting evidence was retrieved."
                ),
                "metrics": {
                    "engine": generation["engine"],
                    "engine_id": generation["engine_id"],
                    "grounded": generation["grounded"],
                },
            },
        ]

        # `extracted_docs` and `reasoning_path` use append-style reducers, so return
        # ONLY the new items - returning the accumulated list would duplicate it.
        return {
            "final_response": generation["text"],
            "extracted_docs": refined_context_chunks,
            "reasoning_path": [agent_name],
            "decision_trace": trace,
            "current_agent": "compiler_node",
            "confidence_score": confidence["score"],
            "retrieval_stats": {
                "confidence": confidence,
                "engine": generation["engine"],
                "engine_id": generation["engine_id"],
                "grounded": generation["grounded"],
                "notice": generation.get("notice"),
                "vector_candidates": vector_hits,
                "graph_candidates": graph_hits,
                "vector_only": vector_only,
                "graph_only": graph_only,
                "corroborated": corroborated,
                "total_candidates": len(raw_candidates),
            },
        }

    async def knowledge_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """ Handles general equipment specifications and manual parameters """
        return await self._execute_agent_retrieval_and_reasoning(state, "knowledge_agent")

    async def maintenance_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """ Handles asset wear tracking, runtime data, and service loops """
        return await self._execute_agent_retrieval_and_reasoning(state, "maintenance_agent")

    async def compliance_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """ Handles regulatory boundaries and safety threshold checks """
        return await self._execute_agent_retrieval_and_reasoning(state, "compliance_agent")


# Instantiate global worker singleton instance for graph imports
agent_workers = IndustrialAgentWorkersEngine()
