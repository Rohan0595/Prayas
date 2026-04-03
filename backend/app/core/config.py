"""
Core configuration — reads from environment variables.
All secrets live in .env; never hardcode them here.
"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM provider keys (LiteLLM uses these automatically)
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # App
    SECRET_KEY: str = "change-me-in-production"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    MAX_UPLOAD_SIZE_MB: int = 10

    # Database (Supabase)
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # RAG / Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    FAISS_INDEX_PATH: str = "./faiss_index"
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    TOP_K_RESULTS: int = 4

    # Model routing (LiteLLM format: provider/model-name)
    MODEL_CODING: str = "groq/llama-3.3-70b-versatile"
    MODEL_REASONING: str = "gemini/gemini-1.5-pro"
    MODEL_DEFAULT: str = "groq/llama-3.1-8b-instant"
    MODEL_FAST: str = "groq/llama-3.1-8b-instant"

    # Agent
    MAX_AGENT_ITERATIONS: int = 5
    AGENT_TIMEOUT_SECONDS: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


# ─── Model routing logic ───────────────────────────────────────────────────────

CODING_KEYWORDS = [
    "code", "function", "debug", "python", "javascript", "typescript",
    "sql", "html", "css", "react", "fastapi", "algorithm", "fix this",
    "write a script", "implement", "refactor", "class", "error:",
]

REASONING_KEYWORDS = [
    "explain", "analyze", "compare", "evaluate", "strategy", "philosophy",
    "ethics", "why does", "prove", "hypothesis", "research", "theory",
    "deep dive", "step by step reasoning", "complex", "nuanced",
]


def route_model(user_message: str, preferred_model: str | None = None) -> str:
    """
    Select the best model based on the query content.
    If the user explicitly picks a model, honor that choice.
    """
    if preferred_model:
        return preferred_model

    msg_lower = user_message.lower()

    if any(kw in msg_lower for kw in CODING_KEYWORDS):
        return settings.MODEL_CODING

    if any(kw in msg_lower for kw in REASONING_KEYWORDS):
        if "gemini" in settings.MODEL_REASONING.lower() and (not settings.GEMINI_API_KEY or "your-gemini-api-key" in settings.GEMINI_API_KEY):
            return settings.MODEL_CODING
        return settings.MODEL_REASONING

    return settings.MODEL_DEFAULT
