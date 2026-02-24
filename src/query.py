"""Query the Sherlock Holmes ChromaDB index (RAG chatbot).

Explicit modes:
- canon_qa      — question answering over canon passages (LLM)
- character_chat — in-character roleplay grounded in canon passages
- raw_chunks    — inspect retrieved chunks directly (no LLM)

Run:
    python -m src.query "Who is Mycroft?"
    python -m src.query --chat                      # interactive canon_qa mode
    python -m src.query --raw "..."                 # raw_chunks mode
    python -m src.query --chat --character sherlock # character_chat mode

Requires Ollama running locally: ollama run llama3.2
"""
import sys
from enum import Enum

import chromadb
import ollama

from src.config import CHROMA_DIR, COLLECTION_NAME, OLLAMA_MODEL, TOP_K, CHAT_TOP_K, CHARACTERS
from src.embeddings import get_embedding


class Mode(str, Enum):
    CANON_QA = "canon_qa"
    CHARACTER_CHAT = "character_chat"
    RAW_CHUNKS = "raw_chunks"


def retrieve(query: str, top_k: int = TOP_K) -> tuple[list[str], list[dict]]:
    """Get top-k chunks for query. Returns (documents, metadatas)."""
    embedding = get_embedding(query)
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception as e:  # pragma: no cover - defensive, exact error type is backend-specific
        raise RuntimeError(
            f"Vector index not found at {CHROMA_DIR} (collection '{COLLECTION_NAME}'). "
            "Build it first by running: python -m src.index"
        ) from e

    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        include=["documents", "metadatas"],
    )
    return results["documents"][0], results["metadatas"][0]


def _build_context(chunks: list[str], metas: list[dict]) -> str:
    """Format retrieved chunks into a numbered context block."""
    context_parts = []
    for i, (doc, meta) in enumerate(zip(chunks, metas), 1):
        title = meta.get("title", "?")
        context_parts.append(f"[{i}] ({title})\n{doc.strip()}")
    return "\n\n".join(context_parts)


def generate_answer(query: str, chunks: list[str], metas: list[dict]) -> str:
    """Use local Ollama (Llama) to synthesize a structured answer. No API, no quota."""
    context = _build_context(chunks, metas)
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
        if "requires more system memory" in err or "more system memory" in err:
            return (
                "The configured Ollama model requires more system memory than is available.\n"
                "Choose a smaller model (e.g. a 1B/2B variant), `ollama pull` it, and set OLLAMA_MODEL "
                "in your .env to that model name, then restart the program."
            )
        raise


def _normalise_character_key(name: str) -> str | None:
    """Resolve a character name or alias to a configured key."""
    key = name.strip().lower()
    if key in CHARACTERS:
        return key

    # Also allow full display names (e.g. "Sherlock Holmes").
    for cfg_key, cfg in CHARACTERS.items():
        if key == cfg.get("name", "").lower():
            return cfg_key
    return None


def _format_history(character_key: str, history: list[tuple[str, str]], max_turns: int = 6) -> str:
    """Render recent conversation history as text to include in the prompt."""
    if not history:
        return "No prior conversation."

    char_name = CHARACTERS[character_key]["name"]
    recent = history[-max_turns:]
    parts: list[str] = []
    for user_text, char_reply in recent:
        parts.append(f"User: {user_text}\n{char_name}: {char_reply}")
    return "\n\n".join(parts)


