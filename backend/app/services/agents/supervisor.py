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
            r"\b(safety|compliance|compliant|violat\w*|regulat\w*|osha|oisd|peso|law|legal|illegal|"
            r"standard|hazard|protocol|epa|rule|permit|certif\w*|audit|lockout|isolation|relief|"
            r"warning|caution|risk|breach|mandatory)\b",
            re.IGNORECASE
        )
        self.maintenance_patterns = re.compile(
            r"\b(maintenance|maintain|repair\w*|service\w*|schedul\w*|ticket|history|breakdown|fix\w*|"
            r"fail\w*|work.?order|clog\w*|leak\w*|replac\w*|overhaul|wear|degrad\w*|downtime|outage|"
            r"rebuild|refurbish|lubricat\w*|greas\w*|vibration|bearing|seal|impeller|past|previous|"
            r"last.time|when.did)\b",
            re.IGNORECASE
        )
        self.knowledge_patterns = re.compile(
            r"\b(manual|specification|spec|drawing\w*|dimension\w*|operating.range|limit\w*|capacity|"
            r"torque|pressure|psi|bar|temperature|celsius|rpm|gpm|flow|how.to|blueprint|rating|"
            r"sop|procedure|instruction|step\w*|startup|start.?up|shutdown|shut.?down|changeover|"
            r"commission\w*|operate|operating|checklist|setpoint|tolerance|threshold|datasheet|"
            r"part.number|model|design)\b",
            re.IGNORECASE
        )

        # Any equipment tag (PUMP-101, VALVE-220 ...) makes a query industrial even
        # when it contains none of the keywords above.
        from app.services.asset_tags import ASSET_TAG_PATTERN
        self.asset_tag_pattern = ASSET_TAG_PATTERN

        # Questions ABOUT the corpus rather than answerable FROM one passage.
        # No single passage says "these documents contradict each other", so these
        # must go to the deterministic conflict engine instead of RAG.
        self.conflict_patterns = re.compile(
            r"\b(conflict\w*|contradict\w*|discrepanc\w*|inconsisten\w*|mismatch\w*|"
            r"disagree\w*|differ\w*\s+values?|which\s+is\s+correct|out.of.date|supersed\w*)\b",
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
                "reasoning_path": ["supervisor_null_fallback"],
                "decision_trace": [{
                    "step": 1,
                    "node": "supervisor",
                    "title": "Intent Classification",
                    "status": "SKIPPED",
                    "detail": "Empty query received. No specialist agent dispatched."
                }]
            }

        # Calculate keyword signal density weights
        compliance_hits = len(self.compliance_patterns.findall(query_text))
        maintenance_hits = len(self.maintenance_patterns.findall(query_text))
        knowledge_hits = len(self.knowledge_patterns.findall(query_text))
        asset_tags = self.asset_tag_pattern.findall(query_text)

        print(f"📊 INTENT MATRIX WEIGHTS -> Compliance: {compliance_hits} | Maintenance: {maintenance_hits} | Knowledge: {knowledge_hits} | Asset tags: {len(asset_tags)}")

        # Routing decision tree resolver logic.
        # Conflict intent is checked FIRST: "are there conflicting pressure values?"
        # also matches the knowledge patterns, but only the conflict engine can
        # actually answer it.
        if self.conflict_patterns.search(query_text):
            target_agent = "conflict_agent"
            routing_tag = "route_to_conflict_analysis"
        elif compliance_hits > 0 and compliance_hits >= max(maintenance_hits, knowledge_hits):
            target_agent = "compliance_agent"
            routing_tag = "route_to_compliance"
        elif maintenance_hits > 0 and maintenance_hits >= max(compliance_hits, knowledge_hits):
            target_agent = "maintenance_agent"
            routing_tag = "route_to_maintenance"
        elif knowledge_hits > 0 and knowledge_hits >= max(compliance_hits, maintenance_hits):
            target_agent = "knowledge_agent"
            routing_tag = "route_to_knowledge"
        elif asset_tags:
            # Mentioning a real piece of equipment is itself a strong industrial signal.
            target_agent = "knowledge_agent"
            routing_tag = "route_to_knowledge_by_asset_tag"
        else:
            # ATTEMPT RETRIEVAL ANYWAY.
            #
            # Previously an unmatched query skipped retrieval entirely and returned
            # "that doesn't map to my domains" - which wrongly rejected valid questions
            # whose wording happened to miss the keyword lists (e.g. "Which SOP should
            # be followed before startup?").
            #
            # Keyword lists can never be complete, so they are now used only to choose
            # WHICH specialist runs. Whether we can actually answer is decided by
            # retrieval: if nothing relevant is found, the honest "not in your
            # documents" response is produced downstream with zero citations and zero
            # confidence. That is correct for both an unindexed industrial topic and
            # an off-domain question.
            target_agent = "knowledge_agent"
            routing_tag = "route_to_knowledge_unclassified"

        print(f"🎯 SUPERVISOR NODE: Intent resolved. Dispatching to specialized agent: {target_agent}")

        # Record the REAL classification evidence: the actual keyword hit counts that
        # drove the routing decision, and the agent that was actually selected.
        if routing_tag == "route_to_conflict_analysis":
            routing_detail = (
                "Recognised a question about contradictions between documents. "
                "Routed to the deterministic conflict engine, which compares parameter "
                "values across the whole corpus rather than retrieving single passages."
            )
        elif routing_tag == "route_to_knowledge_unclassified":
            routing_detail = (
                "No domain keywords matched "
                f"(compliance={compliance_hits}, maintenance={maintenance_hits}, knowledge={knowledge_hits}). "
                "Attempting document retrieval anyway - relevance of the retrieved passages, "
                "not keyword matching, decides whether this question can be answered."
            )
        elif routing_tag == "route_to_knowledge_by_asset_tag":
            routing_detail = (
                f"No domain keywords matched, but equipment tag(s) {sorted(set(t.upper() for t in asset_tags))} "
                "were recognised, so the query was routed to the knowledge agent."
            )
        else:
            routing_detail = (
                f"Keyword signal counts - compliance={compliance_hits}, "
                f"maintenance={maintenance_hits}, knowledge={knowledge_hits}. "
                f"Highest signal routed the query to '{target_agent}'."
            )

        # Return the dictionary delta updates. LangGraph applies these directly to our IndustryOSState object
        return {
            "current_agent": target_agent,
            "reasoning_path": [routing_tag],
            "decision_trace": [{
                "step": 1,
                "node": "supervisor",
                "title": "Intent Classification",
                "status": "COMPLETED",
                "detail": routing_detail,
                "metrics": {
                    "compliance_hits": compliance_hits,
                    "maintenance_hits": maintenance_hits,
                    "knowledge_hits": knowledge_hits,
                    "selected_agent": target_agent
                }
            }]
        }

supervisor_orchestrator = SupervisorOrchestrator()