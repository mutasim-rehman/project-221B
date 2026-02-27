# 221B Baker Street — Deployment Guide

A developer’s guide to deploying this project: architecture, steps, hurdles, and solutions.

---

## Architecture Overview

**Option A — Hugging Face Space + Vercel (recommended for production):**

```
┌─────────────────────────────────────┐     ┌─────────────────────────────────────┐
│   React frontend (Vercel)           │     │   Gradio app (HF Space "appledoor")  │
│   VITE_GRADIO_SPACE → @gradio/client│ ──► │   Character chat, Case story,        │
│   Static SPA                        │     │   Six-character chatroom             │
└─────────────────────────────────────┘     └─────────────────────────────────────┘
```

**Option B — React frontend + FastAPI backend (self-hosted):**

```
┌─────────────────┐         API          ┌─────────────────────┐
│   Frontend      │ ◄──────────────────► │   Backend           │
│   (Vercel)      │   JSON over HTTP     │   (Railway, etc.)   │
└─────────────────┘                      └─────────────────────┘
```

---

## How This Project Was Deployed

### Summary

- **Frontend**: React + Vite, deployed to Vercel. Uses `@gradio/client` to talk to the Hugging Face Space.
- **Backend (prod)**: Gradio app in `huggingface/appledoor/`, deployed as a Hugging Face Space. Uses HF Inference API (Qwen 7B) and ChromaDB for RAG. Includes character chat, case story, six-character chatroom, and **interactive canon mode** (RAG Q&A).
- **Backend (local)**: FastAPI (`src.api.main`) with Ollama for local dev.

### Deployment Flow

1. Create a Hugging Face Space, push the contents of `huggingface/appledoor/`.
2. Deploy `frontend/` to Vercel, set `VITE_GRADIO_SPACE` to `username/appledoor`.
3. The frontend connects to the Space via Gradio’s client SDK; no custom API server is required.

---

## Phase 1: Local Development

### Prerequisites

- Python venv, dependencies, index built (`python -m src.index`)
- Ollama running (e.g. `llama3.2`)
- Node.js for the frontend

**Tip:** Keep the model loaded before starting the backend:

```bash
ollama run llama3.2:1b
# Leave running, then start the backend in another terminal
```

### Start backend

```bash
python -m src.api.main
# or: uvicorn src.api.main:app --reload --port 8000
```

Health check: `GET http://localhost:8000/health`

### Start frontend

```bash
cd frontend
cp .env.example .env
# Edit .env: VITE_API_BASE=http://localhost:8000  (for FastAPI) or VITE_GRADIO_SPACE=user/appledoor (for HF)
npm install
npm run dev
```

Frontend: `http://localhost:5173`. Without a backend config, it uses mock data.

---

## Phase 2: Hugging Face Space Deployment

### What We Deploy

The `huggingface/appledoor/` directory is a self-contained Gradio Space:

- `app.py` — Gradio UI and entry point
- `src/` — RAG pipeline (index, query, backend_api)
- `raw/` — Sherlock Holmes corpus
- `chroma_db/` — vector index (optional; built on first run if missing)

### Steps

