import re
from typing import Dict, Any
from app.services.agents.state import IndustryOSState

class SupervisorOrchestrator:
    """
    Core Supervisor Node in the LangGraph state machine.
    Performs deterministic, high-speed intent classification across 
    unstructured queries to assign specialized worker routing paths.
    """
    def __init__(self):
        # Explicit compilation of regex anchors for industrial domains to ensure sub-millisecond classification speed
        self.compliance_patterns = re.compile(
            r"\b(safety|compliance|violate|violation|regulation|osha|law|standard|illegal|hazard|protocol|epa|rule)\b", 
            re.IGNORECASE
        )
        self.maintenance_patterns = re.compile(
            r"\b(maintenance|repair|schedule|ticket|history|breakdown|fix|fail|failure|work order|clog|leak|serviced|replace)\b", 
            re.IGNORECASE
        )
        self.knowledge_patterns = re.compile(
            r"\b(manual|specification|spec|drawings|dimensions|operating range|limit|capacity|torque|pressure|psi|temperature|how to|blueprint)\b", 
            re.IGNORECASE
        )

    def classify_intent_node(self, state: IndustryOSState) -> Dict[str, Any]:
        """
        LangGraph node execution block. Evaluates the shared state clipboard 
        and updates the routing anchors dynamically.
        """
        query_text = state.get("query", "").strip()
        print(f"🕵️‍♂️ SUPERVISOR NODE: Evaluating incoming operator query: '{query_text}'")

        if not query_text:
            return {
                "current_agent": "compiler_node",
                "reasoning_path": ["supervisor_null_fallback"]
            }

        # Calculate keyword signal density weights
        compliance_hits = len(self.compliance_patterns.findall(query_text))
        maintenance_hits = len(self.maintenance_patterns.findall(query_text))
        knowledge_hits = len(self.knowledge_patterns.findall(query_text))

        print(f"📊 INTENT MATRIX WEIGHTS -> Compliance: {compliance_hits} | Maintenance: {maintenance_hits} | Knowledge: {knowledge_hits}")

        # Routing decision tree resolver logic
        target_agent = "compiler_node" # Default direct answer fallback
        routing_tag = "supervisor_direct_fallback"

        if compliance_hits > 0 and compliance_hits >= max(maintenance_hits, knowledge_hits):
            target_agent = "compliance_agent"
            routing_tag = "route_to_compliance"
        elif maintenance_hits > 0 and maintenance_hits >= max(compliance_hits, knowledge_hits):
            target_agent = "maintenance_agent"
            routing_tag = "route_to_maintenance"
        elif knowledge_hits > 0 and knowledge_hits >= max(compliance_hits, maintenance_hits):
            target_agent = "knowledge_agent"
            routing_tag = "route_to_knowledge"
        
        # If no explicit matches occur, perform a fast conversational fallback check
        if max(compliance_hits, maintenance_hits, knowledge_hits) == 0:
            print("💬 SUPERVISOR NODE: Direct conversational query identified. Routing directly to compiler.")
        else:
            print(f"🎯 SUPERVISOR NODE: Intent resolved. Dispatching to specialized agent: {target_agent}")

        # Return the dictionary delta updates. LangGraph applies these directly to our IndustryOSState object
        return {
            "current_agent": target_agent,
            "reasoning_path": [routing_tag]
        }

supervisor_orchestrator = SupervisorOrchestrator()