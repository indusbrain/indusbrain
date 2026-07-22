import os
import re
from typing import List, Dict, Any
from neo4j import GraphDatabase

class AdvancedIndustrialGraphStore:
    def __init__(self):
        # 🛡️ THE BULLETPROOF LOCAL BOUNDARY: Uses bolt:// to prevent cluster routing lookups,
        # combined with 127.0.0.1 to avoid Windows IPv6 name resolution loop locks.
        self.uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        # Default matches docker-compose.yml so a fresh clone works out of the box.
        self.password = os.getenv("NEO4J_PASSWORD", "secret_graph_pass_2026")

        # Lazy connection. Importing this module must never raise, otherwise the
        # entire API fails to boot whenever the Neo4j container is not up yet.
        self._driver = None
        self._constraints_ready = False

    @property
    def driver(self):
        """
        Returns a live Neo4j driver, or None if the graph database is unreachable.
        Reconnects automatically on a later call once the container is available.
        """
        if self._driver is not None:
            return self._driver
        try:
            print(f"📡 NEO4J CORE: Connecting to node network cluster at {self.uri}...")
            candidate = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            candidate.verify_connectivity()
            self._driver = candidate
            if not self._constraints_ready:
                self._initialize_database_constraints()
                self._constraints_ready = True
            print("🟢 NEO4J CORE: Graph cluster online.")
        except Exception as connection_error:
            self._driver = None
            print(f"⚠️ NEO4J OFFLINE: Graph store unreachable ({connection_error}). Retrying on next use.")
        return self._driver

    @property
    def is_online(self) -> bool:
        return self.driver is not None

    def close(self):
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def _initialize_database_constraints(self):
        """
        Sets up unique constraints using a dynamic multi-version fallback routing 
        to support both modern Neo4j v5.x and legacy v4.x engine deployments.
        """
        with self.driver.session() as session:
            # Try Modern Neo4j v5.x Syntax Blueprint First
            v5_queries = [
                "CREATE CONSTRAINT unique_document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;",
                "CREATE CONSTRAINT unique_chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.uid IS UNIQUE;",
                "CREATE CONSTRAINT unique_asset_tag IF NOT EXISTS FOR (a:Asset) REQUIRE a.tag IS UNIQUE;"
            ]
            
            try:
                for q in v5_queries:
                    session.run(q)
                print("🟢 GRAPH ENGINE: Neo4j v5.x global unique index constraints activated successfully.")
                return
            except Exception:
                print("🔄 GRAPH ENGINE: Modern v5 syntax rejected. Falling back to legacy v4.x compiler passes...")

            # Fallback to Legacy Neo4j v4.x Syntax Specification
            v4_queries = [
                "CREATE CONSTRAINT ON (d:Document) ASSERT d.id IS UNIQUE;",
                "CREATE CONSTRAINT ON (c:Chunk) ASSERT c.uid IS UNIQUE;",
                "CREATE CONSTRAINT ON (a:Asset) ASSERT a.tag IS UNIQUE;"
            ]
            
            for q in v4_queries:
                try:
                    session.run(q)
                except Exception as e:
                    print(f"⚠️ NEO4J INDEX WARNING: Constraint configuration bypassed: {e}")

    def _extract_semantic_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Advanced regex parser. Identifies hardware tags and compliance models
        across spaces, dashes, and varied casing arrangements.
        """
        # Formatted to catch variations like: PUMP-101, pump 102, VALVE203, sys-45
        asset_pattern = re.compile(r"\b(PUMP|VALVE|SYS|COMP|PSV|BRG|ENG)[-_\s]*(\d{2,4})\b", re.IGNORECASE)
        standard_pattern = re.compile(r"\b(OSHA[-_\s]*\d{4}|ASME[-_\s]*[A-Z0-9]+|ISO[-_\s]*\d{4})\b", re.IGNORECASE)

        # Reconstruct structured text identifiers
        assets = []
        for match in asset_pattern.findall(text):
            prefix = match[0].upper()
            numeric_suffix = match[1]
            assets.append(f"{prefix}-{numeric_suffix}") # Re-unify to standard format: PUMP-101

        standards = []
        for match in standard_pattern.findall(text):
            cleaned_standard = re.sub(r"[-_\s]+", "-", match).upper()
            standards.append(cleaned_standard)

        return {
            "assets": list(set(assets)),
            "standards": list(set(standards))
        }

    def sync_document_graph_topology(self, document_id: int, filename: str, chunks: List[Dict[str, Any]]):
        """
        Commits structural data points while building semantic relationships
        between chunk fragments, assets, and regulatory codes.
        """
        active_driver = self.driver
        if active_driver is None:
            print(f"⚠️ GRAPH SYNC SKIPPED: Neo4j offline, document {document_id} not mapped into the graph.")
            return

        print(f"⚡ GRAPH STORE PERSISTENCE: Orchestrating topological mappings for ID: {document_id}")

        with active_driver.session() as session:
            # 1. Create or merge the parent Document Node entry point
            session.run(
                """
                MERGE (d:Document {id: $doc_id})
                SET d.filename = $filename, d.updated_at = timestamp()
                """,
                doc_id=document_id, filename=filename
            )

            # 2. Iterate through each chunk to map its structural and semantic boundaries
            for chunk in chunks:
                raw_content = chunk.get("content", "")
                chunk_idx = chunk.get("chunk_index", 0)
                unique_chunk_uid = f"doc_{document_id}_chunk_{chunk_idx}"

                # Extract pure text if the database row has our child|||parent string separator
                display_content = chunk_content = raw_content.split(" ||| ", 1)[0] if " ||| " in raw_content else raw_content

                # Isolate assets and compliance standards using our entities parser
                entities = self._extract_semantic_entities(chunk_content)

                # 3. Insert and link the current Chunk Node to its parent Document Node
                session.run(
                    """
                    MATCH (d:Document {id: $doc_id})
                    MERGE (c:Chunk {uid: $c_uid})
                    SET c.index = $c_idx, c.content = $content, c.page = $page
                    MERGE (d)-[:HAS_CHUNK]->(c)
                    """,
                    doc_id=document_id, c_uid=unique_chunk_uid, 
                    c_idx=chunk_idx, content=display_content, page=chunk.get("page_number", 1)
                )

                # 4. Draw graph connections from Chunk Nodes to explicit Asset Entities
                for asset_tag in entities["assets"]:
                    session.run(
                        """
                        MATCH (c:Chunk {uid: $c_uid})
                        MERGE (a:Asset {tag: $asset_tag})
                        SET a.type = CASE 
                            WHEN $asset_tag STARTS WITH 'PUMP' THEN 'Centrifugal Fluid Pump'
                            WHEN $asset_tag STARTS WITH 'VALVE' THEN 'Flow Actuation Valve'
                            WHEN $asset_tag STARTS WITH 'PSV' THEN 'Pressure Safety Valve'
                            ELSE 'Industrial Component Asset'
                        END
                        MERGE (c)-[:MENTIONS]->(a)
                        """,
                        c_uid=unique_chunk_uid, asset_tag=asset_tag
                    )

                # 5. Draw graph connections from Chunk Nodes to explicit Regulation Entities
                for standard_code in entities["standards"]:
                    session.run(
                        """
                        MATCH (c:Chunk {uid: $c_uid})
                        MERGE (s:Standard {code: $standard_code})
                        MERGE (c)-[:REFERENCES_COMPLIANCE]->(s)
                        """,
                        c_uid=unique_chunk_uid, standard_code=standard_code
                    )

        print(f"🟢 GRAPH STORE PERSISTENCE: GraphRAG semantic nodes successfully mapped into cluster.")

    def purge_document_graph(self, document_id: int) -> None:
        """Detaches and deletes a document's chunk nodes (used when a doc is deleted)."""
        active_driver = self.driver
        if active_driver is None:
            return
        try:
            with active_driver.session() as session:
                session.run(
                    """
                    MATCH (d:Document {id: $doc_id})
                    OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
                    DETACH DELETE c, d
                    """,
                    doc_id=document_id,
                )
            print(f"🧹 GRAPH CLEANUP: Purged graph topology for document {document_id}.")
        except Exception as purge_error:
            print(f"⚠️ GRAPH CLEANUP FAILED for document {document_id}: {purge_error}")

graph_store_engine = AdvancedIndustrialGraphStore()