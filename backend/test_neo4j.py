import asyncio
from app.services.graph_store import graph_store_engine

print("📡 CONNECTING DIRECTLY TO NEO4J GRAPH ROUTING LABELS...")

def execute_graph_topology_sweep():
    # Verify if the application engine instance carries an open connection driver
    driver_instance = None
    for attr in dir(graph_store_engine):
        val = getattr(graph_store_engine, attr, None)
        if val and "driver" in str(type(val)).lower():
            driver_instance = val
            break
            
    if not driver_instance:
        # Emergency fallback connection string mapping
        from neo4j import GraphDatabase
        print("⚠️ Driver property isolated. Initializing direct socket channel connection...")
        driver_instance = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "password"))

    with driver_instance.session() as session:
        # Audit A: Global Node Verification Counts
        node_query = "MATCH (n) RETURN labels(n) as label, count(*) as count;"
        node_results = session.run(node_query)
        
        print("\n🧮 1. GRAPH NODE DENSITY MAPPING:")
        has_nodes = False
        for record in node_results:
            has_nodes = True
            print(f"   🔹 Entity Node Label: {record['label']} ──► Active Count inside Cluster: {record['count']}")
        if not has_nodes:
            print("   [Pristine Graph Cluster: 0 Active Nodes Generated]")

        # Audit B: Global Functional Edge Relationship Counts
        rel_query = "MATCH ()-[r]->() RETURN type(r) as relationship, count(*) as count;"
        rel_results = session.run(rel_query)
        
        print("\n🕸️ 2. TOPOLOGICAL EDGE RELATIONSHIP COUNTS:")
        has_rels = False
        for record in rel_results:
            has_rels = True
            print(f"   🔹 Functional Edge Link: [:{record['relationship']}] ──► Count: {record['count']} active connections")
        if not has_rels:
            print("   [0 Explicit Semantic Relationships mapped]")

if __name__ == "__main__":
    try:
        execute_graph_topology_sweep()
    except Exception as exc:
        print(f"❌ KNOWLEDGE GRAPH AUDIT FAULT: Connection rejected: {str(exc)}")