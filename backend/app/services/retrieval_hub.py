import os
import re
from typing import List, Dict, Any
from app.services.vector_store import vector_store_engine
from app.services.graph_store import graph_store_engine

class HybridRetrievalHubEngine:
    """
    Production Cross-Paradigm Information Engine. Integrates unstructured 
    ChromaDB vector searches with structured Neo4j graph crawls in parallel.
    """
    def __init__(self):
        self.chroma_collection = getattr(vector_store_engine, "collection", None)
        self.neo4j_driver = None
        
        # Self-heal Neo4j driver reference mapping
        for attr in dir(graph_store_engine):
            val = getattr(graph_store_engine, attr, None)
            if val and "driver" in str(type(val)).lower():
                self.neo4j_driver = val
                break
                
        if not self.neo4j_driver:
            from neo4j import GraphDatabase
            self.neo4j_driver = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "password"))

    def _extract_industrial_asset_tags(self, query: str) -> List[str]:
        """ Uses alphanumeric lookaheads to catch machine tokens (e.g., PUMP-102, VALVE-404) """
        asset_pattern = re.compile(r'\b[A-Z]+-\d+\b|\b[A-Z]+\d+\b')
        found_tags = asset_pattern.findall(query.upper())
        return list(dict.fromkeys(found_tags))

    async def retrieve_hybrid_context(self, query_string: str, limit: int = 8) -> List[Dict[str, Any]]:
        """
        Executes parallel dual-database context lookups, unifying 
        semantic proximity vectors with topological graph records.
        """
        print(f"🛰️ RETRIEVAL HUB: Processing multi-database hybrid query sweep for: '{query_string}'")
        pooled_candidates_manifest: Dict[str, Dict[str, Any]] = {}
        
        # =====================================================================
        # PATHWAY 1: DENSE SEMANTIC VECTOR SEARCH (ChromaDB)
        # =====================================================================
        if self.chroma_collection:
            try:
                vector_results = self.chroma_collection.query(
                    query_texts=[query_string],
                    n_results=limit,
                    include=["documents", "metadatas", "distances"]
                )
                
                if vector_results and vector_results.get("documents") and len(vector_results["documents"]) > 0:
                    documents = vector_results["documents"][0]
                    metadatas = vector_results["metadatas"][0]
                    distances = vector_results["distances"][0] if "distances" in vector_results else [0.5] * len(documents)
                    
                    for idx, text in enumerate(documents):
                        meta = metadatas[idx] or {}
                        chunk_id_key = f"chunk_{meta.get('document_id', 'unknown')}_{meta.get('chunk_index', idx)}"
                        
                        pooled_candidates_manifest[chunk_id_key] = {
                            "content": text,
                            "filename": meta.get("filename", "Unknown Specification Reference"),
                            "document_id": meta.get("document_id", None),
                            "chunk_index": meta.get("chunk_index", idx),
                            "origin_source": "VECTOR_PROXIMITY_MATRIX",
                            "semantic_distance": float(distances[idx])
                        }
                print(f"   🟢 ChromaDB Sweep complete. Pulled {len(vector_results.get('documents', [[]])[0])} candidate vectors.")
            except Exception as chroma_err:
                print(f"   ⚠️ VECTOR ACCESS EXCEPTION: Chroma lookups bypassed: {str(chroma_err)}")

        # =====================================================================
        # PATHWAY 2: TOPOLOGICAL KNOWLEDGE GRAPH WALKS (Neo4j)
        # =====================================================================
        extracted_asset_tags = self._extract_industrial_asset_tags(query_string)
        
        if extracted_asset_tags and self.neo4j_driver:
            print(f"   ⚙️ GRAPH ROUTER: Isolated asset entity tags: {extracted_asset_tags}. Spawning Cypher transaction...")
            try:
                with self.neo4j_driver.session() as graph_session:
                    # 🎯 THE FIX: Changed id(c) to elementId(c) and safely read the full chunk node 
                    # properties dictionary wrapper to completely silence schema-level warnings
                    cypher_crawl_query = """
                    MATCH (a:Asset) WHERE a.tag IN $tags
                    MATCH (a)-[:MENTIONS|HAS_CHUNK*1..3]-(c:Chunk)
                    RETURN properties(c) as props, a.tag as asset_tag, elementId(c) as native_id
                    LIMIT $graph_limit;
                    """
                    graph_records = graph_session.run(cypher_crawl_query, tags=extracted_asset_tags, graph_limit=limit)
                    
                    graph_chunks_added = 0
                    for record in graph_records:
                        graph_chunks_added += 1
                        props = record["props"] or {}
                        g_idx = props.get("chunk_index", props.get("index", 0))
                        g_text = props.get("content", "")
                        asset_binding = record["asset_tag"]
                        native_el_id = record["native_id"]
                        
                        if not g_text:
                            continue
                        
                        # Match graph results against existing vector records using content snippet overlap
                        vector_match_key = None
                        for key, val in pooled_candidates_manifest.items():
                            if val["content"][:40] in g_text or g_text[:40] in val["content"]:
                                vector_match_key = key
                                break
                        
                        if vector_match_key:
                            pooled_candidates_manifest[vector_match_key]["origin_source"] = "HYBRID_GRAPH_VECTOR_VERIFIED"
                            pooled_candidates_manifest[vector_match_key]["asset_tag_context"] = asset_binding
                        else:
                            graph_only_key = f"graph_node_{native_el_id}"
                            pooled_candidates_manifest[graph_only_key] = {
                                "content": g_text,
                                "filename": f"Asset Topological Graph Link ({asset_binding})",
                                "document_id": "graph_linked",
                                "chunk_index": g_idx,
                                "origin_source": "GRAPH_TOPOLOGY_WALK",
                                "semantic_distance": 0.0,
                                "asset_tag_context": asset_binding
                            }
                    print(f"   🟢 Neo4j Crawl complete. Pulled {graph_chunks_added} asset-linked chunks from topology graph.")
            except Exception as graph_err:
                print(f"   ⚠️ GRAPH ACCESS EXCEPTION: Neo4j transactional walks bypassed: {str(graph_err)}")
        else:
            print("   ⚙️ GRAPH ROUTER: No hardware asset entity identifiers found in query string. Skipping Cypher crawl.")

        return list(pooled_candidates_manifest.values())

# Instantiate the global retrieval coordinator singleton instance
industrial_retrieval_hub = HybridRetrievalHubEngine()