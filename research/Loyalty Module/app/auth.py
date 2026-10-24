"""
Authentication, RBAC and tenant resolution.

Every request is resolved to a Principal(organization_id, role). Handlers must
scope ALL data access to principal.organization_id — the client never tells
the server which tenant it is.

Credentials accepted:
  * X-Api-Key: <key>            long-lived, server-to-server (stored hashed)
  * Authorization: Bearer <jwt> short-lived token minted via POST /auth/token
                                (client-credentials style exchange of an API key)

The JWT is only a transport: the database row of the API key it names stays
authoritative for org + role, so revoking a key or changing its role takes
effect immediately, even for tokens already issued.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select

from . import config, models
from .database import SessionLocal

KEY_PREFIX = "gos_"

ROLE_RANK = {models.Role.VIEWER: 0, models.Role.OPERATOR: 1, models.Role.ADMIN: 2}


@dataclass(frozen=True)
class Principal:
    organization_id: str
    role: models.Role
    key_id: str
    auth_method: str  # "api_key" | "jwt"


def generate_api_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def _principal_for(where_clause, method: str) -> Principal | None:
    # Own short-lived session: keeps the request's main session free of an
    # auto-begun transaction so services can open their own `db.begin()`.
    with SessionLocal() as s:
        key = s.execute(
            select(models.ApiKey).where(where_clause, models.ApiKey.is_active.is_(True))
        ).scalar_one_or_none()
        if key is None:
            return None
        return Principal(key.organization_id, key.role, key.key_id, method)


def principal_from_api_key(x_api_key: str | None = Header(default=None)) -> Principal:
    if not x_api_key:
        raise _unauthorized("Missing credentials: send X-Api-Key")
    principal = _principal_for(models.ApiKey.key_hash == hash_api_key(x_api_key), "api_key")
    if principal is None:
        raise _unauthorized("Invalid or revoked API key")
    return principal


def get_principal(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> Principal:
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise _unauthorized("Malformed Authorization header")
        try:
            claims = jwt.decode(
                token,
                config.JWT_SECRET,
                algorithms=[config.JWT_ALGORITHM],
                issuer=config.JWT_ISSUER,
                options={"require": ["exp", "iat", "sub", "iss"]},
            )
        except jwt.PyJWTError:
            raise _unauthorized("Invalid or expired token")
        principal = _principal_for(models.ApiKey.key_id == claims["sub"], "jwt")
        if principal is None:
            raise _unauthorized("Token's API key is revoked or unknown")
        return principal
    return principal_from_api_key(x_api_key)


def require_role(minimum: models.Role):
    def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if ROLE_RANK[principal.role] < ROLE_RANK[minimum]:
            raise HTTPException(status_code=403, detail=f"This action requires the {minimum.value} role or higher")
        return principal

    return dependency


def issue_token(principal: Principal) -> tuple[str, int]:
    now = int(time.time())
    payload = {
        "iss": config.JWT_ISSUER,
        "sub": principal.key_id,
        "org": principal.organization_id,
        "role": principal.role.value,
        "iat": now,
        "exp": now + config.JWT_TTL_SECONDS,
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM), config.JWT_TTL_SECONDS


def require_platform_admin(x_platform_key: str | None = Header(default=None)) -> None:
    """Gate for tenant creation. Entirely separate from tenant API keys."""
    if not config.PLATFORM_ADMIN_KEY:
        raise HTTPException(403, "Platform administration is not enabled on this server")
    if not x_platform_key or not hmac.compare_digest(
        x_platform_key.encode(), config.PLATFORM_ADMIN_KEY.encode()
    ):
        raise HTTPException(401, "Invalid platform key")
