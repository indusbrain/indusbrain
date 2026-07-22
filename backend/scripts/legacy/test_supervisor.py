import sys
from app.services.agents.supervisor import supervisor_orchestrator

def run_supervisor_diagnostics():
    print("🧪 DIAGNOSTIC: Testing Orchestrator Supervisor Routing Engine...")
    
    test_queries = [
        {
            "query": "Is it a violation of OSHA standards to operate a high-pressure line without a secondary pressure venting valve?",
            "expected": "compliance_agent"
        },
        {
            "query": "When was the primary steam turbine last serviced and did the engineer report any micro-fractures in the housing?",
            "expected": "maintenance_agent"
        },
        {
            "query": "What is the maximum allowable operating torque and PSI boundary for the Type-B Centrifugal Pump?",
            "expected": "knowledge_agent"
        },
        {
            "query": "Good morning! Can you help me out today on the factory floor?",
            "expected": "compiler_node"
        }
    ]

    success_count = 0
    
    print("\n=== 🚦 RUNNING SUPERVISOR INTENT CLASSIFICATION MATCHES ===")
    for index, test_case in enumerate(test_queries):
        # Simulate our central state clipboard dictionary structure
        simulated_state = {
            "query": test_case["query"],
            "current_agent": "orchestrator",
            "extracted_docs": [],
            "graph_entities": [],
            "compliance_violations": [],
            "failure_logs": [],
            "reasoning_path": [],
            "confidence_score": 0.0,
            "final_response": ""
        }
        
        # Trigger the node evaluation
        state_delta = supervisor_orchestrator.classify_intent_node(simulated_state)
        resolved_agent = state_delta["current_agent"]
        reasoning = state_delta["reasoning_path"][0]
        
        is_correct = (resolved_agent == test_case["expected"])
        status_symbol = "🟢 PASS" if is_correct else "❌ FAIL"
        
        if is_correct:
            success_count += 1
            
        print(f"\n[Test Case #{index + 1}]")
        print(f"  Operator Query : \"{test_case['query']}\"")
        print(f"  Resolved Agent : {resolved_agent} ({reasoning})")
        print(f"  Verification   : {status_symbol} (Expected: {test_case['expected']})")
    
    print("\n============================================================")
    print(f"🏆 SCORECARD: {success_count}/{len(test_queries)} Intent Classifications Resolved Perfectly!")
    print("============================================================\n")
    
    if success_count == len(test_queries):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    run_supervisor_diagnostics()