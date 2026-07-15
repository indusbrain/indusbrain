from langgraph.graph import StateGraph, END
from app.services.agents.state import IndustryOSState
from app.services.agents.supervisor import supervisor_orchestrator
from app.services.agents.workers import agent_workers
from app.services.agents.compiler import decision_compiler

# 1. Initialize the State Graph with our custom state schema
workflow = StateGraph(IndustryOSState)

# 2. Register all active processing nodes in the network
workflow.add_node("supervisor", supervisor_orchestrator.classify_intent_node)
workflow.add_node("knowledge_agent", agent_workers.knowledge_agent_node)
workflow.add_node("maintenance_agent", agent_workers.maintenance_agent_node)
workflow.add_node("compliance_agent", agent_workers.compliance_agent_node)
workflow.add_node("compiler_node", decision_compiler.compile_response_node)

# 3. Define the starting entry point of the graph execution path
workflow.set_entry_point("supervisor")

# 4. Implement the Conditional Router Routing Logic
def route_after_supervisor(state: IndustryOSState) -> str:
    """
    Conditional router that directs the execution path to the
    specialized agent assigned by the supervisor.
    """
    next_agent = state.get("current_agent", "compiler_node")
    print(f"🔀 GRAPH ROUTER: Directing state-machine execution flow straight to: {next_agent}")
    return next_agent

# 5. Connect the nodes with edges
# The supervisor routes dynamically to a worker node
workflow.add_conditional_edges(
    "supervisor",
    route_after_supervisor,
    {
        "knowledge_agent": "knowledge_agent",
        "maintenance_agent": "maintenance_agent",
        "compliance_agent": "compliance_agent",
        "compiler_node": "compiler_node"
    }
)

# All specialized worker nodes feed their findings directly into the compiler node
workflow.add_edge("knowledge_agent", "compiler_node")
workflow.add_edge("maintenance_agent", "compiler_node")
workflow.add_edge("compliance_agent", "compiler_node")

# The compiler node is the final step, ending the execution loop
workflow.add_edge("compiler_node", END)

# 6. Compile the workflow into a runnable engine
compiled_agent_workflow = workflow.compile()
print("🏆 LANGGRAPH MATRIX: Complete Multi-Agent Workflow Graph Compiled Successfully!")