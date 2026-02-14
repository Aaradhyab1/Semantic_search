# chunking.py
import re

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:

    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence_len = len(sentence.split())
        
        if current_length + sentence_len > chunk_size:
            chunks.append(" ".join(current_chunk))

            overlap_buffer = []
            overlap_len = 0
            for s in reversed(current_chunk):
                overlap_buffer.insert(0, s)
                overlap_len += len(s.split())
                if overlap_len >= overlap:
                    break
            
            current_chunk = overlap_buffer
            current_length = overlap_len
            
        current_chunk.append(sentence)
        current_length += sentence_len

    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks