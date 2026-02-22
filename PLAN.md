# 221B Baker Street — RAG + Character Chat

## Overview

A RAG-powered Sherlock Holmes companion with:
1. **World Q&A** — Ask questions about the canon (stories, characters, events)
2. **Character Chat** — Converse with Sherlock, Watson, Moriarty, Mycroft, Irene Adler, Lestrade

**Stack:** Gemini (LLM + embeddings), ChromaDB, Python/FastAPI, frontend TBD

---

## Phase 1: Project Setup + Data Pipeline
**Goal:** Ingest the canon, chunk it, embed, and store in ChromaDB.

| Step | Task | Output |
|------|------|--------|
| 1.1 | Project setup (venv, deps, .env) | `requirements.txt`, `.env.example` |
| 1.2 | Load all `.txt` files from `raw/` | List of (path, title, collection, year, content) |
| 1.3 | Chunk text (paragraph/semantic splits) | Chunks with metadata (source, title, collection) |
| 1.4 | Embed chunks via Gemini | Vectors |
| 1.5 | Store in ChromaDB with metadata | Persistent `chroma_db/` |

**Acceptance:** Run `python -m src.index` → populate ChromaDB. Can query for similar chunks.

---

## Phase 2: RAG Core — Q&A Pipeline
**Goal:** Retrieve relevant chunks and generate grounded answers.

| Step | Task | Output |
|------|------|--------|
| 2.1 | Retrieval function (query → top-k chunks) | `retrieve(query, k=5)` |
| 2.2 | Q&A prompt template | System + user prompt using retrieved context |
| 2.3 | Gemini generate with context | `ask(question)` → answer |
| 2.4 | Optional: reranking or score threshold | Better relevance |

**Acceptance:** CLI or simple script: `ask("What is the Red-Headed League?")` → accurate, cited answer.

---

## Phase 3: Character Chat Layer
**Goal:** Chat with characters, grounded in canon.

| Step | Task | Output |
|------|------|--------|
| 3.1 | Persona prompts for each character | Sherlock, Watson, Moriarty, Mycroft, Irene Adler, Lestrade |
| 3.2 | Character-specific retrieval (optional) | Filter/boost by character mentions |
| 3.3 | Chat loop: history + RAG context → response | `chat(character, message, history)` |
| 3.4 | Conversation history handling | Last N turns in context |

**Acceptance:** Chat with Sherlock; he responds in character and references real cases.

---

## Phase 4: API Backend
**Goal:** REST API for the frontend.

| Step | Task | Output |
|------|------|--------|
| 4.1 | FastAPI app with CORS | `POST /ask`, `POST /chat` |
| 4.2 | Request/response schemas | Pydantic models |
| 4.3 | Error handling, rate limiting awareness | Graceful 429 handling |
| 4.4 | Health check, docs | `/health`, Swagger UI |

**Acceptance:** Frontend can call API for Q&A and character chat.

---

## Phase 5: Frontend Website
**Goal:** Web UI for users.

| Step | Task | Output |
|------|------|--------|
| 5.1 | Choose stack (React, Next, etc.) | — |
| 5.2 | Q&A page (input → answer) | — |
| 5.3 | Character select + chat UI | — |
| 5.4 | Styling, Victorian / Holmes aesthetic | — |

---

## Project Structure (Target)

```
project-221B/
├── raw/                    # Canon (existing)
├── chroma_db/              # Vector store (created by index)
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── loader.py           # Load .txt files
│   ├── chunker.py          # Split into chunks
│   ├── embeddings.py       # Gemini embeddings
│   ├── index.py            # Build ChromaDB index (Phase 1)
│   ├── retrieval.py        # Query ChromaDB (Phase 2)
│   ├── qa.py               # Q&A pipeline (Phase 2)
│   ├── personas.py         # Character prompts (Phase 3)
│   ├── chat.py             # Character chat (Phase 3)
│   └── api/                # FastAPI (Phase 4)
│       ├── main.py
│       └── routes.py
├── PLAN.md
├── requirements.txt
├── .env.example
└── .env                    # GEMINI_API_KEY (gitignore)
```
