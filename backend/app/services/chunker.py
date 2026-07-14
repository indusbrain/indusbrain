import re
from typing import List, Dict, Any

class CognitiveChunkerService:
    """
    Orchestration engine responsible for transforming unstructured text payloads
    into clean, context-preserving text fragments while preserving source references.
    """
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Regular expression boundary match targeting our custom page headers from Sub-phase 5.2
        self.page_marker_regex = re.compile(r"--- \[STRUCTURED ASSET PAGE BOUNDARY: INDEX (\d+)\] ---")

    def split_document_text(self, raw_text: str) -> List[Dict[str, Any]]:
        """
        Parses text structures sequentially, updates tracking indices, 
        and extracts overlapping chunk arrays.
        """
        chunks_output_matrix = []
        
        # 1. Fragment the text base line using our explicit page boundary headers
        page_splits = self.page_marker_regex.split(raw_text)
        
        # If no page tags exist in the file context string, treat everything as page 1
        if len(page_splits) == 1:
            return self._build_sliding_chunks(raw_text, default_page=1)

        # The regex split pattern returns: [text_before, page_num_1, text_of_page_1, page_num_2, text_of_page_2...]
        current_chunk_global_index = 0
        
        # Start processing from index 1 to read structural pairs cleanly
        for i in range(1, len(page_splits), 2):
            page_num = int(page_splits[i])
            page_content = page_splits[i+1]
            
            if not page_content.strip():
                continue
                
            # Generate sliding windows specifically within the boundaries of the current page layout
            page_chunks = self._build_sliding_chunks(page_content, default_page=page_num)
            
            for chunk_data in page_chunks:
                chunk_data["chunk_index"] = current_chunk_global_index
                chunks_output_matrix.append(chunk_data)
                current_chunk_global_index += 1
                
        return chunks_output_matrix

    def _build_sliding_chunks(self, text_payload: str, default_page: int) -> List[Dict[str, Any]]:
        """
        Applies a localized window sliding matrix across character sets 
        while preserving semantic overlaps.
        """
        local_chunks = []
        cleaned_text = text_payload.strip()
        
        if len(cleaned_text) <= self.chunk_size:
            return [{"content": cleaned_text, "page_number": default_page}]
            
        cursor_pointer = 0
        while cursor_pointer < len(cleaned_text):
            # Calculate target end boundary parameter bounds
            end_pointer = min(cursor_pointer + self.chunk_size, len(cleaned_text))
            
            # If we aren't at the end of the text block, try to roll back to the nearest natural sentence ending
            if end_pointer < len(cleaned_text):
                # Search for the final period, newline, or question mark inside the last 150 characters of our window
                search_buffer = cleaned_text[end_pointer - 150:end_pointer]
                boundary_match = list(re.finditer(r"[\n\.]", search_buffer))
                
                if boundary_match:
                    # Snip right at the natural paragraph boundary mark
                    end_pointer = (end_pointer - 150) + boundary_match[-1].end()

            chunk_text = cleaned_text[cursor_pointer:end_pointer].strip()
            if chunk_text:
                local_chunks.append({
                    "content": chunk_text,
                    "page_number": default_page
                })
                
            # Advance our cursor pointer forward, subtracting the overlap buffer size
            cursor_pointer = end_pointer - self.chunk_overlap
            if cursor_pointer >= len(cleaned_text) or (end_pointer == len(cleaned_text)):
                break
                
            # Safeguard to prevent infinite loops if overlap size conflicts with content bounds
            if cursor_pointer <= 0:
                cursor_pointer = end_pointer

        return local_chunks

cognitive_chunker = CognitiveChunkerService()