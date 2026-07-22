import asyncio
from app.services.retrieval_hub import industrial_retrieval_hub

async def test_end_to_end_retrieval_pass():
    print("🚀 INITIALIZING HYBRID GRAPH-RAG RETRIEVAL HUB RUNTIME CHECKS...")
    
    # 🎯 Test Query: Explicitly mentions an asset tag currently populated in your Neo4j node cluster
    test_query = "What is the maximum safety threshold limitation and PSI ceiling tolerance for PUMP-102?"
    
    candidates = await industrial_retrieval_hub.retrieve_hybrid_context(test_query, limit=5)
    
    print(f"\n🏆 DUAL-DATABASE RETRIEVAL AGGREGATION PASS COMPLETE!")
    print(f"📊 Total Distinct Candidates Extracted to Memory: {len(candidates)}")
    
    for idx, cand in enumerate(candidates):
        print(f"\n📍 Fragment Match Row [{idx + 1}]")
        print(f"   • Data Origin Pathway: {cand['origin_source']}")
        print(f"   • Reference Lineage File Name: {cand['filename']}")
        print(f"   • Context Preview Snippet: {cand['content'][:120]}...")
        print("-" * 75)

if __name__ == "__main__":
    asyncio.run(test_end_to_end_retrieval_pass())