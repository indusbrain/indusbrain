from typing import Any, Dict


class DecisionCompilerNode:
    """
    Final assembly node. Closes out the execution trace and guarantees the
    response is never an internal error string leaking to the operator.
    """

    def compile_response_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        print("🧠 COMPILER NODE: Finalizing response synthesis pass...")

        final_answer = (state.get("final_response") or "").strip()
        retrieved = state.get("extracted_docs") or []
        reasoning_path = state.get("reasoning_path") or []

        # The supervisor routes here directly when a question matches no industrial
        # domain (e.g. small talk). In that case no retrieval ever ran, and we must
        # say so rather than emitting an internal error string.
        no_specialist_ran = not any(str(step).endswith("_agent") for step in reasoning_path)

        if not final_answer:
            if no_specialist_ran:
                final_answer = (
                    "That question doesn't map to any of the industrial domains I cover "
                    "(equipment specifications, maintenance history, or safety compliance).\n\n"
                    "Try asking about a specific asset tag, a procedure, a component "
                    "specification, or a safety standard."
                )
            else:
                final_answer = (
                    "I could not construct an answer from the indexed documents. "
                    "No supporting passages were retrieved for this question."
                )

        trace_entry = {
            "step": 5,
            "node": "compiler",
            "title": "Response Assembly",
            "status": "COMPLETED",
            "detail": (
                f"Final answer assembled from {len(retrieved)} cited passage(s)."
                if retrieved
                else "No passages were cited. Returned an explicit no-evidence response."
            ),
            "metrics": {"cited_passages": len(retrieved)},
        }

        return {
            "final_response": final_answer,
            "current_agent": "compiler_node",
            "decision_trace": [trace_entry],
        }


decision_compiler = DecisionCompilerNode()