1. Create a Space at [huggingface.co/spaces](https://huggingface.co/spaces) (Gradio SDK).
2. Clone the Space, replace its contents with `huggingface/appledoor/`, or push from a repo linked to the Space.
3. Add **HF_TOKEN** under Settings → Repository secrets.
4. Enable Inference Providers: [huggingface.co/settings/inference-providers](https://huggingface.co/settings/inference-providers) (e.g. Together, Groq; free tiers exist).
5. Push; HF builds and runs the app.

### Hurdles and Solutions

| Hurdle | Cause | Solution |
|--------|-------|----------|
| “Please add HF_TOKEN to your Space secrets” | Token not configured | Add `HF_TOKEN` (or `HUGGING_FACE_HUB_TOKEN`) in Space Settings → Repository secrets |
| No model / no credits | Inference provider not set up | Enable at least one provider in [inference-providers](https://huggingface.co/settings/inference-providers) |
| First run takes 5–10+ minutes | ChromaDB index built at startup | Pre-build locally: `cd huggingface/appledoor && python -m src.index`, then commit `chroma_db/` to the Space repo |
| App fails with path errors | Paths assume Space root | `app.py` uses `os.path.dirname(__file__)` so paths resolve from the app root |
| Gradio client can’t find endpoints | Endpoint names differ | Frontend must use `/chat`, `/gen_case_story`, `/chat_1`, `/canon_qa` as in `app.py`; see `frontend/src/api.ts` |

### Gradio Endpoint Mapping

The frontend (`api.ts`) expects these predict calls:

- Character chat → `/chat` with `message`, `param_2` (character key)
- Case story → `/gen_case_story` with `prompt`
- Six-character chatroom → `/chat_1` with `message`
- Interactive canon Q&A → `/canon_qa` with `message`

Changing these in `app.py` requires matching updates in the frontend.

### Hugging Face Terminal Commands

From the project root or `huggingface/appledoor`:

```bash
# Navigate to the HF Space directory
cd huggingface/appledoor

# Create Python virtual environment and install dependencies
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt

# Build ChromaDB index (do this before first push to avoid long cold-start)
python -m src.index

# Run the Gradio app locally (optional, for testing)
python app.py

# Push to Hugging Face (after cloning the Space and adding remote)
git add .
git commit -m "Add interactive canon mode"
git push origin main
```

If deploying a new Space from scratch:

```bash
# Install Hugging Face CLI (if not installed)
pip install huggingface_hub

# Login (creates ~/.huggingface/token)
huggingface-cli login

# Create Space and upload (from project root)
cd huggingface/appledoor
huggingface-cli repo create appledoor --type space --space_sdk gradio
git init
git remote add origin https://huggingface.co/spaces/YOUR_USERNAME/appledoor
git add .
git commit -m "Initial 221B Space with canon mode"
git push -u origin main
```

Replace `YOUR_USERNAME` with your Hugging Face username.

---

## Phase 3: Vercel Deployment (Frontend)

### What We Deploy

The `frontend/` directory: a Vite React SPA that can talk to either:

- A Hugging Face Gradio Space (via `@gradio/client`), or  
- A FastAPI backend (via `fetch` to `VITE_API_BASE`).

### Steps

1. Import the project in Vercel (from GitHub/GitLab/Bitbucket).
2. Set root directory to `frontend` (or configure build to use it).
3. Add environment variables:
   - `VITE_GRADIO_SPACE` = `username/appledoor` (for HF Space)
   - `VITE_HF_TOKEN` = `hf_xxx` (only for private Spaces)
   - Or `VITE_API_BASE` = backend URL (for FastAPI)
4. Deploy. Vite’s default output is `dist/`, which Vercel serves as a static site.

### Hurdles and Solutions

| Hurdle | Cause | Solution |
|--------|-------|----------|
| Env vars not available in app | Vite only embeds vars with `VITE_` prefix | Use `VITE_GRADIO_SPACE`, `VITE_API_BASE`, `VITE_HF_TOKEN` — never `GRADIO_SPACE` etc. |
| 404 on refresh / deep links | SPA routing, no server fallback | Add `vercel.json` with rewrites (see below) |
| CORS errors calling HF Space | Cross-origin request blocked | HF Spaces typically allow Gradio client origins; if issues persist, check Space visibility and token |
| “API not connected” in UI | Env vars not set or wrong at build time | Ensure env vars are set in Vercel project before build; rebuild after changes |

### Optional: SPA Routing Rewrites

If you use client-side routing and want clean URLs:

```json
// frontend/vercel.json (or root vercel.json with "frontend" as root)
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

---

## Environment Variables Reference

| Variable | Where | Purpose |
|----------|-------|---------|
| `VITE_GRADIO_SPACE` | Frontend | HF Space path, e.g. `user/space-name` |
| `VITE_HF_TOKEN` | Frontend | HF token for private Spaces (baked into build; use only if necessary) |
| `VITE_API_BASE` | Frontend | FastAPI base URL (no trailing slash) |
| `HF_TOKEN` | HF Space | HF Inference API access |
| `CORS_ORIGINS` | Backend | Comma-separated allowed origins (FastAPI) |
| `APP_PORT` | Backend | API port (default 8000) |
| `OLLAMA_MODEL` | Backend | Ollama model for local dev |

---

## .replit — Keep or Remove?

**Recommendation: remove `.replit` from the repo** (or add it to `.gitignore`) unless you use [Replit](https://replit.com) for development.

- `.replit` configures the Replit IDE (run command, root directory, etc.).
- If you develop locally or on Vercel/HF, it has no effect and adds noise.
- If you later want to run or demo on Replit, you can reintroduce a minimal `.replit` and keep it out of the main deployment docs.

If you prefer to keep it for Replit users, add a short note in the README so others know what it’s for.
