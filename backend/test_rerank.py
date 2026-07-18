import asyncio
from app.services.retrieval_hub import industrial_retrieval_hub
from app.services.reranker import industrial_reranker

async def test_semantic_reranking_pipeline():
    print("🚀 INITIALIZING PHASE 10.2 SEMANTIC RERANKING INTEGRATION TESTING...")
    
    test_query = "What is the maximum safety threshold limitation and PSI ceiling tolerance for PUMP-102?"
    
    # 1. Gather raw data components using your Sub-Phase 10.1 retrieval hub
    raw_mixed_candidates = await industrial_retrieval_hub.retrieve_hybrid_context(test_query, limit=6)
    print(f"\n📥 RETRIEVAL PHASE COMPLETE: Gathered {len(raw_mixed_candidates)} raw candidate fragments.")
    
    # 2. Filter data and run the reranking scoring system
    refined_context_chunks = industrial_reranker.filter_and_rerank_context(
        query_string=test_query,
        all_raw_candidates=raw_mixed_candidates,
        top_n=3 # Restrict final array payload output to the top 3 highest-quality matches
    )
    
    print(f"\n🏆 RERANKING COMPLETED SUCCESSFULLY!")
    print(f"📋 Top {len(refined_context_chunks)} Final Verified Context Blocks Routed to Agents:")
    
    for idx, chunk in enumerate(refined_context_chunks):
        print(f"\n🔥 [Rank POSITION #{idx + 1}] ──► Confidence Affinity Score: {chunk['confidence_score']:.4f}")
        print(f"   • RRF Placement Value: {chunk['rrf_score']:.5f}")
        print(f"   • Database Origin Path: {chunk['origin_source']}")
        print(f"   • Source Manual Origin: {chunk['filename']}")
        print(f"   • Fact Text Snippet: {chunk['content'].strip()[:140]}...")
        print("-" * 80)

if __name__ == "__main__":
    asyncio.run(test_semantic_reranking_pipeline())
    