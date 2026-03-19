"""
auth.py — Microsoft SSO via MSAL authorization code flow.

Uses ConfidentialClientApplication (same Azure app as frAInk's Outlook integration).
Sessions are signed cookies via itsdangerous — no DB required.
"""

import os
import json
import secrets
import msal
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CLIENT_ID     = os.getenv("MS_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET", "")
TENANT_ID     = os.getenv("MS_TENANT_ID", "")
AUTHORITY     = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES        = ["User.Read"]

# Site URL determines the redirect URI — set SITE_URL in env.
# Local: http://localhost:8000   |   Prod: https://letmebefraink.com
SITE_URL       = os.getenv("SITE_URL", "http://localhost:8000").rstrip("/")
REDIRECT_URI   = f"{SITE_URL}/auth/callback"

# Only this email may access the admin area.
ALLOWED_EMAIL  = os.getenv("ALLOWED_EMAIL", "frank@letmebefraink.com").lower()

# Secret for signing session cookies.  Set AUTH_SECRET_KEY in env.
AUTH_SECRET    = os.getenv("AUTH_SECRET_KEY", "change-me-in-production")
SESSION_MAX_AGE = 60 * 60 * 8  # 8 hours

_serializer = URLSafeTimedSerializer(AUTH_SECRET)

# ---------------------------------------------------------------------------
# MSAL helpers
# ---------------------------------------------------------------------------

def _msal_app() -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=AUTHORITY,
    )


def build_auth_url() -> tuple[str, str]:
    """Return (auth_url, state).  state is stored in a short-lived cookie for CSRF."""
    state = secrets.token_urlsafe(16)
    url = _msal_app().get_authorization_request_url(
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI,
    )
    return url, state


def exchange_code(code: str, redirect_uri: str) -> dict | None:
    """Exchange auth code for token; return user info dict or None on failure."""
    result = _msal_app().acquire_token_by_authorization_code(
        code=code,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    if "error" in result:
        return None

    # id_token_claims contains the user's identity
    claims = result.get("id_token_claims", {})
    email = (claims.get("preferred_username") or claims.get("email") or "").lower()
    name  = claims.get("name") or email
    return {"email": email, "name": name}

# ---------------------------------------------------------------------------
# Session cookie helpers
# ---------------------------------------------------------------------------

SESSION_COOKIE = "fraink_session"


def create_session_cookie(user: dict) -> str:
    """Return a signed, serialized session string."""
    return _serializer.dumps(user)


def decode_session_cookie(value: str) -> dict | None:
    """Decode and verify session cookie.  Returns user dict or None."""
    try:
        return _serializer.loads(value, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None

# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_current_user(request: Request) -> dict | None:
    """Return user dict if authenticated, else None."""
    value = request.cookies.get(SESSION_COOKIE)
    if not value:
        return None
    return decode_session_cookie(value)


def require_auth(request: Request) -> dict:
    """Dependency that enforces authentication.  Redirects to /login on failure."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return user
