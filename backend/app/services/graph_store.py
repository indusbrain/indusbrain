import os
from typing import List, Dict, Any
from neo4j import GraphDatabase

class GraphStoreEngine:
    """
    Enterprise-grade Graph Database Controller orchestrating transactional 
    cypher execution blocks natively into the Neo4j cluster container grid.
    """
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "secret_graph_pass_2026")
        
        self.driver = None
        # Self-healing connection wrapper targeting our Docker container network
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Verify network credentials instantly via a quick head ping query
            self.driver.verify_connectivity()
            print(f"📡 NEO4J CORE: Connection verified. Structural Graph maps active on {self.uri}")
        except Exception as e:
            print(f"⚠️ NEO4J CONNECTION BYPASSED: Operating in offline mock mode. Graph writes will print to console logs: {str(e)}")

    def close(self):
        if self.driver:
            self.driver.close()

    def sync_document_graph_topology(self, document_id: int, filename: str, chunks: List[Dict[str, Any]]):
        """
        Executes an atomic Cypher transaction block to map structural text 
        nodes and trace document parent-to-child relationships.
        """
        if not self.driver:
            print(f"💾 MOCK GRAPH WRITE: Document {document_id} mapped to {len(chunks)} structural relations.")
            return

        # Cypher statement optimized for idempotency using MERGE syntax boundaries
        cypher_query = """
        MERGE (d:Document {id: $doc_id})
        SET d.filename = $filename, d.updated_at = timestamp()
        
        WITH d
        UNWIND $chunks_payload AS chunk_item
        MERGE (c:Chunk {id: $doc_id + "_" + chunk_item.chunk_index})
        SET c.chunk_index = chunk_item.chunk_index,
            c.page_number = chunk_item.page_number,
            c.content = chunk_item.content
            
        MERGE (d)-[:HAS_CHUNK]->(c)
        """

        try:
            with self.driver.session() as session:
                session.run(
                    cypher_query,
                    doc_id=document_id,
                    filename=filename,
                    chunks_payload=chunks
                )
            print(f"⚡ GRAPH STORE PERSISTENCE: Structural topology mapped into Neo4j for ID: {document_id}")
        except Exception as e:
            print(f"❌ GRAPH STORE TRANSACTION FAILURE: {str(e)}")
            raise e

graph_store_engine = GraphStoreEngine()