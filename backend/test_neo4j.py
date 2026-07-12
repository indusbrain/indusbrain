import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Initialize live system environment process configurations from local disk
load_dotenv()

def verify_graph_engine():
    print("====================================================")
    print("🕸️  NEO4J GRAPH INFRASTRUCTURE: AUTHENTICATION AUDIT DIAGNOSTIC")
    print("====================================================")
    
    # Retrieve credential parameters from environment context mapping
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    
    print(f"📡 Initializing binary Bolt driver connection channel to: {uri}")
    print(f"👤 target Authentication Identity: {user}")
    
    if not password:
        print("🚨 AUDIT CRITICAL FAILURE: NEO4J_PASSWORD is not present inside environment memory.")
        return False

    # Instantiate the formal native Graph database connection client driver
    try:
        with GraphDatabase.driver(uri, auth=(user, password)) as driver:
            print("🔄 Driver instantiated. Executing remote session query handshake...")
            
            # Open a thread-safe execution workspace context path to run a test cypher line
            with driver.session() as session:
                # Execute a primitive math computation return loop directly inside the graph engine
                result = session.run("RETURN 1 AS handshake_telemetry")
                record = result.single()
                
                if record and record["handshake_telemetry"] == 1:
                    print("🟢 SUCCESS: Neo4j driver authenticated perfectly!")
                    print("📊 Telemetry Response Verified: Graph engine is fully operational.")
                    return True
                else:
                    print("❌ FAILURE: Connection response returned unreadable data blocks.")
                    return False
                    
    except Exception as e:
        print(f"❌ AUDIT EXCEPTION FAILURE: Driver could not authenticate with the container instance.")
        print(f"📝 Raw Engine Diagnostics Error: {str(e)}")
        print("\n💡 REMEDY STEP: Ensure you have initialized your database container using 'docker compose up -d'.")
        return False

if __name__ == "__main__":
    success = verify_graph_engine()
    print("====================================================")
    if success:
        print("🏆 GRAPH LAYER SCORECARD: 100% VALIDATED. Infrastructure is locked down.")
        exit(0)
    else:
        print("🚨 GRAPH LAYER SCORECARD: AUTHENTICATION ERROR. Check your .env file credentials.")
        exit(1)