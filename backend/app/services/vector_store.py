import os
import chromadb
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer

class HierarchicalVectorStoreEngine:
    """
    Enterprise ChromaDB Connection Manager. Stores high-density child vectors 
    anchored to complete parent context strings inside the metadata fields.
    """
    COLLECTION_NAME = "industrial_knowledge_vault"

    def __init__(self):
        self.chroma_host = os.getenv("CHROMA_HOST", "localhost")
        self.chroma_port = int(os.getenv("CHROMA_PORT", 8001))

        # Lazy resources. Nothing here may raise: this module is imported at
        # application startup, and a hard failure would stop the whole API from
        # booting just because a database container was not running yet.
        self.chroma_client = None
        self._collection = None
        self._embedding_model = None

    # ------------------------------------------------------------------
    # Lazy resource accessors (connect on first real use, retry on failure)
    # ------------------------------------------------------------------
    @property
    def embedding_model(self) -> SentenceTransformer:
        """Loads the sentence-transformer once, on first use rather than on import."""
        if self._embedding_model is None:
            print("🧠 EMBEDDING ENGINE: Loading all-MiniLM-L6-v2 into memory...")
            self._embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        return self._embedding_model

    @property
    def collection(self):
        """
        Returns the live Chroma collection, or None if Chroma is unreachable.
        Retries on every access so the app self-heals once the container starts.
        """
        if self._collection is not None:
            return self._collection
        try:
            if self.chroma_client is None:
                self.chroma_client = chromadb.HttpClient(host=self.chroma_host, port=self.chroma_port)
            self._collection = self.chroma_client.get_or_create_collection(name=self.COLLECTION_NAME)
            print(f"🟢 CHROMA CORE: Connected to '{self.COLLECTION_NAME}' at {self.chroma_host}:{self.chroma_port}")
        except Exception as connection_error:
            self.chroma_client = None
            self._collection = None
            print(f"⚠️ CHROMA OFFLINE: Vector store unreachable ({connection_error}). Retrying on next use.")
        return self._collection

    @property
    def is_online(self) -> bool:
        return self.collection is not None

    def index_document_chunks(self, document_id: int, filename: str, db_chunks: List[Any]):
        """
        Extracts child and parent metrics from text buffers and indexes them into ChromaDB.
        """
        target_collection = self.collection
        if target_collection is None:
            print(f"⚠️ CHROMA PERSISTENCE SKIPPED: Vector store offline, document {document_id} not indexed.")
            return

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
            # upsert, NOT add: chunk ids are deterministic (doc_<id>_chunk_<n>), so
            # re-uploading a document would otherwise be silently ignored by Chroma
            # and the vector store would drift out of sync with Postgres.
            target_collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadata_list
            )
        print(f"🟢 CHROMA METRICS: Successfully populated {len(ids)} child vectors in vector indices.")

    def purge_document_vectors(self, document_id: int) -> None:
        """Removes every vector belonging to a document (used when a doc is deleted)."""
        target_collection = self.collection
        if target_collection is None:
            return
        try:
            target_collection.delete(where={"document_id": document_id})
            print(f"🧹 CHROMA CLEANUP: Purged vectors for document {document_id}.")
        except Exception as purge_error:
            print(f"⚠️ CHROMA CLEANUP FAILED for document {document_id}: {purge_error}")

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