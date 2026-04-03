"""
FastAPI dependencies — JWT authentication via Supabase.
"""
from fastapi import HTTPException, Header
from supabase import create_client
from app.core.config import settings


async def get_current_user(authorization: str = Header(None)):
    """
    Validate a Bearer token from the Authorization header.
    Returns the Supabase user object on success, raises 401 otherwise.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing or malformed",
        )

    token = authorization.split(" ", 1)[1]
    try:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        response = client.auth.get_user(token)
        if not response or not response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return response.user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
