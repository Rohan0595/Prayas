"""
Sessions API — CRUD for chat sessions.
"""
import uuid
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.memory.store import (
    list_sessions, get_session, create_session,
    delete_session, get_messages
)
from app.core.deps import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])



class SessionOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


@router.get("/sessions", response_model=List[dict])
async def get_sessions(user = Depends(get_current_user)):
    return list_sessions(user_id=user.id)


@router.post("/sessions")
async def new_session(user = Depends(get_current_user)):
    session_id = str(uuid.uuid4())
    session = create_session(session_id, user_id=user.id)
    return session


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, user = Depends(get_current_user)):
    session = get_session(session_id)
    if not session or session.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = get_messages(session_id, limit=200)
    return {"session": session, "messages": messages}


@router.delete("/sessions/{session_id}")
async def remove_session(session_id: str, user = Depends(get_current_user)):
    session = get_session(session_id)
    if not session or session.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    delete_session(session_id)
    return {"deleted": session_id}
