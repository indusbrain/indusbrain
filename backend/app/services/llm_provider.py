import os
import httpx
from typing import Any, Dict, List, Optional


class IndustrialLLMProviderGateway:
    """
    Handles runtime switching between local Ollama inference and a deterministic
    extractive fallback.

    Every call reports WHICH engine actually produced the answer, so the UI can
    tell the operator the truth instead of implying a language model ran when it
    did not.
    """

    def __init__(self):
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        self.ollama_endpoint = f"{self.ollama_host}/api/generate"
        self.tags_endpoint = f"{self.ollama_host}/api/tags"
        self.preferred_model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        self.request_timeout = float(os.getenv("OLLAMA_TIMEOUT", "120"))
        self._resolved_model: Optional[str] = None

    async def resolve_model(self) -> Optional[str]:
        """
        Picks a model that is ACTUALLY installed on this Ollama host.

        The preferred model is used when present. Otherwise we fall back to any
        installed model rather than failing - a demo machine may have a different
        model pulled, and silently falling back to "no inference" made the whole
        LOCAL mode look broken.
        """
        if self._resolved_model:
            return self._resolved_model

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(self.tags_endpoint)
            if response.status_code != 200:
                return None
            installed = [m.get("name", "") for m in response.json().get("models", [])]
        except Exception as tags_error:
            print(f"⚠️ LLM GATEWAY: could not list Ollama models ({tags_error}).")
            return None

        if not installed:
            print("⚠️ LLM GATEWAY: Ollama is running but has no models installed.")
            return None

        # Exact match, then prefix match (handles ':latest' style suffixes), then first.
        if self.preferred_model in installed:
            chosen = self.preferred_model
        else:
            base_name = self.preferred_model.split(":")[0]
            prefix_matches = [m for m in installed if m.split(":")[0] == base_name]
            chosen = prefix_matches[0] if prefix_matches else installed[0]
            print(
                f"ℹ️ LLM GATEWAY: '{self.preferred_model}' is not installed. "
                f"Using '{chosen}' instead. Installed: {installed}"
            )

        self._resolved_model = chosen
        return chosen

    def _build_grounded_prompt(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        agent_directive: Optional[str] = None,
    ) -> str:
        """
        Builds a strictly grounded prompt. Sources are numbered so the model can
        cite them, and it is explicitly told to refuse rather than invent.

        `agent_directive` carries the calling specialist's domain instructions, so
        the same retrieved evidence is presented differently by the knowledge,
        maintenance and compliance agents.
        """
        context_blocks = []
        for idx, chunk in enumerate(context_chunks, start=1):
            source_name = chunk.get("filename", "Unknown source")
            body = chunk.get("content", "")
            context_blocks.append(f"[SOURCE {idx} - {source_name}]\n{body}")

        context_text = "\n\n".join(context_blocks)

        return (
            "You are IndusBrain, a knowledge assistant for industrial plant engineers.\n"
            "Your answers influence maintenance and safety decisions on live equipment, "
            "so incompleteness is as dangerous as being wrong.\n\n"

            "ABSOLUTE RULES\n"
            "1. Use ONLY the numbered sources below. Never use outside knowledge.\n"
            "2. Cite the source number inline, like [SOURCE 2], for every factual claim.\n"
            "3. Never guess a number, pressure, torque, date or part identifier. "
            "If the sources do not contain it, say precisely what is missing.\n\n"

            "BEFORE YOU ANSWER, CHECK FOR THESE - THEY ARE MANDATORY\n"
            "A. CONFLICTING VALUES. If two sources state different values for the same "
            "parameter, you MUST report both values with their sources and state clearly "
            "that they disagree. Never silently pick one.\n"
            "B. CONDITIONS AND PRECONDITIONS. If a value is only valid when certain "
            "conditions are met, you MUST list those conditions. A limit quoted without "
            "its preconditions is a dangerous answer.\n"
            "C. WARNINGS. If any source contains a warning, caution or consequence "
            "statement relevant to the question, you MUST include it.\n"
            "D. OPEN ACTIONS. If a source shows a required step was not completed, "
            "say so explicitly and explain what it means for the answer.\n"
            "E. CONSERVATIVE DEFAULT. Where sources conflict on a safety limit and you "
            "cannot confirm the preconditions were satisfied, state that the LOWER, more "
            "conservative limit applies until an engineer resolves the conflict.\n\n"

            "ANSWER FORMAT\n"
            "- Open with the direct answer in one or two sentences.\n"
            "- Then '**Conflicts and conditions**' if any of A-E apply. Omit if none apply.\n"
            "- Then '**What to verify**' listing concrete checks the engineer must perform.\n"
            "- Be technical and concise. No filler.\n\n"

            + (f"{agent_directive}\n\n" if agent_directive else "")

            + f"SOURCES:\n{context_text}\n\n"
            f"ENGINEER'S QUESTION: {query}\n\n"
            "ANSWER:"
        )

    async def execute_reasoning_pass(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        mode: str = "LOCAL",
        agent_directive: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Returns a dict describing both the answer AND how it was produced:
            {
              "text":      the answer,
              "engine":    human-readable engine label,
              "engine_id": machine id ("ollama" | "extractive_fallback" | "no_context"),
              "grounded":  whether any retrieved source backed the answer,
              "notice":    optional operator-facing warning
            }
        """
        # ------------------------------------------------------------------
        # GUARD: no retrieved context means we must NOT answer from model memory.
        # ------------------------------------------------------------------
        if not context_chunks:
            return {
                "text": (
                    "I could not find anything in the indexed documents that answers this question.\n\n"
                    "This is a genuine gap in the knowledge base, not a system error. "
                    "Upload the relevant manual, SOP or maintenance report and ask again."
                ),
                "engine": "No answer produced",
                "engine_id": "no_context",
                "grounded": False,
                "notice": "No supporting documents were retrieved, so no answer was generated.",
            }

        prompt = self._build_grounded_prompt(query, context_chunks, agent_directive)

        # ------------------------------------------------------------------
        # TIER 1: LOCAL OLLAMA INFERENCE (async - does not block the event loop)
        # ------------------------------------------------------------------
        if mode == "LOCAL":
            active_model = await self.resolve_model()
            if not active_model:
                print("⚠️ TIER 1: No usable Ollama model. Falling back to extraction.")
            else:
                try:
                    print(f"🤖 LLM GATEWAY: Dispatching to local Ollama ({active_model})...")
                    async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                        response = await client.post(
                            self.ollama_endpoint,
                            json={
                                "model": active_model,
                                "prompt": prompt,
                                "stream": False,
                                "options": {"temperature": 0.1},
                            },
                        )
                    if response.status_code == 200:
                        generated_text = response.json().get("response", "").strip()
                        if generated_text:
                            return {
                                "text": generated_text,
                                "engine": f"Local Ollama · {active_model}",
                                "engine_id": "ollama",
                                "grounded": True,
                                "notice": None,
                            }
                        print("⚠️ TIER 1: Ollama returned an empty completion. Falling back.")
                    else:
                        print(f"⚠️ TIER 1: Ollama HTTP {response.status_code}. Falling back.")
                except Exception as ollama_error:
                    print(f"⚠️ TIER 1: Ollama call failed ({ollama_error}). Falling back.")

        # ------------------------------------------------------------------
        # TIER 2: DETERMINISTIC EXTRACTIVE FALLBACK
        # This does NOT reason. It returns the retrieved passages verbatim and says
        # so plainly, so nobody mistakes quoted text for generated analysis.
        # ------------------------------------------------------------------
        print("🔧 TIER 2: Returning verbatim retrieved passages (no model inference).")

        excerpt_lines = []
        for idx, chunk in enumerate(context_chunks, start=1):
            source_name = chunk.get("filename", "Unknown source")
            passage = (chunk.get("matched_excerpt") or chunk.get("content", "")).strip()
            excerpt_lines.append(f"**{idx}. {source_name}**\n\n> {passage[:600]}")

        joined = "\n\n".join(excerpt_lines)
        reason = "Local model unavailable" if mode == "LOCAL" else "Direct retrieval mode selected"

        return {
            "text": (
                f"**Retrieved passages — no AI summary generated ({reason}).**\n\n"
                "The following text is quoted directly from your documents. "
                f"It has not been interpreted or summarised:\n\n{joined}"
            ),
            "engine": "Extractive retrieval (no model inference)",
            "engine_id": "extractive_fallback",
            "grounded": True,
            "notice": f"{reason}. Passages are shown verbatim rather than summarised.",
        }


# Global model driver instance singleton
llm_gateway = IndustrialLLMProviderGateway()
