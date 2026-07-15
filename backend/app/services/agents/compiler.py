import os
from typing import Dict, Any
from app.services.agents.state import IndustryOSState

class DecisionIntelligenceCompiler:
    """
    Final consolidation node in the LangGraph multi-agent system.
    Synthesizes all gathered data from specialized worker agents
    into a structured, professional response.
    """
    def __init__(self):
        self.app_env = os.getenv("APP_ENV", "development")

    def compile_response_node(self, state: IndustryOSState) -> Dict[str, Any]:
        """
        Processes the accumulated state clipboard data and generates
        the final response.
        """
        print("🧠 COMPILER NODE: Reviewing clipboard to synthesize final response...")

        query = state.get("query", "")
        extracted_docs = state.get("extracted_docs", [])
        failure_logs = state.get("failure_logs", [])
        compliance_violations = state.get("compliance_violations", [])
        
        # Calculate confidence score based on data availability
        confidence = 0.5
        if extracted_docs: confidence += 0.2
        if failure_logs: confidence += 0.15
        if compliance_violations: confidence += 0.15
        confidence = min(confidence, 1.0)

        # Build a highly structured, professional synthesis report
        response_sections = []
        response_sections.append(f"### ⚙️ Industrial Intelligence Report")
        response_sections.append(f"**Operator Query:** *\"{query}\"*\n")

        # 1. Integrate Technical Specifications
        if extracted_docs:
            response_sections.append("#### 📖 Technical Specifications & Manual References")
            for doc in extracted_docs:
                response_sections.append(
                    f"- **Source:** {doc.get('source', 'Manual')} (Page {doc.get('page_number', 'N/A')})\n"
                    f"  ```text\n  {doc.get('content', '').strip()}\n  ```"
                )
        else:
            response_sections.append("#### 📖 Technical Specifications\n- *No direct technical specifications were retrieved from the knowledge vault.*")

        # 2. Integrate Machinery Health & Maintenance History
        if failure_logs:
            response_sections.append("\n#### 🔧 Asset Maintenance History & Status")
            for log in failure_logs:
                response_sections.append(
                    f"- **Asset Tag:** `{log.get('asset_tag')}`\n"
                    f"- **Last Serviced:** {log.get('last_serviced_date')} | **Status:** {log.get('operational_status')}\n"
                    f"- **Maintenance Log Notes:** *\"{log.get('engineer_notes')}\"*"
                )

        # 3. Integrate Regulatory Safety Audits
        if compliance_violations:
            response_sections.append("\n#### 🛡️ Operational Safety & Compliance Audits")
            for violation in compliance_violations:
                severity_tag = "🔴 CRITICAL WARNING" if violation.get("severity_level") == "CRITICAL" else "⚠️ NOMINAL PROTOCOL"
                response_sections.append(
                    f"- **Standard:** {violation.get('regulatory_standard')} ({severity_tag})\n"
                    f"- **Safety Hazard:** *{violation.get('hazard_description')}*\n"
                    f"- **Required Action:** **{violation.get('remediation_directive')}**"
                )

        # 4. Generate the Final Executive Summary (Simulating LLM synthesis)
        response_sections.append("\n#### 💡 Executive Action Directive")
        if compliance_violations and any(v.get("severity_level") == "CRITICAL" for v in compliance_violations):
            response_sections.append(
                "**URGENT:** Operational safety hazards have been flagged for this procedure. "
                "Do not initiate work until lock-out/tag-out procedures are verified, "
                "the line is fully depressurized, and proper PPE is equipped."
            )
        else:
            response_sections.append(
                "Operations may proceed under standard maintenance protocols. Ensure work order "
                "documentation is updated upon completion of the task."
            )

        final_markdown_response = "\n".join(response_sections)

        return {
            "final_response": final_markdown_response,
            "confidence_score": confidence,
            "reasoning_path": ["decision_intelligence_compilation_complete"]
        }

decision_compiler = DecisionIntelligenceCompiler()