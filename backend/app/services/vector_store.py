import os
import chromadb
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer

class HierarchicalVectorStoreEngine:
    """
    Enterprise ChromaDB Connection Manager. Stores high-density child vectors 
    anchored to complete parent context strings inside the metadata fields.
    """
    def __init__(self):
        self.chroma_host = os.getenv("CHROMA_HOST", "localhost")
        self.chroma_port = int(os.getenv("CHROMA_PORT", 8001))
        
        # Open connection to containerized Chroma cluster
        self.chroma_client = chromadb.HttpClient(host=self.chroma_host, port=self.chroma_port)
        self.embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.collection = self.chroma_client.get_or_create_collection(
            name="industrial_knowledge_vault"
        )

    def index_document_chunks(self, document_id: int, filename: str, db_chunks: List[Any]):
        """
        Extracts child and parent metrics from text buffers and indexes them into ChromaDB.
        """
        print(f"📡 CHROMA PERSISTENCE: Indexing vector fields for Doc ID: {document_id}")
        
        ids = []
        embeddings = []
        documents = []
        metadata_list = []
        
        for chunk in db_chunks:
            raw_content = chunk.content
            
            # Separate the child text block from its parent context string
            if " ||| " in raw_content:
                child_text, parent_context = raw_content.split(" ||| ", 1)
            else:
                child_text = raw_content
                parent_context = raw_content
                
            unique_vector_id = f"doc_{document_id}_chunk_{chunk.chunk_index}"
            vector_embedding = self.embedding_model.encode(child_text).tolist()
            
            ids.append(unique_vector_id)
            embeddings.append(vector_embedding)
            documents.append(child_text) # Vectorized search text entry
            
            # Map the complete parent context block inside the metadata dictionary structure
            metadata_list.append({
                "document_id": document_id,
                "filename": filename,
                "chunk_index": chunk.chunk_index,
                "parent_context": parent_context 
            })

        if ids:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadata_list
            )
        print(f"🟢 CHROMA METRICS: Successfully populated {len(ids)} child vectors in vector indices.")

    def query_precision_context(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Queries child vectors but automatically returns parent context data strings."""
        query_vector = self.embedding_model.encode(query_text).tolist()
        
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k
        )
        
        compiled_contexts = []
        if results and results['metadatas'] and len(results['metadatas'][0]) > 0:
            for idx, metadata in enumerate(results['metadatas'][0]):
                parent_text = metadata.get("parent_context", results['documents'][0][idx])
                
                compiled_contexts.append({
                    "content": parent_text, 
                    "source": metadata.get("filename", "Knowledge Vault"),
                    "page_number": metadata.get("chunk_index", 0) + 1
                })
                
        return compiled_contexts

vector_store_engine = HierarchicalVectorStoreEngine()