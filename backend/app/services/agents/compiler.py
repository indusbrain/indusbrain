from typing import Dict, Any

class DecisionCompilerNode:
    """ Final assembly node. Compiles intermediate states into the final response payload. """
    
    def compile_response_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        print("🧠 COMPILER NODE: Finalizing response synthesis pass...")
        
        # Ensure the final answer string is preserved correctly
        final_answer = state.get("final_response", "Failed to compile final report.")
        
        return {
            "final_response": final_answer,
            "current_agent": "compiler_node"
        }

decision_compiler = DecisionCompilerNode()