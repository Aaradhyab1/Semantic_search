def chunk_text(                             # take in text and return a list of chunks
        text: str,
        chunk_size: int = 200,
        overlap: int = 50                   # overlaps 50 words between chunks
) -> list[str]:
    words = text.split()
    chunks = []

    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = words[start:end]
        chunks.append(" ".join(chunk))
        start += chunk_size - overlap

    return chunks
