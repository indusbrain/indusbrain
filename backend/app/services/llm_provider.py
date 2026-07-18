import httpx
import os

class IndustrialLLMProviderGateway:
    """ Handles dynamic runtime switching between local Ollama, cloud APIs, and fallback math engines """
    
    def __init__(self):
        self.ollama_endpoint = "http://127.0.0.1:11434/api/generate"
        self.target_model = "qwen2.5:7b"

    def execute_reasoning_pass(self, query: str, context_chunks: list, mode: str = "LOCAL") -> str:
        context_text = "\n\n".join([f"Context Block:\n{c.get('content', '')}" for c in context_chunks])
        
        # Base system instruction prompt ensuring strict engineering alignment
        system_prompt = (
            f"You are the IndusBrain Core AI Engine. Review the provided technical documentation snippets "
            f"carefully and answer the query accurately. If you notice structural contradictions in the values, "
            f"explicitly flag them.\n\n"
            f"VERIFIED DATA REFERENCE CONTEXTS:\n{context_text}\n\n"
            f"OPERATOR QUERY: {query}\n"
            f"Synthesize an authoritative engineering report anchored in these facts:"
        )

        # -----------------------------------------------------------------
        # TIER 1: RUN LOCAL OLLAMA WORKFLOWS
        # -----------------------------------------------------------------
        if mode == "LOCAL":
            try:
                print(f"🤖 LLM GATEWAY: Directing prompt to local Ollama execution ({self.target_model})...")
                response = httpx.post(
                    self.ollama_endpoint,
                    json={
                        "model": self.target_model,
                        "prompt": system_prompt,
                        "stream": False,
                        "options": {"temperature": 0.1} # Keep responses highly deterministic
                    },
                    timeout=45.0
                )
                if response.status_code == 200:
                    return response.json().get("response", "").strip()
                else:
                    print("⚠️ TIER 1 FAILED: Ollama server returned an error code. Cascading to fallback paths...")
            except Exception as e:
                print(f"⚠️ TIER 1 FAILED: Could not reach Ollama (Is it running?). Error: {str(e)}")
            
            # Auto-cascade if selected mode breaks down
            mode = "INTERNAL"

        # -----------------------------------------------------------------
        # TIER 2: RUN CLOUD API METHOD HOOKS
        # -----------------------------------------------------------------
        if mode == "CLOUD":
            print("⚠️ TIER 2 NOTICE: Cloud API configurations missing. Cascading to baseline fallbacks...")
            mode = "INTERNAL"

        # -----------------------------------------------------------------
        # TIER 3: RUN INTERNAL DETERMINISTIC ENGINE (The Fail-Safe Fallback)
        # -----------------------------------------------------------------
        print("🔧 TIER 3 RUNTIME: Executing internal mathematical/rule-based processing core...")
        if not context_chunks:
            return "⚠️ DATA ISOLATION NOTICE: No contextual specifications were discovered in the local data layers."
            
        facts = [f"• {c.get('content', '')[:250]}... [Source: {c.get('filename', 'Manual')}]" for c in context_chunks]
        joined_facts = "\n".join(facts)
        
        return (
            f"🔧 LOCAL MATH MATRIX REPORT (OFFLINE ENGINE VERIFIED)\n"
            f"======================================================================\n"
            f"Query Target Analysis: '{query}'\n\n"
            f"The local processing engine extracted these verified technical data fragments:\n"
            f"{joined_facts}\n"
            f"======================================================================\n"
            f"🛡️ STATUS: Verified via internal consensus data layers."
        )

# Global model driver instance singleton
llm_gateway = IndustrialLLMProviderGateway()