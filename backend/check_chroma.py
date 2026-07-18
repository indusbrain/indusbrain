import os
from app.services.vector_store import vector_store_engine

print("📡 SWEEPING ACTIVE CHROMA STORAGE INDICES VIA ENGINE INTROSPECTION...")

# Dynamic property discovery loop
chroma_client = None
collection_obj = None

for attr_name in dir(vector_store_engine):
    attr_val = getattr(vector_store_engine, attr_name, None)
    if attr_val:
        type_str = str(type(attr_val)).lower()
        if "client" in type_str:
            chroma_client = attr_val
        elif "collection" in type_str:
            collection_obj = attr_val

try:
    if collection_obj:
        print(f"🟢 Direct Collection Object Identified via attribute proxy.")
        print(f"   📊 Total Vector Embeddings Count: {collection_obj.count()}")
    elif chroma_client:
        print(f"🟢 Client Connection Engine Identified via attribute proxy.")
        collections = chroma_client.list_collections()
        print(f"   🔹 Collections Registered: {len(collections)}")
        for c in collections:
            print(f"   🔹 Collection Name: '{c.name}' | Vector Count: {c.count()}")
    else:
        # Fallback to manual directory verification if properties are fully private
        print("⚠️ Properties isolated. Initializing direct hard-drive directory sweep...")
        import chromadb
        persist_path = os.path.join("storage", "chroma")
        if not os.path.exists(persist_path):
            persist_path = os.path.join("..", "storage", "chroma")
            
        fallback_client = chromadb.PersistentClient(path=persist_path)
        collections = fallback_client.list_collections()
        print(f"   🔹 Collections Registered on Disk: {len(collections)}")
        for c in collections:
            print(f"   🔹 Collection Name: '{c.name}' | Vector Count: {c.count()}")
            
except Exception as exc:
    print(f"❌ VECTOR SPACE AUDIT FAULT: {str(exc)}")