def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    """Split document text into overlapping chunks for embeddings."""
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = max(0, end - overlap)
    return chunks
