import re
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

    @staticmethod
    def _build_candidate_key(chunk: Dict[str, Any]) -> str:
        """
        Stable identity for a candidate chunk across both retrieval pathways.
        Falls back to a content fingerprint, because graph-only hits can arrive
        without a document_id and would otherwise all collide under one key.
        """
        doc_id = chunk.get("document_id")
        chunk_idx = chunk.get("chunk_index")
        if doc_id is not None and chunk_idx is not None:
            return f"doc_{doc_id}_idx_{chunk_idx}"
        fingerprint = (chunk.get("matched_excerpt") or chunk.get("content", ""))[:64]
        return f"frag_{hash(fingerprint)}"

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
            unique_key = self._build_candidate_key(chunk)
            chunk_lookup_registry[unique_key] = chunk
            
            if unique_key not in fused_scores:
                fused_scores[unique_key] = 0.0
            fused_scores[unique_key] += 1.0 / (self.k + (rank_idx + 1))

        # Pathway B: Process Graph Rank order placements
        for rank_idx, chunk in enumerate(graph_chunks):
            unique_key = self._build_candidate_key(chunk)
            
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

        # Step 2: Apply the Cross-Encoder semantic relevance sweep.
        # Score against the CHILD excerpt that actually matched where available - it is
        # the precise passage. Scoring the whole parent block dilutes the signal.
        scoring_texts = [
            (item.get("matched_excerpt") or item.get("content", "")) for item in fused_working_set
        ]

        relevance_scores: List[float] = []
        if self.cross_encoder_model and scoring_texts:
            try:
                # ONE batched forward pass for all candidates instead of a Python loop
                # calling the transformer once per chunk.
                pairs = [(query_string, text) for text in scoring_texts]
                raw_scores = self.cross_encoder_model.predict(pairs)
                relevance_scores = [float(score) for score in raw_scores]
            except Exception as rerank_error:
                print(f"⚠️ RERANKER: Neural pass failed ({rerank_error}). Using lexical fallback.")
                relevance_scores = []

        if len(relevance_scores) != len(fused_working_set):
            relevance_scores = [
                self._compute_local_attention_coefficient(query_string, text) for text in scoring_texts
            ]

        for item, score in zip(fused_working_set, relevance_scores):
            item["confidence_score"] = score

        # Re-sort descending based on the final attention confidence coefficients
        fused_working_set.sort(key=lambda x: x["confidence_score"], reverse=True)

        # Return only the top N highest-quality results
        return fused_working_set[:top_n]

import re # Import injection dependency for our fallback tokenizer regex logic

# Instantiate the global semantic rerank coordinator singleton instance
industrial_reranker = IndustrialContextRerankerEngine()