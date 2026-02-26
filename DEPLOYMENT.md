# 221B Baker Street — Internal Testing & Deployment

## Architecture

**Option A — Hugging Face Space (Gradio, standalone):**
```
┌─────────────────────────────────────┐
│   Gradio app (HF Space "appledoor") │
│   Character chat, Case story,       │
│   Six-character chatroom            │
└─────────────────────────────────────┘
```

**Option B — React frontend + FastAPI backend:**
```
┌─────────────────┐         API          ┌─────────────────────┐
│   Frontend      │ ◄──────────────────► │   Backend           │
│   (Vercel)      │   JSON over HTTP     │   (Railway, etc.)   │
└─────────────────┘                      └─────────────────────┘
```

---

## Phase 1: Internal Testing (Local)

Connect frontend and backend on your machine before deploying.

### Prerequisites

- Python venv, dependencies, index built (`python -m src.index`)
- Ollama running with the model (e.g. `llama3.2`)
- Node.js for the frontend

**Tip (reduces first-message delay):** Keep the Ollama model loaded before starting the backend:

```bash
ollama run llama3.2:1b
# Leave this running in a separate terminal, then start the backend
```

The backend also runs a warmup at startup (embedding model, ChromaDB, Ollama) in the background, so the first user request is typically faster.

### 1. Start the backend

From project root:

```bash
python -m src.api.main
# or: uvicorn src.api.main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`. Health check: `GET http://localhost:8000/health`

### 2. Configure and start the frontend

```bash
cd frontend
cp .env.example .env
# Edit .env: VITE_API_BASE=http://localhost:8000
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

### 3. Test the chatbots

1. Open `http://localhost:5173` in a browser
2. Go to **Six-character experiences**
3. Try **Case-based story** — enter a case prompt, generate a story
4. Try **Character chatroom** — send a message and see the six characters respond

If `VITE_API_BASE` is unset or wrong, the frontend falls back to mock data.

---

## Phase 2: Deployment

### Backend on Hugging Face Spaces (Gradio)

The `huggingface/appledoor/` directory contains a complete Hugging Face Space. Push it to your Space:

1. The Space is in `huggingface/appledoor/` (cloned from your HF Space)
2. Add **HF_TOKEN** to Space secrets (Settings → Repository secrets) for the Inference API
3. Push to the Space: `cd huggingface/appledoor && git add . && git commit -m "..." && git push`
4. HF will build and run the Gradio app. The index is built automatically on first run (or pre-build locally and commit `chroma_db/`)

### Frontend + Gradio Space (Option A — recommended)

Connect the React frontend to your deployed HF Gradio Space:

1. Deploy the `frontend/` folder to Vercel (or any static host)
2. Add environment variable: `VITE_GRADIO_SPACE` = `mutasim-rehman/appledoor` (your Space path)
3. For private Spaces, add `VITE_HF_TOKEN` = your HF token
4. Redeploy so the frontend is built with the correct config

The frontend uses `@gradio/client` to call your Space's API endpoints: `/chat`, `/gen_case_story`, `/chat_1`.

### Frontend on Vercel (Option B — FastAPI backend)

1. Deploy the `frontend/` folder to Vercel
2. Add environment variable: `VITE_API_BASE` = your backend URL
3. Redeploy so the frontend is built with the correct API base

---

## Environment variables

| Variable            | Where      | Purpose                                              |
|---------------------|------------|------------------------------------------------------|
| `VITE_GRADIO_SPACE` | Frontend   | HF Space path (e.g. `user/space-name`) for Gradio API |
| `VITE_HF_TOKEN`     | Frontend   | HF token for private Spaces (optional)               |
| `VITE_API_BASE`     | Frontend   | Backend base URL when using FastAPI (no trailing slash) |
| `CORS_ORIGINS`      | Backend    | Comma-separated allowed origins for cross-origin     |
| `APP_PORT`          | Backend    | Port for the API server (default: 8000)              |
| `OLLAMA_MODEL`      | Backend    | Ollama model name                                    |
