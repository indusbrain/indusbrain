const API_BASE_URL = "http://localhost:8000/api/v1";

export interface DocumentMetadata {
  id: number;
  filename: string;
  status: 'pending' | 'parsed' | 'failed' | 'embedded';
  s3_key: string;
  created_at: string;
}

export interface QueryResponse {
  response: string;
  confidence_score: number;
  reasoning_path: string[];
  current_agent: string;
}

export const apiService = {
  async uploadDocument(file: File): Promise<DocumentMetadata> {
    const formData = new FormData();
    formData.append("file", file);
    
    const response = await fetch(`${API_BASE_URL}/ingestion/upload`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) throw new Error("File upload gateway rejected the asset.");
    return response.json();
  },

  async parseDocument(id: number): Promise<{ character_count_processed: number }> {
    const response = await fetch(`${API_BASE_URL}/ingestion/parse/${id}`, { method: "POST" });
    if (!response.ok) throw new Error("Programmatic/OCR layout parsing engine failed.");
    return response.json();
  },

  async chunkDocument(id: number): Promise<{ total_semantic_chunks_generated: number }> {
    const response = await fetch(`${API_BASE_URL}/ingestion/chunk/${id}`, { method: "POST" });
    if (!response.ok) throw new Error("Cognitive sliding-window chunker collapsed.");
    return response.json();
  },

  async embedDocument(id: number): Promise<{ total_vectors_indexed: number }> {
    const response = await fetch(`${API_BASE_URL}/ingestion/embed/${id}`, { method: "POST" });
    if (!response.ok) throw new Error("Multi-model vectorization pipeline rejected the arrays.");
    return response.json();
  },

  async graphDocument(id: number): Promise<{ total_nodes_synced: number }> {
    const response = await fetch(`${API_BASE_URL}/ingestion/graph/${id}`, { method: "POST" });
    if (!response.ok) throw new Error("Neo4j topological database sync failed.");
    return response.json();
  },

  async submitQuery(queryText: string): Promise<QueryResponse> {
    const response = await fetch(`${API_BASE_URL}/query/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: queryText }),
    });
    if (!response.ok) throw new Error("Multi-agent decision compiler crashed.");
    return response.json();
  }
};