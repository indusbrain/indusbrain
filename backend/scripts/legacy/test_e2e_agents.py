import sys
from app.services.agents.graph import compiled_agent_workflow

def run_e2e_agent_workflow_diagnostic():
    print("🚀 DIAGNOSTIC: Testing Complete LangGraph Multi-Agent Workflow Engine...")

    test_query = "When was the turbine last serviced, and does it violate osha pressure guidelines?"
    
    # Initialize the master shared state dictionary
    initial_state = {
        "query": test_query,
        "current_agent": "orchestrator",
        "extracted_docs": [],
        "graph_entities": [],
        "compliance_violations": [],
        "failure_logs": [],
        "reasoning_path": [],
        "confidence_score": 0.0,
        "final_response": ""
    }

    print(f"\n==================== STARTING GRAPH EXECUTION ====================")
    print(f"User Query: \"{test_query}\"")
    print(f"==================================================================\n")

    try:
        # Run the entire graph state machine
        final_state = compiled_agent_workflow.invoke(initial_state)
        
        print(f"\n==================== GRAPH EXECUTION COMPLETE ====================")
        print("🏆 SUCCESS! Final Compiled State Snapshot:")
        print(f"  Reasoning Path   : {final_state['reasoning_path']}")
        print(f"  Confidence Score : {final_state['confidence_score']}")
        print(f"\n--- Generated Response ---")
        print(final_state['final_response'])
        print(f"--------------------------")
        print(f"==================================================================\n")
        
        sys.exit(0)
    except Exception as e:
        print(f"❌ STATE MACHINE CRASHED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_e2e_agent_workflow_diagnostic()