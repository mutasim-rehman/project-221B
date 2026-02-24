"""Build ChromaDB index from Sherlock Holmes canon.

Run: python -m src.index
"""
from typing import Iterable

import chromadb

from src.chunker import chunk_document
from src.config import CHROMA_DIR, COLLECTION_NAME, CHUNK_SIZE, CHUNK_OVERLAP
from src.embeddings import get_embeddings
from src.loader import load_documents


def build_index(
    documents: Iterable[dict],
    chroma_path: str | None = None,
    collection_name: str | None = None,
) -> None:
    """Build a Chroma index from the given documents."""
    chroma_path = chroma_path or str(CHROMA_DIR)
    collection_name = collection_name or COLLECTION_NAME

    # Deduplicate documents by id to keep the canon clean.
    seen_ids: set[str] = set()
    unique_docs: list[dict] = []
    for doc in documents:
        doc_id = doc.get("id")
        if not doc_id:
            continue
        if doc_id in seen_ids:
            continue
        seen_ids.add(doc_id)
        unique_docs.append(doc)

    print(f"Loaded {len(unique_docs)} unique documents")

    # Chunk documents with de-duplication of identical chunks per source.
    chunks: list[dict] = []
    seen_chunk_keys: set[tuple[str, str]] = set()
    for doc in unique_docs:
        for c in chunk_document(doc, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
            key = (c["source_id"], c["text"])
            if key in seen_chunk_keys:
                continue
            seen_chunk_keys.add(key)
            chunks.append(c)

    print(f"Created {len(chunks)} chunks after de-duplication")

    texts = [c["text"] for c in chunks]
    print("Embedding chunks (this may take a few minutes)...")
    embeddings = get_embeddings(texts, batch_size=25)

    chroma_client = chromadb.PersistentClient(path=chroma_path)
    # Clear existing collection if rebuilding
    try:
        chroma_client.delete_collection(collection_name)
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name=collection_name,
        metadata={"description": "Sherlock Holmes canon"},
    )

    # ChromaDB has a max batch size of 5461
    batch_size = 5000
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        batch_ids = [f"chunk_{i + j}" for j in range(len(batch))]
        batch_texts = [c["text"] for c in batch]
        batch_embeddings = embeddings[i : i + batch_size]
        batch_metadatas = [
            {
                "source_id": c["source_id"],
                "title": c["title"],
                "collection": c["collection"],
                "year": c.get("year", ""),
                "story_type": c.get("story_type", ""),
                "characters": c.get("characters", []),
                "chunk_index": c.get("chunk_index", 0),
            }
            for c in batch
        ]
        collection.add(
            ids=batch_ids,
            embeddings=batch_embeddings,
            documents=batch_texts,
            metadatas=batch_metadatas,
        )
        print(f"  Added chunks {i + 1}-{i + len(batch)}")

    print(f"Indexed {len(chunks)} chunks into ChromaDB at {chroma_path}")


def main() -> None:
    documents = list(load_documents())
    build_index(documents)


if __name__ == "__main__":
    main()
