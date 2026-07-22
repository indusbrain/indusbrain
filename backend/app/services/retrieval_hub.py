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
    # Both datastores are resolved live on every query rather than captured once at
    # import time. Previously this class snapshotted a connection during module
    # import, so a database that came up later was never picked up, and a second
    # Neo4j driver was created with a hardcoded password that did not match
    # docker-compose - meaning the graph half of "hybrid" retrieval never ran.
    @property
    def chroma_collection(self):
        return vector_store_engine.collection

    @property
    def neo4j_driver(self):
        return graph_store_engine.driver

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
        active_collection = self.chroma_collection
        if active_collection is not None:
            try:
                # Embed the question with the SAME model used at indexing time.
                # Passing `query_texts=` instead would make Chroma fall back to its own
                # built-in embedder, silently comparing vectors from two different
                # models and degrading recall.
                query_vector = vector_store_engine.embedding_model.encode(query_string).tolist()

                vector_results = active_collection.query(
                    query_embeddings=[query_vector],
                    n_results=limit,
                    include=["documents", "metadatas", "distances"]
                )

                if vector_results and vector_results.get("documents") and len(vector_results["documents"]) > 0:
                    documents = vector_results["documents"][0]
                    metadatas = vector_results["metadatas"][0] or []
                    distances = vector_results.get("distances") or []
                    distances = distances[0] if distances else [0.5] * len(documents)

                    for idx, matched_child_text in enumerate(documents):
                        meta = (metadatas[idx] if idx < len(metadatas) else None) or {}
                        chunk_id_key = f"chunk_{meta.get('document_id', 'unknown')}_{meta.get('chunk_index', idx)}"

                        # PARENT-CHILD RAG: we search over the small, precise child chunk,
                        # but hand the model the larger parent block so it has enough
                        # surrounding context to answer properly. The parent was already
                        # being stored at index time - it was simply never read back.
                        parent_context_text = meta.get("parent_context") or matched_child_text

                        pooled_candidates_manifest[chunk_id_key] = {
                            "content": parent_context_text,
                            "matched_excerpt": matched_child_text,
                            "filename": meta.get("filename", "Unknown Specification Reference"),
                            "document_id": meta.get("document_id", None),
                            "chunk_index": meta.get("chunk_index", idx),
                            "origin_source": "VECTOR_PROXIMITY_MATRIX",
                            "semantic_distance": float(distances[idx]) if idx < len(distances) else 0.5
                        }
                    print(f"   🟢 ChromaDB Sweep complete. Pulled {len(documents)} candidate vectors.")
            except Exception as chroma_err:
                print(f"   ⚠️ VECTOR ACCESS EXCEPTION: Chroma lookups bypassed: {str(chroma_err)}")
        else:
            print("   ⚠️ VECTOR PATHWAY OFFLINE: Chroma unreachable, skipping semantic sweep.")

        # =====================================================================
        # PATHWAY 2: TOPOLOGICAL KNOWLEDGE GRAPH WALKS (Neo4j)
        # =====================================================================
        extracted_asset_tags = self._extract_industrial_asset_tags(query_string)
        
        active_driver = self.neo4j_driver
        if extracted_asset_tags and active_driver is not None:
            print(f"   ⚙️ GRAPH ROUTER: Isolated asset entity tags: {extracted_asset_tags}. Spawning Cypher transaction...")
            try:
                with active_driver.session() as graph_session:
                    # Walk from the matched Asset back to the Chunks that mention it, and
                    # on to the owning Document so graph hits carry a REAL source filename
                    # instead of a synthetic "Asset Topological Graph Link" label.
                    cypher_crawl_query = """
                    MATCH (a:Asset) WHERE a.tag IN $tags
                    MATCH (c:Chunk)-[:MENTIONS]->(a)
                    OPTIONAL MATCH (d:Document)-[:HAS_CHUNK]->(c)
                    RETURN properties(c) AS props,
                           a.tag        AS asset_tag,
                           elementId(c) AS native_id,
                           d.filename   AS source_filename,
                           d.id         AS source_document_id
                    LIMIT $graph_limit;
                    """
                    graph_records = graph_session.run(cypher_crawl_query, tags=extracted_asset_tags, graph_limit=limit)

                    graph_chunks_added = 0
                    for record in graph_records:
                        props = record["props"] or {}
                        g_idx = props.get("chunk_index", props.get("index", 0))
                        g_text = props.get("content", "")
                        asset_binding = record["asset_tag"]
                        native_el_id = record["native_id"]
                        graph_filename = record["source_filename"] or "Knowledge Graph Node"
                        graph_doc_id = record["source_document_id"]

                        if not g_text:
                            continue

                        graph_chunks_added += 1

                        # Cross-check graph results against vector results. Compare against the
                        # child excerpt that actually matched, not the wider parent block, or
                        # nearly every parent would spuriously overlap.
                        vector_match_key = None
                        for key, val in pooled_candidates_manifest.items():
                            comparison_text = val.get("matched_excerpt") or val.get("content", "")
                            if not comparison_text:
                                continue
                            if comparison_text[:40] in g_text or g_text[:40] in comparison_text:
                                vector_match_key = key
                                break

                        if vector_match_key:
                            # Found by BOTH the vector index and the knowledge graph: this is the
                            # strongest possible evidence, and is what "graph verified" means.
                            pooled_candidates_manifest[vector_match_key]["origin_source"] = "HYBRID_GRAPH_VECTOR_VERIFIED"
                            pooled_candidates_manifest[vector_match_key]["asset_tag_context"] = asset_binding
                        else:
                            graph_only_key = f"graph_node_{native_el_id}"
                            pooled_candidates_manifest[graph_only_key] = {
                                "content": g_text,
                                "matched_excerpt": g_text,
                                "filename": graph_filename,
                                "document_id": graph_doc_id,
                                "chunk_index": g_idx,
                                "origin_source": "GRAPH_TOPOLOGY_WALK",
                                "semantic_distance": 0.0,
                                "asset_tag_context": asset_binding
                            }
                    print(f"   🟢 Neo4j Crawl complete. Pulled {graph_chunks_added} asset-linked chunks from topology graph.")
            except Exception as graph_err:
                print(f"   ⚠️ GRAPH ACCESS EXCEPTION: Neo4j transactional walks bypassed: {str(graph_err)}")
        elif not extracted_asset_tags:
            print("   ⚙️ GRAPH ROUTER: No hardware asset entity identifiers found in query string. Skipping Cypher crawl.")
        else:
            print("   ⚠️ GRAPH PATHWAY OFFLINE: Neo4j unreachable, skipping topology walk.")

        return list(pooled_candidates_manifest.values())

# Instantiate the global retrieval coordinator singleton instance
industrial_retrieval_hub = HybridRetrievalHubEngine()