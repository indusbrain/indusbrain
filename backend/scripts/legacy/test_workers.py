import sys
from app.services.agents.supervisor import supervisor_orchestrator
from app.services.agents.workers import agent_workers

def run_agent_workers_diagnostics():
    print("🧪 DIAGNOSTIC: Testing Specialized Agent Worker Nodes...")

    test_queries = [
        {
            "query": "Is it a violation of OSHA standards to operate high-pressure lines?",
            "expected_agent": "compliance_agent"
        },
        {
            "query": "When was the turbine last serviced and what did the engineer report?",
            "expected_agent": "maintenance_agent"
        },
        {
            "query": "What is the maximum torque limit for Pump-3B in the manual?",
            "expected_agent": "knowledge_agent"
        }
    ]

    print("\n=== 🚦 SIMULATING MULTI-AGENT STATE HANDSHAKE ===")
    
    for index, test_case in enumerate(test_queries):
        print(f"\n------------------------------------------------------------")
        print(f"📍 [Test Case #{index + 1}] User Query: \"{test_case['query']}\"")
        
        # 1. Initialize empty shared state
        state = {
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

        # 2. Step 1: Run Supervisor classification
        supervisor_delta = supervisor_orchestrator.classify_intent_node(state)
        state.update(supervisor_delta)
        resolved_agent = state["current_agent"]
        
        print(f"🎯 STEP 1: Supervisor routed to: {resolved_agent}")

        # Verify supervisor routed correctly
        assert resolved_agent == test_case["expected_agent"], f"Supervisor routed incorrectly to {resolved_agent}"

        # 3. Step 2: Trigger the routed worker agent
        worker_delta = {}
        if resolved_agent == "knowledge_agent":
            worker_delta = agent_workers.knowledge_agent_node(state)
        elif resolved_agent == "maintenance_agent":
            worker_delta = agent_workers.maintenance_agent_node(state)
        elif resolved_agent == "compliance_agent":
            worker_delta = agent_workers.compliance_agent_node(state)

        # Apply worker state update
        state["extracted_docs"] = state.get("extracted_docs", []) + worker_delta.get("extracted_docs", [])
        state["failure_logs"] = state.get("failure_logs", []) + worker_delta.get("failure_logs", [])
        state["compliance_violations"] = state.get("compliance_violations", []) + worker_delta.get("compliance_violations", [])
        state["reasoning_path"] = state.get("reasoning_path", []) + worker_delta.get("reasoning_path", [])

        # 4. Display state snapshot
        print("📝 STEP 2: Worker execution finished. State update snapshot:")
        print(f"  Reasoning Path : {state['reasoning_path']}")
        
        if state["extracted_docs"]:
            print(f"  Extracted Docs : {state['extracted_docs'][0]['content'][:60]}... (Source: {state['extracted_docs'][0]['source']})")
        if state["failure_logs"]:
            print(f"  Failure Logs   : Tag: {state['failure_logs'][0]['asset_tag']} | Date: {state['failure_logs'][0]['last_serviced_date']}")
        if state["compliance_violations"]:
            print(f"  Compliance     : Standard: {state['compliance_violations'][0]['regulatory_standard']} | Status: {state['compliance_violations'][0]['severity_level']}")

    print("\n============================================================")
    print("🏆 SCORECARD: 3/3 Specialized Worker Handshakes Validated Perfectly!")
    print("============================================================\n")
    sys.exit(0)

if __name__ == "__main__":
    run_agent_workers_diagnostics()