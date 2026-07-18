import asyncio
from app.services.agent_orchestrator import industrial_agent_orchestrator

async def test_agent_graph_execution_pathway():
    print("🚀 INITIALIZING PHASE 10.3 MULTI-AGENT STATE GRAPH RUNTIME CHECK...")
    
    # Formulate a structured initial runtime state state array payload packet
    initial_state_payload = {
        "user_query": "What is the maximum safety threshold limitation and PSI ceiling tolerance for PUMP-102?",
        "extracted_assets": [],
        "retrieved_contexts": [],
        "draft_response": "",
        "audit_verdict": "",
        "iteration_count": 0,
        "system_logs": []
    }
    
    # Execute the compiled LangGraph engine out-of-band over memory channels
    final_output_state = await industrial_agent_orchestrator.ainvoke(initial_state_payload)
    
    print("\n📈 INTERNAL COGNITIVE RUNTIME LOG TRACE:")
    for log_line in final_output_state["system_logs"]:
        print(f"   {log_line}")
        
    print("\n👑 FINAL AGENT FABRICATED RESPONSE REPORT:")
    print(final_output_state["draft_response"])

if __name__ == "__main__":
    asyncio.run(test_agent_graph_execution_pathway())