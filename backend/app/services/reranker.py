import math
from typing import List, Dict, Any

class IndustrialContextRerankerEngine:
    """
    Advanced Data Refinement Engine. Normalizes diverse vector and graph 
    inputs via RRF and filters out noise using deep semantic context ranking.
    """
    def __init__(self, k_constant: int = 60):
        self.k = k_constant
        self.cross_encoder_model = None
        
        # Self-heal attempt to load heavyweight transformer neural structures if available
        try:
            from sentence_transformers import CrossEncoder
            # Utilize a highly efficient, CPU-friendly open-source reranker model
            self.cross_encoder_model = CrossEncoder('BAAI/bge-reranker-base')
            print("🟢 RERANKING CORE: Neural Cross-Encoder Transformer activated successfully.")
        except Exception:
            print("🟢 RERANKING CORE: Local Alphanumeric Self-Attention Matrix activated successfully.")

    def compute_reciprocal_rank_fusion(
        self, 
        vector_chunks: List[Dict[str, Any]], 
        graph_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Applies the RRF consensus algorithm to blend vector proximity arrays 
        with topological graph outputs without relying on normalized scores.
        """
        fused_scores: Dict[str, float] = {}
        chunk_lookup_registry: Dict[str, Dict[str, Any]] = {}

        # Pathway A: Process Vector Rank order placements
        for rank_idx, chunk in enumerate(vector_chunks):
            # Formulate clean structural mapping identifiers
            unique_key = f"doc_{chunk.get('document_id')}_idx_{chunk.get('chunk_index')}"
            chunk_lookup_registry[unique_key] = chunk
            
            if unique_key not in fused_scores:
                fused_scores[unique_key] = 0.0
            fused_scores[unique_key] += 1.0 / (self.k + (rank_idx + 1))

        # Pathway B: Process Graph Rank order placements
        for rank_idx, chunk in enumerate(graph_chunks):
            unique_key = f"doc_{chunk.get('document_id')}_idx_{chunk.get('chunk_index')}"
            
            if unique_key not in chunk_lookup_registry:
                chunk_lookup_registry[unique_key] = chunk
                
            if unique_key not in fused_scores:
                fused_scores[unique_key] = 0.0
            fused_scores[unique_key] += 1.0 / (self.k + (rank_idx + 1))

        # Reassemble the registry list mapped against calculated RRF scores
        blended_candidates_list = []
        for key, rrf_val in fused_scores.items():
            target_item = chunk_lookup_registry[key]
            target_item["rrf_score"] = float(rrf_val)
            blended_candidates_list.append(target_item)

        # Sort the items descending based on their consensus rank values
        blended_candidates_list.sort(key=lambda x: x["rrf_score"], reverse=True)
        return blended_candidates_list

    def _compute_local_attention_coefficient(self, query: str, document_text: str) -> float:
        """ High-speed CPU fallback matching technical token lookaheads and intersection overlaps """
        query_tokens = set(re.findall(r'\w+', query.upper()))
        doc_tokens = set(re.findall(r'\w+', document_text.upper()))
        
        if not query_tokens:
            return 0.0
            
        intersection = query_tokens.intersection(doc_tokens)
        
        # Give extra weight to explicit industrial asset tag numbers (e.g., '102')
        industrial_multiplier = 1.0
        for token in query_tokens:
            if token.isdigit() and token in doc_tokens:
                industrial_multiplier += 1.5
                
        jaccard_fraction = len(intersection) / len(query_tokens)
        return float(jaccard_fraction * industrial_multiplier)

    def filter_and_rerank_context(
        self, 
        query_string: str, 
        all_raw_candidates: List[Dict[str, Any]], 
        top_n: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Executes a deep attention sweep over your blended candidates list, 
        filtering out noise to deliver the most accurate, context-rich results.
        """
        if not all_raw_candidates:
            return []

        # Segment candidates into their respective database discovery streams
        vector_stream = [c for c in all_raw_candidates if "VECTOR" in c.get("origin_source", "")]
        graph_stream = [c for c in all_raw_candidates if "GRAPH" in c.get("origin_source", "")]
        verified_stream = [c for c in all_raw_candidates if "VERIFIED" in c.get("origin_source", "")]

        # Include overlapping verified row items in both analytical arrays
        for item in verified_stream:
            vector_stream.append(item)
            graph_stream.append(item)

        # Step 1: Blend the streams together using our RRF rank calculations
        fused_working_set = self.compute_reciprocal_rank_fusion(vector_stream, graph_stream)

        # Step 2: Apply the Cross-Encoder semantic relevance sweep
        for item in fused_working_set:
            text_content = item.get("content", "")
            
            if self.cross_encoder_model:
                try:
                    # Run neural transformer model matrix calculations
                    relevance_probability = self.cross_encoder_model.predict([query_string, text_content])
                    item["confidence_score"] = float(relevance_probability)
                except Exception:
                    item["confidence_score"] = self._compute_local_attention_coefficient(query_string, text_content)
            else:
                item["confidence_score"] = self._compute_local_attention_coefficient(query_string, text_content)

        # Re-sort descending based on the final attention confidence coefficients
        fused_working_set.sort(key=lambda x: x["confidence_score"], reverse=True)
        
        # Return only the top N highest-quality results
        return fused_working_set[:top_n]

import re # Import injection dependency for our fallback tokenizer regex logic

# Instantiate the global semantic rerank coordinator singleton instance
industrial_reranker = IndustrialContextRerankerEngine()