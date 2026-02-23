"""Configuration for 221B Baker Street RAG."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Paths
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
CHROMA_DIR = ROOT / "chroma_db"
COLLECTION_NAME = "sherlock_holmes"

# LLM (local via Ollama - no API key needed)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# Chunking
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64

# Retrieval
TOP_K = 5
CHAT_TOP_K = 8  # more context for comprehensive answers
