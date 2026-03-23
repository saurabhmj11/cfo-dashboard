"""
Settings Router - Manage runtime configuration like API keys.
Keys are stored in the .env file and applied at runtime without restarting.
"""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.dependencies import get_current_user
from app.models.db_models import User

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

ENV_PATH = Path(__file__).parent.parent.parent / ".env"


def read_env() -> dict:
    """Read the .env file into a dict."""
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def write_env(env: dict):
    """Write a dict back to the .env file."""
    lines = [f"{k}={v}" for k, v in env.items()]
    ENV_PATH.write_text("\n".join(lines) + "\n")


class ApiKeyUpdate(BaseModel):
    gemini_api_key: str


class SettingsResponse(BaseModel):
    gemini_api_key_set: bool
    gemini_api_key_preview: Optional[str] = None      # e.g. "AIza...XYZ" (masked)


@router.get("", response_model=SettingsResponse)
async def get_settings(current_user: User = Depends(get_current_user)):
    """Return current settings status (never return the raw key)."""
    env = read_env()
    key = env.get("GEMINI_API_KEY", "")
    is_set = bool(key) and key != "your_gemini_key_here"
    preview = None
    if is_set and len(key) > 8:
        preview = key[:6] + "..." + key[-4:]
    return SettingsResponse(gemini_api_key_set=is_set, gemini_api_key_preview=preview)


@router.post("", response_model=SettingsResponse)
async def update_settings(
    payload: ApiKeyUpdate,
    current_user: User = Depends(get_current_user)
):
    """Save the Gemini API key to .env and apply it to the current process."""
    if not payload.gemini_api_key.strip():
        raise HTTPException(status_code=400, detail="API key cannot be empty.")

    env = read_env()
    env["GEMINI_API_KEY"] = payload.gemini_api_key.strip()
    write_env(env)

    # Apply to running process immediately (no restart needed)
    os.environ["GEMINI_API_KEY"] = payload.gemini_api_key.strip()

    key = payload.gemini_api_key.strip()
    preview = key[:6] + "..." + key[-4:] if len(key) > 8 else "****"
    return SettingsResponse(gemini_api_key_set=True, gemini_api_key_preview=preview)


@router.delete("")
async def clear_settings(current_user: User = Depends(get_current_user)):
    """Clear the Gemini API key."""
    env = read_env()
    env["GEMINI_API_KEY"] = "your_gemini_key_here"
    write_env(env)
    os.environ.pop("GEMINI_API_KEY", None)
    return {"status": "cleared"}
