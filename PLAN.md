# 221B Baker Street — RAG + Character Chat

## Overview

A RAG-powered Sherlock Holmes companion with:
1. **World Q&A** — Ask questions about the canon (stories, characters, events)
2. **Character Chat** — Converse with Sherlock, Watson, Moriarty, Mycroft, Irene Adler, Lestrade

**Stack (current):** Local Ollama LLM, sentence-transformers embeddings, ChromaDB, Python CLI (FastAPI + frontend later).

The focus is on:
- **Core correctness & reliability** (clean indexing, deterministic retrieval, explicit modes, tests).
- **Security, privacy, and deployment hardening** (no leaked secrets, prompt-injection-aware RAG, safe logging).

---

## Phase 1: Project Setup + Data Pipeline
**Goal:** Ingest the canon, chunk it, embed, and store in ChromaDB.

| Step | Task | Output |
|------|------|--------|
| 1.1 | Project setup (venv, deps, `.env` pattern) | `requirements.txt`, `.env.example`, `.env` in `.gitignore` |
| 1.2 | Load all `.txt` files from `raw/` | List of docs: (id, path, title, collection, year, story_type, characters, content) |
| 1.3 | Chunk text (paragraph/overlap splits) | Chunks with metadata (source_id, title, collection, year, story_type, characters, chunk_index) |
| 1.4 | Embed chunks via local sentence-transformers model | Embedding vectors (no external API) |
| 1.5 | Store in ChromaDB with metadata | Persistent `chroma_db/` collection `sherlock_holmes` |

**Acceptance:** Run `python -m src.index` → builds a clean, deduplicated ChromaDB index. Chunks have rich metadata and can be inspected via queries.

---

## Phase 2: RAG Core — Q&A Pipeline
**Goal:** Retrieve relevant chunks and generate grounded answers.

| Step | Task | Output |
|------|------|--------|
| 2.1 | Retrieval function (query → top-k chunks) | `retrieve(query, top_k)` in `src.query` |
| 2.2 | Q&A prompt template (canon_qa mode) | `generate_answer(query, chunks, metas)` with explicit instructions to ignore instructions in retrieved text |
| 2.3 | Ollama `chat` with context | `python -m src.query "Who is Mycroft?"` → answer + sources |
| 2.4 | Mode router (canon_qa vs raw_chunks) | `Mode` enum and `run_turn(query, mode)` |

**Acceptance:** CLI: `python -m src.query "What is the Red-Headed League?"` → accurate, cited answer; `--raw` shows the underlying chunks.

---

## Phase 3: Character Chat Layer
**Goal:** Chat with characters, grounded in canon.

| Step | Task | Output |
|------|------|--------|
| 3.1 | Persona definitions for each character | `CHARACTERS` in `config.py` (Sherlock, Watson, Moriarty, Mycroft, Irene, Lestrade) |
| 3.2 | Character prompt template (character_chat mode) | `generate_character_reply(character_key, query, chunks, metas, history)` with injection-resistant system prompt |
| 3.3 | Character chat loop (CLI) | `python -m src.query --chat --character sherlock` (interactive) |
| 3.4 | Conversation history handling | Recent N turns via `history` passed into `generate_character_reply` |

**Acceptance:** Chat with Sherlock; he responds in character, grounded in canon passages, and ignores any instructions embedded in the corpus.

---

## Phase 4: API Backend
**Goal:** REST API for the frontend, with security and privacy as first-class concerns.

| Step | Task | Output |
|------|------|--------|
| 4.1 | FastAPI app with CORS | `POST /ask`, `POST /chat` endpoints wrapping existing `retrieve` / `generate_*` |
| 4.2 | Request/response schemas | Pydantic models with max lengths matching `MAX_QUERY_CHARS` |
| 4.3 | Auth + rate limiting | API key header, per-IP/per-key rate limiting (429s), wired via middleware or proxy |
| 4.4 | Safe logging | Use `logging_utils.log_request` + `generate_session_id` for non-PII logs |
| 4.5 | Health check, docs | `/health`, OpenAPI/Swagger UI |

**Acceptance:** Frontend can call API for Q&A and character chat; oversized/abusive inputs are rejected; logs avoid raw PII; secrets live only in `.env`.

---

## Phase 5: Frontend Website
**Goal:** Web UI for users.

| Step | Task | Output |
|------|------|--------|
| 5.1 | Choose stack (React, Next, etc.) | Frontend project |
| 5.2 | Q&A page (input → answer) | Calls `POST /ask` |
| 5.3 | Character select + chat UI | Calls `POST /chat` with session ids |
| 5.4 | Styling, Victorian / Holmes aesthetic | Themed UI |

---

## Project Structure (Current/Target)

```
project-221B/
├── raw/                    # Canon text files
├── chroma_db/              # Vector store (created by index)
├── src/
│   ├── __init__.py
│   ├── config.py           # Paths, env vars, character personas, limits
│   ├── loader.py           # Load .txt files with rich metadata
│   ├── chunker.py          # Split into chunks with overlap
│   ├── embeddings.py       # Local sentence-transformers embeddings
│   ├── index.py            # Build ChromaDB index (Phase 1)
│   ├── query.py            # Retrieval + canon_qa + character_chat + CLI (Phase 2–3)
│   ├── logging_utils.py    # Safe logging helpers for API (Phase 4)
│   └── api/                # FastAPI (Phase 4, planned)
│       ├── main.py
│       └── routes.py
├── tests/                  # Pytest unit/smoke tests for RAG pipeline
├── PLAN.md
├── README.md
├── requirements.txt
├── .env.example
└── .env                    # Local-only config (gitignored; never committed)
```
