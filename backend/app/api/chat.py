"""
Chat API — main endpoint.
Supports streaming (SSE) and agent mode.
"""
import uuid
import json
import asyncio
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import settings, route_model
from app.core.deps import get_current_user
from fastapi import Depends
from app.models.openrouter import openrouter_client, OpenRouterError
from app.memory.store import (
    add_message, get_messages, create_session, get_session, update_session_title
)
from app.rag.vector_store import get_user_store
from app.tools.agent import run_agent

router = APIRouter()

SYSTEM_PROMPT = """You are Prayāsa, a helpful, knowledgeable, and concise AI assistant.
You have access to tools (calculator, web search, clock) and can reference uploaded documents.
When using retrieved document context, cite the source.
Be direct and accurate. If you don't know something, say so."""


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    model: Optional[str] = None       # user-selected model override
    use_agent: bool = False            # enable tool-use agent loop
    use_rag: bool = True               # include document context


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    model_used: str


# ─── Streaming endpoint ────────────────────────────────────────────────────────

@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, user = Depends(get_current_user)):
    """
    SSE streaming endpoint.
    Returns text/event-stream chunks for real-time display.
    """
    session_id = req.session_id or str(uuid.uuid4())

    # Ensure session exists
    if not get_session(session_id):
        create_session(session_id, user_id=user.id)

    # Select model
    model = route_model(req.message, req.model)

    # Build context messages
    history = get_messages(session_id)
    rag_context = ""
    user_store = get_user_store(user.id)
    if req.use_rag and user_store.document_count > 0:
        rag_context = user_store.get_context_for_query(req.message)

    system = SYSTEM_PROMPT
    if rag_context:
        system += f"\n\n{rag_context}"

    messages = [{"role": "system", "content": system}] + history + [
        {"role": "user", "content": req.message}
    ]

    # Persist user message
    add_message(session_id, "user", req.message)

    # Auto-title session from first user message
    if len(history) == 0:
        title = req.message[:60] + ("…" if len(req.message) > 60 else "")
        update_session_title(session_id, title)

    async def event_generator():
        full_reply = []
        # Yield session_id and model first so the client knows them
        meta = json.dumps({"session_id": session_id, "model": model})
        yield f"data: {json.dumps({'type': 'meta', 'payload': meta})}\n\n"

        try:
            async for chunk in openrouter_client.stream_chat_completion(
                model=model,
                messages=messages,
            ):
                full_reply.append(chunk)
                yield f"data: {json.dumps({'type': 'chunk', 'payload': chunk})}\n\n"
        except OpenRouterError as e:
            yield f"data: {json.dumps({'type': 'error', 'payload': str(e)})}\n\n"
            return

        # Persist assistant response
        reply_text = "".join(full_reply)
        add_message(session_id, "assistant", reply_text, model)
        yield f"data: {json.dumps({'type': 'done', 'payload': ''})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Agent (non-streaming) endpoint ───────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, user = Depends(get_current_user)):
    """
    Non-streaming endpoint with optional agent loop.
    Used when streaming is not needed or agent mode is enabled.
    """
    session_id = req.session_id or str(uuid.uuid4())
    if not get_session(session_id):
        create_session(session_id, user_id=user.id)

    model = route_model(req.message, req.model)
    history = get_messages(session_id)

    rag_context = ""
    user_store = get_user_store(user.id)
    if req.use_rag and user_store.document_count > 0:
        rag_context = user_store.get_context_for_query(req.message)

    system = SYSTEM_PROMPT
    if rag_context:
        system += f"\n\n{rag_context}"

    messages_for_llm = history + [{"role": "user", "content": req.message}]
    add_message(session_id, "user", req.message)

    if len(history) == 0:
        update_session_title(session_id, req.message[:60])

    try:
        if req.use_agent:
            reply = await run_agent(messages_for_llm, model, system)
        else:
            response = await openrouter_client.chat_completion(
                model=model,
                messages=[{"role": "system", "content": system}] + messages_for_llm,
            )
            reply = response["choices"][0]["message"]["content"]
    except OpenRouterError as e:
        raise HTTPException(status_code=502, detail=str(e))

    add_message(session_id, "assistant", reply, model)

    return ChatResponse(reply=reply, session_id=session_id, model_used=model)
