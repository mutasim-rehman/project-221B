"""Embeddings for RAG — local model, no API rate limits."""
from sentence_transformers import SentenceTransformer

# Optimized for semantic search / Q&A retrieval
_MODEL = SentenceTransformer("multi-qa-MiniLM-L6-dot-v1")


def get_embedding(text: str) -> list[float]:
    """Get embedding for a single text."""
    return _MODEL.encode(text, convert_to_numpy=True).tolist()


def get_embeddings(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """Get embeddings for multiple texts. Fast, local, no API limits."""
    embeddings = _MODEL.encode(texts, batch_size=batch_size, convert_to_numpy=True)
    return embeddings.tolist()
