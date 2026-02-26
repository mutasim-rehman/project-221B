"""FastAPI server exposing six-case-story and six-chatroom endpoints for the frontend."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.backend_api import character_chat_turn, six_character_case_story, six_character_chatroom_turn
from src.config import MAX_QUERY_CHARS
from src.logging_utils import get_request_logger, log_request


def _get_cors_origins() -> list[str]:
    """CORS origins: localhost for internal testing + env override for deployment."""
    origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    extra = os.getenv("CORS_ORIGINS", "")
    if extra:
        origins.extend(s.strip() for s in extra.split(",") if s.strip())
    return origins


# --- Request/Response models ---
class SixCaseStoryRequest(BaseModel):
    case_prompt: str = Field(..., min_length=1, max_length=MAX_QUERY_CHARS)
    session_id: str = Field(..., min_length=1)
    strictness: str = Field(default="creative", pattern="^(creative|balanced|strict)$")


class SixCaseStoryResponse(BaseModel):
    story: str
    characters: list[str]
    sources: list[str]
    mode: str
    setting: str


class SixChatroomRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUERY_CHARS)
    session_id: str = Field(..., min_length=1)
    strictness: str = Field(default="balanced", pattern="^(creative|balanced|strict)$")


class SixChatroomResponse(BaseModel):
    scene: str
    characters: list[str]
    sources: list[str]
    mode: str
    setting: str


class CharacterChatRequest(BaseModel):
    character_key: str = Field(..., pattern="^(sherlock|watson|moriarty|irene|mycroft|lestrade)$")
    question: str = Field(..., min_length=1, max_length=MAX_QUERY_CHARS)
    session_id: str = Field(..., min_length=1)
    strictness: str = Field(default="strict", pattern="^(creative|balanced|strict)$")


class CharacterChatResponse(BaseModel):
    reply: str
    character: str
    sources: list[str]
    mode: str
    strictness: str


# --- Warmup ---
def _warmup_blocking() -> None:
    """Load models at startup so the first user request doesn't pay cold-start (5–25 sec)."""
    try:
        from src.cache import get_embedding
        get_embedding("warmup")
        logger.info("Warmup: embedding model loaded")
    except Exception as e:
        logger.warning("Warmup: embedding load failed: %s", e)
    try:
        import chromadb
        from src.config import CHROMA_DIR, COLLECTION_NAME
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        client.get_collection(name=COLLECTION_NAME)
        logger.info("Warmup: ChromaDB ready")
    except Exception as e:
        logger.warning("Warmup: ChromaDB not ready: %s", e)
    try:
        from ollama import Client
        from src.config import OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS
        ollama = Client(timeout=min(10, OLLAMA_TIMEOUT_SECONDS))
        ollama.chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": "."}])
        logger.info("Warmup: Ollama model loaded")
    except Exception as e:
        logger.warning("Warmup: Ollama not ready (first request may be slow): %s", e)


# --- App ---
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Run warmup in a thread so the server starts quickly; models load in background.
    import asyncio
    asyncio.create_task(asyncio.to_thread(_warmup_blocking))
    yield


app = FastAPI(
    title="221B Baker Street API",
    description="RAG-powered Sherlock Holmes character chat and case stories",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

logger = get_request_logger()


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@app.get("/health")
async def health():
    """Health check for deployment probes."""
    return {"status": "ok"}


@app.post("/api/six-case-story", response_model=SixCaseStoryResponse)
async def api_six_case_story(req: SixCaseStoryRequest, request: Request):
    """Generate a case story episode featuring all six characters."""
    log_request(
        logger,
        session_id=req.session_id,
        user_input=req.case_prompt,
        ip=_client_ip(request),
        extra_fields={"mode": "six_case_story"},
    )
    try:
        result = six_character_case_story(
            case_prompt=req.case_prompt,
            session_id=req.session_id,
            strictness=req.strictness,
        )
        return SixCaseStoryResponse(
            story=result["story"],
            characters=result["characters"],
            sources=result["sources"],
            mode=result["mode"],
            setting=result["setting"],
        )
    except Exception as e:
        logger.exception("six_case_story failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/six-chatroom", response_model=SixChatroomResponse)
async def api_six_chatroom(req: SixChatroomRequest, request: Request):
    """Generate a chatroom turn with all six characters responding."""
    log_request(
        logger,
        session_id=req.session_id,
        user_input=req.question,
        ip=_client_ip(request),
        extra_fields={"mode": "six_chatroom"},
    )
    try:
        result = six_character_chatroom_turn(
            question=req.question,
            session_id=req.session_id,
            strictness=req.strictness,
        )
        return SixChatroomResponse(
            scene=result["scene"],
            characters=result["characters"],
            sources=result["sources"],
            mode=result["mode"],
            setting=result["setting"],
        )
    except Exception as e:
        logger.exception("six_chatroom failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/character-chat", response_model=CharacterChatResponse)
async def api_character_chat(req: CharacterChatRequest, request: Request):
    """Get an in-character reply from a single character (Sherlock, Watson, etc.)."""
    log_request(
        logger,
        session_id=req.session_id,
        user_input=req.question,
        ip=_client_ip(request),
        extra_fields={"mode": "character_chat", "character_key": req.character_key},
    )
    try:
        result = character_chat_turn(
            character_key=req.character_key,
            question=req.question,
            session_id=req.session_id,
            strictness=req.strictness,
        )
        return CharacterChatResponse(
            reply=result["reply"],
            character=result["character"],
            sources=result["sources"],
            mode=result["mode"],
            strictness=result["strictness"],
        )
    except Exception as e:
        logger.exception("character_chat failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


def main() -> None:
    import uvicorn

    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("APP_ENV", "development") == "development",
    )


if __name__ == "__main__":
    main()
