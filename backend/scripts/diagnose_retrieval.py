"""
Traces a query through every retrieval stage so a "not found" answer can be
explained: was nothing retrieved, or was it retrieved and then filtered out?

Usage:  python scripts/diagnose_retrieval.py "your question here"
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))


async def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else "What do the documents say about COMP-350?"

    from app.services.retrieval_hub import industrial_retrieval_hub
    from app.services.reranker import industrial_reranker
    from app.services.agents.workers import RELEVANCE_FLOOR
    from app.services.vector_store import vector_store_engine

    print(f"\nQUERY: {query!r}\n" + "=" * 70)

    print(f"\n[0] Vector store contains {vector_store_engine.collection.count()} vectors")

    # --- stage 1: hybrid retrieval -----------------------------------------
    candidates = await industrial_retrieval_hub.retrieve_hybrid_context(query, limit=8)
    print(f"\n[1] HYBRID RETRIEVAL -> {len(candidates)} candidates")
    for candidate in candidates:
        excerpt = (candidate.get("matched_excerpt") or candidate.get("content", ""))[:80]
        print(
            f"    {candidate.get('origin_source', '?')[:28]:30s} "
            f"{str(candidate.get('filename'))[:34]:36s} {excerpt!r}"
        )

    if not candidates:
        print("\n    Nothing retrieved. Either the vector index is empty or the")
        print("    embedding of this query matched nothing.")
        return

    # --- stage 2: rerank ----------------------------------------------------
    scored = industrial_reranker.filter_and_rerank_context(
        query_string=query, all_raw_candidates=candidates, top_n=4
    )
    print(f"\n[2] RERANK (top 4 of {len(candidates)})")
    for chunk in scored:
        print(
            f"    score={float(chunk.get('confidence_score', 0)):.6f}  "
            f"{str(chunk.get('filename'))[:34]:36s} "
            f"{(chunk.get('matched_excerpt') or '')[:60]!r}"
        )

    # --- stage 3: relevance floor -------------------------------------------
    best = max((float(c.get("confidence_score", 0.0)) for c in scored), default=0.0)
    print(f"\n[3] RELEVANCE FLOOR = {RELEVANCE_FLOOR}")
    print(f"    best score = {best:.6f}")
    if best < RELEVANCE_FLOOR:
        print("    -> ALL passages discarded. The answer will be 'not found'.")
        print("    -> This is the stage responsible for the refusal.")
    else:
        kept = [c for c in scored if float(c.get("confidence_score", 0.0)) >= 0]
        print(f"    -> {len(kept)} passage(s) kept. An answer WILL be produced.")


if __name__ == "__main__":
    asyncio.run(main())
