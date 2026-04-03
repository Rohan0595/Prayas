"""
Prayāsa - FastAPI Backend
Entry point for the application
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, upload, sessions, auth
from app.core.config import settings
from app.rag.vector_store import vector_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup, clean up on shutdown."""
    # Initialize FAISS vector store
    vector_store.initialize()
    print("✅ Vector store initialized")
    yield
    print("🛑 Shutting down Prayāsa")


app = FastAPI(
    title="Prayāsa API",
    description="Multi-model AI assistant with RAG and agent capabilities",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server and production origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(auth.router, prefix="/api", tags=["auth"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
