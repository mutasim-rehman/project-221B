# 221B Baker Street — Internal Testing & Deployment

## Architecture

```
┌─────────────────┐         API          ┌─────────────────────┐
│   Frontend      │ ◄──────────────────► │   Backend/Chatbot   │
│   (Vercel)      │   JSON over HTTP     │   (Replit)          │
└─────────────────┘                      └─────────────────────┘
```

- **Backend**: FastAPI server exposing `/api/six-case-story` and `/api/six-chatroom`
- **Frontend**: React/Vite app; uses `VITE_API_BASE` to target the backend
- **Communication**: REST API (POST JSON, receive JSON)

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

### Backend on Replit

The project includes a `.replit` file that uses **CPU-only PyTorch** to avoid deployment timeout during the bundle phase. Without this, the default CUDA-enabled PyTorch adds ~2GB and causes the deployment to time out.

1. Create a Replit project and add your code (or import from GitHub)
2. The `.replit` file configures the deploy build and run commands automatically
3. Set Replit secrets / env vars:
   - `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS` if needed
   - `CORS_ORIGINS` — add your Vercel URL, e.g. `https://your-app.vercel.app`
3. Ensure ChromaDB index is built (e.g. in a setup script or one-time run)
4. Run: `python -m src.api.main` or `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`
5. Note the Replit URL (e.g. `https://your-app-name.replit.app`)

**If deployment still times out:** The build now skips the index step when `chroma_db/` is already in the repo. To use this:

1. Build locally: `python -m src.index`
2. Commit `chroma_db/` (it is no longer in `.gitignore`)
3. Push and redeploy — the build will skip indexing and stay much smaller

### Frontend on Vercel

1. Deploy the `frontend/` folder to Vercel
2. Add environment variable for the build:
   - `VITE_API_BASE` = your Replit backend URL (e.g. `https://your-app-name.replit.app`)
3. Redeploy so the frontend is built with the correct API base

### CORS for production

The backend allows `localhost:5173` and `localhost:3000` by default. For production, set:

```bash
CORS_ORIGINS=https://your-vercel-app.vercel.app
```

Or multiple origins, comma-separated:

```bash
CORS_ORIGINS=https://app.example.com,https://staging.example.com
```

---

## Environment variables

| Variable       | Where      | Purpose                                              |
|----------------|------------|------------------------------------------------------|
| `VITE_API_BASE`| Frontend   | Backend base URL (no trailing slash)                 |
| `CORS_ORIGINS` | Backend    | Comma-separated allowed origins for cross-origin     |
| `APP_PORT`     | Backend    | Port for the API server (default: 8000)              |
| `OLLAMA_MODEL` | Backend    | Ollama model name                                    |
