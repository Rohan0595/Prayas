"""
Chat memory — Supabase-backed session storage.
Each session holds an ordered list of messages (role + content).
Tables must be created in the Supabase dashboard:

    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        title TEXT,
        user_id TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS messages (
        id BIGSERIAL PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        model TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
"""
from datetime import datetime, timezone
from typing import List, Dict, Optional
from supabase import create_client, Client
from app.core.config import settings


def _get_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


# ── sessions ──────────────────────────────────────────────────────────────────

def create_session(session_id: str, title: str = "New Chat", user_id: str = "") -> Dict:
    """Create a new chat session."""
    now = datetime.now(timezone.utc).isoformat()
    client = _get_client()
    data = {
        "id": session_id,
        "title": title,
        "user_id": user_id,
        "created_at": now,
        "updated_at": now,
    }
    client.table("sessions").upsert(data).execute()
    return data


def get_session(session_id: str) -> Optional[Dict]:
    client = _get_client()
    res = (
        client.table("sessions")
        .select("*")
        .eq("id", session_id)
        .limit(1)
        .execute()
    )
    rows = res.data if res and res.data else []
    return rows[0] if rows else None


def list_sessions(user_id: str = "") -> List[Dict]:
    client = _get_client()
    query = (
        client.table("sessions")
        .select("*")
        .order("updated_at", desc=True)
        .limit(50)
    )
    if user_id:
        query = query.eq("user_id", user_id)
    res = query.execute()
    return res.data or []


def delete_session(session_id: str):
    client = _get_client()
    # messages will cascade-delete due to FK ON DELETE CASCADE
    client.table("sessions").delete().eq("id", session_id).execute()


def update_session_title(session_id: str, title: str):
    client = _get_client()
    client.table("sessions").update({"title": title}).eq("id", session_id).execute()


# ── messages ───────────────────────────────────────────────────────────────────

def add_message(session_id: str, role: str, content: str, model: str = "") -> int:
    """Append a message to a session and bump updated_at on the session."""
    now = datetime.now(timezone.utc).isoformat()
    client = _get_client()
    res = (
        client.table("messages")
        .insert({
            "session_id": session_id,
            "role": role,
            "content": content,
            "model": model,
            "created_at": now,
        })
        .execute()
    )
    # Bump session updated_at
    client.table("sessions").update({"updated_at": now}).eq("id", session_id).execute()
    # Return the new message id
    return res.data[0]["id"] if res.data else -1


def get_messages(session_id: str, limit: int = 40) -> List[Dict[str, str]]:
    """Return the last `limit` messages formatted for the LLM API (oldest-first)."""
    client = _get_client()
    res = (
        client.table("messages")
        .select("role, content")
        .eq("session_id", session_id)
        .order("id", desc=True)
        .limit(limit)
        .execute()
    )
    rows = res.data or []
    # Reverse so oldest messages come first
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


# ── legacy stub (safe to call, no-ops) ────────────────────────────────────────

def init_db():
    """No-op: tables are managed in Supabase dashboard, not here."""
    pass
