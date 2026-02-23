"""Query the Sherlock Holmes ChromaDB index (RAG chatbot).

Run: python -m src.query "Who is Mycroft?"
     python -m src.query --chat          # interactive mode
     python -m src.query --raw "..."     # raw chunks only, no LLM

Requires Ollama running locally: ollama run llama3.2
"""
import sys

import chromadb
import ollama

from src.config import CHROMA_DIR, COLLECTION_NAME, OLLAMA_MODEL, TOP_K, CHAT_TOP_K
from src.embeddings import get_embedding


def retrieve(query: str, top_k: int = TOP_K) -> tuple[list[str], list[dict]]:
    """Get top-k chunks for query. Returns (documents, metadatas)."""
    embedding = get_embedding(query)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(name=COLLECTION_NAME)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        include=["documents", "metadatas"],
    )
    return results["documents"][0], results["metadatas"][0]


def generate_answer(query: str, chunks: list[str], metas: list[dict]) -> str:
    """Use local Ollama (Llama) to synthesize a structured answer. No API, no quota."""
    context_parts = []
    for i, (doc, meta) in enumerate(zip(chunks, metas), 1):
        title = meta.get("title", "?")
        context_parts.append(f"[{i}] ({title})\n{doc.strip()}")

    context = "\n\n".join(context_parts)
    prompt = f"""You are a knowledgeable assistant about the Sherlock Holmes canon. Use only the passages below.

Passages:
{context}

Question: {query}

Give a comprehensive, structured answer. Synthesize all relevant facts from the passages. For people (characters, authors): who they are, relation to Holmes/Watson, first appearance, occupation, notable traits. For places or events: what they are, when/where they appear, significance. Use clear formatting (bullets or short paragraphs). If the answer is not in the passages, say so."""

    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": prompt}])
        return response["message"]["content"].strip()
    except Exception as e:
        err = str(e).lower()
        if "connection" in err or "refused" in err or "connect" in err:
            return "Ollama is not running. Install from ollama.com, then run: ollama run llama3.2"
        raise


def run_turn(query: str, raw_mode: bool) -> None:
    """Run a single query and print the result."""
    top_k = CHAT_TOP_K if not raw_mode else TOP_K
    docs, metas = retrieve(query, top_k=top_k)

    if raw_mode:
        for i, (doc, meta) in enumerate(zip(docs, metas), 1):
            title = meta.get("title", "?")
            print(f"--- Result {i} ({title}) ---")
            print(doc.strip())
            print()
    else:
        answer = generate_answer(query, docs, metas)
        print(answer)
        print("\n(Sources:", ", ".join(m.get("title", "?") for m in metas), ")\n")


def main() -> None:
    raw_mode = "--raw" in sys.argv
    chat_mode = "--chat" in sys.argv
    args = [a for a in sys.argv[1:] if a not in ("--raw", "--chat")]

    if chat_mode:
        print("Sherlock Holmes RAG — ask anything about the canon. Type 'quit' or 'exit' to stop.\n")
        while True:
            try:
                query = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break
            if not query:
                continue
            if query.lower() in ("quit", "exit", "q"):
                print("Goodbye.")
                break
            print()
            run_turn(query, raw_mode)
    else:
        if len(args) < 1:
            print("Usage: python -m src.query [--raw] [--chat] <query>")
            print("       python -m src.query --chat   # interactive mode")
            sys.exit(1)
        query = " ".join(args)
        print(f"\nQuery: {query}\n")
        run_turn(query, raw_mode)


if __name__ == "__main__":
    main()
