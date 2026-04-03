"""
Authentication API — register/login via Supabase Auth.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client
from app.core.config import settings

router = APIRouter()


class AuthRequest(BaseModel):
    email: str
    password: str


@router.post("/auth/register")
async def register(req: AuthRequest):
    """Register a new user with Supabase Auth."""
    try:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        res = client.auth.sign_up({"email": req.email, "password": req.password})
        if res.user:
            return {
                "message": "Registered successfully. You can now log in.",
                "user_id": res.user.id,
                "email": res.user.email,
            }
        raise HTTPException(status_code=400, detail="Registration failed")
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "already registered" in msg.lower() or "already exists" in msg.lower():
            raise HTTPException(status_code=409, detail="Email already registered")
        raise HTTPException(status_code=400, detail=msg)


@router.post("/auth/login")
async def login(req: AuthRequest):
    """Login and return a JWT access token."""
    try:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        res = client.auth.sign_in_with_password({"email": req.email, "password": req.password})
        if res.session and res.user:
            return {
                "access_token": res.session.access_token,
                "user_id": res.user.id,
                "email": res.user.email,
            }
        raise HTTPException(status_code=401, detail="Invalid email or password")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password")


@router.post("/auth/logout")
async def logout():
    """Logout — client clears its token."""
    return {"message": "Logged out successfully"}
