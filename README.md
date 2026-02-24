## 221B Baker Street — Sherlock Holmes RAG

Local, privacy-preserving RAG over the Sherlock Holmes canon, with character
chat (Sherlock, Watson, Moriarty, and others) powered by a local Ollama model
and ChromaDB.

### Setup and environment

- **Clone and install**:

```bash
python -m venv .venv
.venv\Scripts\activate  # on Windows
pip install -r requirements.txt
```

- **Environment variables** (configure in `.env`, never commit this file):
  - **`OLLAMA_MODEL`**: model name to use in Ollama (default: `llama3.2`).
  - **`OLLAMA_TIMEOUT_SECONDS`**: max time to wait for a single generation (default: `60`).
  - **`MAX_QUERY_CHARS`**: max length of a single question in characters (default: `2000`).

Future API-specific variables you will likely want:

- **`APP_PORT`**: port for the FastAPI server.
- **`APP_LOG_LEVEL`**: logging verbosity (e.g. `info`, `debug`).
- **`APP_API_KEY`**: shared secret for simple auth in front of the API.
- **`RATE_LIMIT_PER_MINUTE`**: max requests per client per minute.

Use `.env.example` as a reference; copy it to `.env` and adjust values for your
machine. The real `.env` is already in `.gitignore` and must never be committed.

### Building the index

Put canon `.txt` files under `raw/` in the expected folder structure, then run:

```bash
python -m src.index
```

This:

- Loads and normalises documents (title, collection, year, story type, characters).
- Chunks and de-duplicates paragraphs.
- Embeds and indexes them into a local ChromaDB directory (`chroma_db/`).

### Query modes

The CLI supports three explicit modes:

- **`canon_qa`** (default): answer questions about the canon.
  - `python -m src.query "Who is Mycroft?"`
  - `python -m src.query --chat`
- **`character_chat`**: in-character conversation grounded in canon.
  - `python -m src.query --chat --character sherlock`
  - `python -m src.query --chat --character watson`
- **`raw_chunks`**: inspect retrieved chunks without using an LLM.
  - `python -m src.query --raw "Who is Moriarty?"`

### Prompt-injection-aware RAG

The system prompts used in `generate_answer` and `generate_character_reply`:

- **Treat retrieved passages as facts only.**
- **Explicitly instruct the model to ignore any instructions, prompts, or system
  messages found inside those passages.**
- Only the system prompt and the user's question control behaviour.

This reduces the risk of malicious instructions being smuggled into the index.

### Input validation and resource limits

- **Max input length**: queries longer than `MAX_QUERY_CHARS` are rejected with
  a clear error, both in one-shot and interactive chat modes.
- **LLM timeouts**: all Ollama calls go through a `Client` configured with
  `OLLAMA_TIMEOUT_SECONDS`, so runaway generations fail fast instead of hanging.
- When you add a FastAPI layer, you should also:
  - Enforce request body size limits.
  - Add per-IP / per-API-key rate limiting (e.g. using a middleware or reverse proxy).

### Caching

- `src/cache.py` provides:
  - An in-process **LRU cache for embeddings** used during retrieval, so repeated
    questions (or repeated sub-questions) avoid recomputing sentence embeddings.
  - A simple **answer cache** keyed by `(mode, question, character)` that stores
    the full text answer for repeated queries in the same process.
- Both caches are local to a single process and can be safely discarded between
  deployments. They are purely optimisations and do not affect correctness.

### User preference profiles

- `src/preferences.py` implements a very small **file-backed preference store**
  using `data/preferences.json`:
  - `UserPreferences` fields: `favourite_character`, `strictness`, `verbosity`.
  - `get_preferences(user_id)` / `set_preferences(user_id, prefs)` helpers.
- This is primarily a hook for future authenticated APIs so you can:
  - Default to a user's favourite character in chat.
  - Honour per-user strictness/verbosity settings in prompts and responses.

### Safe logging

- `src/logging_utils.py` provides helpers for **safe request logging**:
  - `generate_session_id()` for non-identifying session IDs.
  - `safe_trim_text()` to truncate and hash user text before logging.
  - `log_request()` to log structured events without dumping secrets or raw headers.
  - `log_rag_trace()` to log, per turn, the (truncated) user query, chosen mode,
    character (if any), top‑k source titles, and answer length.
- When wiring an HTTP API, use these helpers instead of logging raw request
  bodies or environment variables.

### Offline evaluation harness

- `eval/canonical_questions.json` contains a small set of canonical questions
  (e.g. “Who is Sherlock Holmes?”, “Who is Dr. John Watson?”) and expected
  key phrases.
- `eval/run_eval.py` runs the live RAG pipeline (retrieve + generate_answer)
  over these questions and reports, for each:
  - Which expected phrases were present in the answer.
  - Answer length.
  - Aggregate phrase-level recall across the set.
- Run it after changes or before deployments:

```bash
python eval/run_eval.py
```

### Deployment hygiene (recommended)

- **Run under a non-privileged user** in production (no `root`).
- **Serve via HTTPS** using a reverse proxy (e.g. Nginx or Caddy) in front of
  the FastAPI app:
  - Terminate TLS at the proxy.
  - Restrict inbound ports to just HTTPS (and any internal-only ports).
- **Protect the API** if exposed publicly:
  - Require an API key header, basic auth, or a more advanced auth mechanism.
  - Add rate limiting and request size limits at the proxy and/or app level.
- **Keep data local**:
  - Embeddings, index, and prompts are all local; no remote LLM or vector store
    is used by default, which simplifies privacy guarantees.

