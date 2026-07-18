import asyncio
from typing import Dict, Any
from app.services.retrieval_hub import industrial_retrieval_hub
from app.services.reranker import industrial_reranker
from app.services.llm_provider import llm_gateway

class IndustrialAgentWorkersEngine:
    """
    Connects LangGraph worker nodes to your custom data layers, 
    retrieving context blocks and routing queries to Ollama.
    """

    async def _execute_agent_retrieval_and_reasoning(self, state: Dict[str, Any], agent_name: str) -> Dict[str, Any]:
        # Extract fields safely to support multiple dictionary structures
        raw_query = state.get("query", state.get("user_query", ""))
        routing_mode = state.get("routing_mode", "LOCAL")
        reasoning_path = state.get("reasoning_path", []) or []
        
        print(f"🛡️ WORKER NODE [{agent_name}]: Processing query under [{routing_mode}] engine execution rules...")
        
        # 1. Trigger parallel ChromaDB and Neo4j sweeps
        raw_candidates = await industrial_retrieval_hub.retrieve_hybrid_context(raw_query, limit=6)
        
        # 2. Refine results via Reciprocal Rank Fusion and Cross-Encoder checks
        refined_context_chunks = industrial_reranker.filter_and_rerank_context(
            query_string=raw_query,
            all_raw_candidates=raw_candidates,
            top_n=3
        )
        
        # 3. Route the consolidated prompt directly into your model gateway (Ollama/Fallback)
        generated_llm_response = llm_gateway.execute_reasoning_pass(
            query=raw_query,
            context_chunks=refined_context_chunks,
            mode=routing_mode
        )
        
        reasoning_path.append(agent_name)
        
        # Return updated state dictionary fields back to the graph thread clipboard
        return {
            "final_response": generated_llm_response,
            "extracted_docs": [c.get("filename", "") for c in refined_context_chunks],
            "reasoning_path": reasoning_path,
            "current_agent": "compiler_node",
            "confidence_score": 0.95 if refined_context_chunks else 0.40
        }

    async def knowledge_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """ Handles general equipment specifications and manual parameters """
        return await self._execute_agent_retrieval_and_reasoning(state, "knowledge_agent")

    async def maintenance_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """ Handles asset wear tracking, runtime data, and service loops """
        return await self._execute_agent_retrieval_and_reasoning(state, "maintenance_agent")

    async def compliance_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """ Handles regulatory boundaries and OSHA safety threshold checks """
        return await self._execute_agent_retrieval_and_reasoning(state, "compliance_agent")

# Instantiate global worker singleton instance for graph imports
agent_workers = IndustrialAgentWorkersEngine()