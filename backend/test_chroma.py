import os
import chromadb
from dotenv import load_dotenv

# Populate process memory parameters from our hidden local environment asset file
load_dotenv()

def verify_vector_engine():
    print("====================================================")
    print("🤖 CHROMADB VECTOR INFRASTRUCTURE: CORE CLIENT DIAGNOSTIC")
    print("====================================================")
    
    # Extract mapped host and port parameters safely from active memory
    host = os.getenv("CHROMA_HOST", "localhost")
    port_str = os.getenv("CHROMA_PORT", "8001")
    port = int(port_str)
    
    print(f"📡 Initializing HttpClient connection link to ChromaDB cluster at {host}:{port}...")
    
    try:
        # Instantiate the formal remote vector store database client connection driver
        client = chromadb.HttpClient(host=host, port=port)
        
        print("🔄 Connection established. Testing data collection allocation loops...")
        
        # Provision a temporary collection space inside the database container memory
        collection_name = "system_handshake_diagnostic_collection"
        collection = client.get_or_create_collection(name=collection_name)
        
        # Inject a basic mock text string. ChromaDB handles simple dummy embeddings internally
        # if none are provided, allowing us to verify the client pipeline easily.
        print("📥 Injecting diagnostic test record metadata blocks...")
        collection.add(
            documents=["Standard operating procedure for emergency shutdown of Valve-4B."],
            metadatas=[{"category": "SOP", "asset_id": "valve_4b"}],
            ids=["doc_handshake_001"]
        )
        
        # Execute a semantic semantic similarity lookup query check
        print("🔍 Executing multi-dimensional vector similarity query check...")
        query_results = collection.query(
            query_texts=["How do I turn off Valve-4B?"],
            n_results=1
        )
        
        # Verify the database successfully performed the similarity math and returned our record
        if query_results and "ids" in query_results and len(query_results["ids"][0]) > 0:
            print("🟢 SUCCESS: ChromaDB vector client driver is operating perfectly!")
            print(f"📄 Retrieved Matching Payload String: '{query_results['documents'][0][0]}'")
            
            # Clean up the system state by purging our temporary testing collection space
            print("🧹 Purging testing database collection space to clean local state...")
            client.delete_collection(name=collection_name)
            return True
        else:
            print("❌ FAILURE: Similarity lookup loop completed but returned unreadable states.")
            return False
            
    except Exception as e:
        print(f"❌ AUDIT EXCEPTION FAILURE: Client engine could not communicate with ChromaDB.")
        print(f"📝 Raw Database Error Feedback: {str(e)}")
        print("\n💡 REMEDY STEP: Ensure your docker containers are active via 'docker compose up -d'.")
        return False

if __name__ == "__main__":
    success = verify_vector_engine()
    print("====================================================")
    if success:
        print("🏆 VECTOR STORE LAYER STATUS: 100% VALIDATED. Infrastructure is green.")
        exit(0)
    else:
        print("🚨 VECTOR STORE LAYER STATUS: CRITICAL FAULT. Fix configuration parameters.")
        exit(1)