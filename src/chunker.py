"""Chunk documents for embedding and retrieval."""
import re
from typing import Iterator


def split_into_paragraphs(text: str, min_length: int = 50) -> list[str]:
    """Split text into paragraphs, filtering very short ones."""
    paras = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paras if p.strip() and len(p.strip()) >= min_length]


def split_long_paragraph(para: str, max_chars: int, overlap: int) -> list[str]:
    """Split a long paragraph into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(para):
        end = start + max_chars
        chunk = para[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks


def chunk_document(
    doc: dict,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> Iterator[dict]:
    """Split a document into chunks with metadata."""
    content = doc["content"]
    paragraphs = split_into_paragraphs(content)

    for para in paragraphs:
        if len(para) <= chunk_size:
            chunks = [para] if para else []
        else:
            chunks = split_long_paragraph(para, chunk_size, chunk_overlap)

        for i, chunk in enumerate(chunks):
            yield {
                "text": chunk,
                "source_id": doc["id"],
                "title": doc["title"],
                "collection": doc["collection"],
                "year": doc.get("year", ""),
            }
