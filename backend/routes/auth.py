"""
Google OAuth 2.0 — works for both local dev and cloud deployment.

Redirect URI and frontend URL are derived from the APP_URL environment variable:
  Local dev  (no APP_URL): redirect URI = http://localhost:8000/auth/callback
                            after-auth   = http://localhost:5173/?auth=success
  Production (APP_URL set): redirect URI = https://your-app.railway.app/auth/callback
                             after-auth   = https://your-app.railway.app/?auth=success

Token persistence on cloud:
  1. First deploy: complete OAuth → visit /auth/token-export → copy value →
     set GOOGLE_TOKEN_JSON env var in Railway → redeploy.
  2. On every cold start the token is restored from that env var automatically.
"""

import base64
import os
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse, RedirectResponse
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

router = APIRouter(prefix="/auth", tags=["auth"])

TOKEN_PATH = Path(__file__).parent.parent / "token.json"

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
]


# ── Token persistence helpers ─────────────────────────────────────────────────

def _restore_token_from_env() -> None:
    """On cold start, unpack GOOGLE_TOKEN_JSON (base64) into token.json."""
    b64 = os.getenv("GOOGLE_TOKEN_JSON", "").strip()
    if b64 and not TOKEN_PATH.exists():
        try:
            TOKEN_PATH.write_bytes(base64.b64decode(b64))
            print("[auth] Google token restored from GOOGLE_TOKEN_JSON env var.")
        except Exception as exc:
            print(f"[auth] Warning: could not restore token from env: {exc}")


# Run once at import time so every worker process restores the token immediately
_restore_token_from_env()


def load_credentials() -> Credentials | None:
    """Return valid (possibly auto-refreshed) credentials, or None."""
    if not TOKEN_PATH.exists():
        return None
    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    except Exception:
        return None
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(GoogleRequest())
            _save_credentials(creds)
        except Exception:
            return None
    return creds if creds.valid else None


def _save_credentials(creds: Credentials) -> None:
    TOKEN_PATH.write_text(creds.to_json())


# ── URL helpers ───────────────────────────────────────────────────────────────

def _redirect_uri() -> str:
    base = os.getenv("APP_URL", "http://localhost:8000").rstrip("/")
    return f"{base}/auth/callback"


def _after_auth_url(success: bool, reason: str = "") -> str:
    # In prod (APP_URL set), frontend is served from the same server.
    # In dev (no APP_URL), frontend is Vite on :5173.
    if os.getenv("APP_URL"):
        base = os.getenv("APP_URL").rstrip("/")
    else:
        base = "http://localhost:5173"
    if success:
        return f"{base}/?auth=success"
    return f"{base}/?auth=error&reason={reason}"


# ── OAuth flow ────────────────────────────────────────────────────────────────

def _make_flow() -> Flow:
    redirect = _redirect_uri()
    client_config = {
        "installed": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "redirect_uris": [redirect],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/login")
async def login():
    if not os.getenv("GOOGLE_CLIENT_ID"):
        return JSONResponse({"error": "GOOGLE_CLIENT_ID not configured on the server."}, status_code=500)
    flow = _make_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return {"auth_url": auth_url}


@router.get("/callback")
async def callback(code: str = "", error: str = ""):
    if error:
        return RedirectResponse(_after_auth_url(False, error))
    if not code:
        return RedirectResponse(_after_auth_url(False, "no_code"))
    flow = _make_flow()
    flow.fetch_token(code=code)
    _save_credentials(flow.credentials)
    return RedirectResponse(_after_auth_url(True))


@router.get("/status")
async def status():
    creds = load_credentials()
    if creds:
        email = None
        if hasattr(creds, "id_token") and isinstance(creds.id_token, dict):
            email = creds.id_token.get("email")
        return {"authenticated": True, "email": email}
    return {"authenticated": False, "email": None}


@router.post("/logout")
async def logout():
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
    return {"success": True}


@router.get("/token-export")
async def token_export():
    """
    Return the current token as a base64 string.
    Copy the value and set it as the GOOGLE_TOKEN_JSON environment variable
    in your cloud platform so the token survives container restarts.
    """
    if not TOKEN_PATH.exists():
        return JSONResponse(
            {"error": "No token stored yet — complete the OAuth flow first."},
            status_code=404,
        )
    b64 = base64.b64encode(TOKEN_PATH.read_bytes()).decode()
    return {
        "variable_name": "GOOGLE_TOKEN_JSON",
        "value": b64,
        "instructions": (
            "1. Copy the 'value' string above.\n"
            "2. In Railway → your service → Variables → add GOOGLE_TOKEN_JSON = <value>.\n"
            "3. Railway will redeploy; from now on the token is restored on every cold start."
        ),
    }
