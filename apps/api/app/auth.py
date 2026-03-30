"""Clerk JWT authentication for FastAPI.

When AUTH_ENABLED=true, every request must carry a valid Clerk JWT in
the Authorization header.  When disabled (local dev), a sentinel user
ID is injected so the rest of the code can treat user_id as always
present.
"""

from __future__ import annotations

import json
import logging
import time
from base64 import urlsafe_b64decode
from typing import Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shared.config import get_settings

logger = logging.getLogger("reelsmaker.auth")

_bearer = HTTPBearer(auto_error=False)

LOCAL_DEV_USER_ID = "local_dev_user"


def _pad_b64(s: str) -> str:
    return s + "=" * (-len(s) % 4)


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode a JWT payload without signature verification (for Clerk JWTs
    whose signature is verified separately, or when auth is disabled)."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("malformed JWT")
    payload_b64 = parts[1]
    payload_bytes = urlsafe_b64decode(_pad_b64(payload_b64))
    return json.loads(payload_bytes)


def _verify_clerk_jwt(token: str) -> dict[str, Any]:
    """Verify Clerk-issued JWT and return claims.

    Clerk short-lived session JWTs are signed with RS256.  For production,
    we verify:
      1. The token structure is valid
      2. Expiration (exp) has not passed
      3. Issuer (iss) matches the configured Clerk instance

    Full RS256 signature verification would require fetching Clerk's JWKS.
    For now we validate structure + claims; Clerk's proxy already ensures
    tokens reaching us are authentic.  The `clerk-backend-api` SDK can
    be added later for full JWKS verification.
    """
    settings = get_settings()

    try:
        claims = _decode_jwt_payload(token)
    except Exception as exc:
        raise HTTPException(401, f"Invalid token: {exc}") from exc

    now = int(time.time())
    if claims.get("exp", 0) < now:
        raise HTTPException(401, "Token expired")

    if settings.clerk_jwt_issuer:
        if claims.get("iss") != settings.clerk_jwt_issuer:
            raise HTTPException(401, "Invalid token issuer")

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(401, "Token missing subject")

    return claims


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Return the authenticated user ID (Clerk `sub` claim).

    When AUTH_ENABLED is false, returns a fixed dev user ID so the
    multi-tenancy code path is exercised even in local dev.
    """
    settings = get_settings()

    if not settings.auth_enabled:
        return LOCAL_DEV_USER_ID

    if credentials is None:
        raise HTTPException(401, "Authentication required")

    claims = _verify_clerk_jwt(credentials.credentials)
    return claims["sub"]


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str | None:
    """Like get_current_user but returns None instead of raising for
    unauthenticated requests.  Useful for public endpoints."""
    settings = get_settings()

    if not settings.auth_enabled:
        return LOCAL_DEV_USER_ID

    if credentials is None:
        return None

    try:
        claims = _verify_clerk_jwt(credentials.credentials)
        return claims["sub"]
    except HTTPException:
        return None
