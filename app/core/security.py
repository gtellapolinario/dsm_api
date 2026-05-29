"""Security helpers: admin auth, path hardening and lightweight rate limiting."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import Header, HTTPException, Request, status

from app.core.config import get_settings


class DsmValidationError(ValueError):
    """Raised when DSM source data fails deterministic validation."""


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


def resolve_safe_path(raw_path: str, *, must_be_under_release_root: bool = True) -> Path:
    """Resolve a user supplied path while rejecting traversal and unsafe production paths."""
    settings = get_settings()
    candidate = Path(raw_path).expanduser()
    if ".." in candidate.parts:
        raise DsmValidationError(f"Path traversal is not allowed: {raw_path}")
    resolved = candidate.resolve()
    release_root = Path(settings.dsm_release_root).expanduser().resolve()
    if must_be_under_release_root or settings.app_env.lower() == "production":
        try:
            resolved.relative_to(release_root)
        except ValueError as exc:
            raise DsmValidationError(
                f"Path must be inside DSM_RELEASE_ROOT ({release_root}): {resolved}"
            ) from exc
    return resolved


_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def rate_limit_dependency(scope: str):
    async def dependency(request: Request) -> None:
        settings = get_settings()
        limit = settings.rate_limit_requests
        window = settings.rate_limit_window_seconds
        if limit <= 0:
            return
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        client = forwarded or (request.client.host if request.client else "unknown")
        key = f"{scope}:{client}"
        now = time.monotonic()
        bucket = _BUCKETS[key]
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded ({limit} requests/{window}s)",
            )
        bucket.append(now)

    return dependency
