"""Build ChromaDB index from Sherlock Holmes canon.

Run: python -m src.index

Requires GEMINI_API_KEY in .env
"""
from src.chunker import chunk_document
from src.config import CHROMA_DIR, COLLECTION_NAME, CHUNK_SIZE, CHUNK_OVERLAP
from src.embeddings import get_embeddings
from src.loader import load_documents

import chromadb
from chromadb.config import Settings


def main() -> None:
    documents = list(load_documents())
    print(f"Loaded {len(documents)} documents")

    chunks = []
    for doc in documents:
        for c in chunk_document(doc, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
            chunks.append(c)

    print(f"Created {len(chunks)} chunks")

    texts = [c["text"] for c in chunks]
    print("Embedding chunks (this may take a few minutes)...")
    embeddings = get_embeddings(texts, batch_size=25)

    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    # Clear existing collection if rebuilding
    try:
        chroma_client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
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
            {"source_id": c["source_id"], "title": c["title"], "collection": c["collection"], "year": c.get("year", "")}
            for c in batch
        ]
        collection.add(
            ids=batch_ids,
            embeddings=batch_embeddings,
            documents=batch_texts,
            metadatas=batch_metadatas,
        )
        print(f"  Added chunks {i + 1}-{i + len(batch)}")

    print(f"Indexed {len(chunks)} chunks into ChromaDB at {CHROMA_DIR}")


if __name__ == "__main__":
    main()