def generate_character_reply(
    character_key: str,
    query: str,
    chunks: list[str],
    metas: list[dict],
    history: list[tuple[str, str]],
) -> str:
    """Generate an in-character reply for the chosen persona."""
    cfg = CHARACTERS[character_key]
    char_name = cfg["name"]
    profile = cfg["profile"]
    context = _build_context(chunks, metas)
    history_text = _format_history(character_key, history)

    prompt = f"""You are roleplaying as {char_name} from the Sherlock Holmes stories.

Character profile:
{profile}

Your rules:
- Stay strictly in-character: match {char_name}'s tone, knowledge, and manner of speech.
- Treat the conversation as taking place in-universe in late 19th / early 20th century London,
  unless the user explicitly asks you to step out of character.
- Use details from the canon passages below to keep events and relationships accurate,
  but do not mention these passages or 'sources' explicitly.
- Do not say that you are an AI or a language model.

Conversation so far:
{history_text}

Canon passages:
{context}

User: {query}

Respond with a single, concise in-character reply from {char_name}."""

    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": prompt}])
        return response["message"]["content"].strip()
    except Exception as e:
        err = str(e).lower()
        if "connection" in err or "refused" in err or "connect" in err:
            return "Ollama is not running. Install from ollama.com, then run: ollama run llama3.2"
        if "requires more system memory" in err or "more system memory" in err:
            return (
                "The configured Ollama model requires more system memory than is available.\n"
                "Choose a smaller model (e.g. a 1B/2B variant), `ollama pull` it, and set OLLAMA_MODEL "
                "in your .env to that model name, then restart the program."
            )
        raise


def run_turn(query: str, mode: Mode) -> None:
    """Run a single non-character query and print the result."""
    if mode == Mode.RAW_CHUNKS:
        docs, metas = retrieve(query, top_k=TOP_K)
        for i, (doc, meta) in enumerate(zip(docs, metas), 1):
            title = meta.get("title", "?")
            print(f"--- Result {i} ({title}) ---")
            print(doc.strip())
            print()
    elif mode == Mode.CANON_QA:
        docs, metas = retrieve(query, top_k=CHAT_TOP_K)
        answer = generate_answer(query, docs, metas)
        print(answer)
        print("\n(Sources:", ", ".join(m.get("title", "?") for m in metas), ")\n")
    else:
        raise ValueError(f"run_turn does not support mode {mode!r}")


def run_character_turn(
    character_key: str,
    query: str,
    history: list[tuple[str, str]],
) -> str:
    """Run a single in-character turn and return the character's reply."""
    docs, metas = retrieve(query, top_k=CHAT_TOP_K)
    reply = generate_character_reply(character_key, query, docs, metas, history)
    print(reply)
    print()
    return reply


def main() -> None:
    raw_mode = False
    chat_mode = False
    character_key: str | None = None
    query_parts: list[str] = []

    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--raw":
            raw_mode = True
        elif a == "--chat":
            chat_mode = True
        elif a == "--character":
            if i + 1 >= len(argv):
                print("Error: --character requires a name (e.g. sherlock, watson, moriarty).")
                sys.exit(1)
            maybe_key = _normalise_character_key(argv[i + 1])
            if maybe_key is None:
                valid = ", ".join(sorted(CHARACTERS.keys()))
                print(f"Unknown character '{argv[i + 1]}'. Choose one of: {valid}")
                sys.exit(1)
            character_key = maybe_key
            i += 1  # skip name
        else:
            query_parts.append(a)
        i += 1

    # Decide mode based on flags for clarity and testability.
    if chat_mode:
        mode = Mode.CHARACTER_CHAT if character_key is not None else Mode.CANON_QA
    else:
        if character_key is not None:
            mode = Mode.CHARACTER_CHAT
        elif raw_mode:
            mode = Mode.RAW_CHUNKS
        else:
            mode = Mode.CANON_QA

    if chat_mode:
        if mode == Mode.CHARACTER_CHAT and character_key is not None:
            cfg = CHARACTERS[character_key]
            print(f"Chatting with {cfg['name']} (model: {OLLAMA_MODEL}) — type 'quit' or 'exit' to stop.\n")
            history: list[tuple[str, str]] = []
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
                reply = run_character_turn(character_key, query, history)
                history.append((query, reply))
        else:
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
                run_turn(query, Mode.CANON_QA)
    else:
        if not query_parts:
            print("Usage: python -m src.query [--raw] [--chat] [--character <name>] <query>")
            print("       python -m src.query --chat")
            print("       python -m src.query --chat --character sherlock")
            sys.exit(1)
        query = " ".join(query_parts)
        if mode == Mode.CHARACTER_CHAT and character_key is not None:
            # One-off in-character answer.
            reply = run_character_turn(character_key, query, history=[])
            # No extra sources printed to keep immersion.
        else:
            print(f"\nMode: {mode.value}\nQuery: {query}\n")
            run_turn(query, mode)


if __name__ == "__main__":
    main()
