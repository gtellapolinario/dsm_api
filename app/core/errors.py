"""Shared exceptions and API dependencies."""
from fastapi import Header, HTTPException, status

from app.core.config import get_settings


class DsmValidationError(ValueError):
    """Raised when DSM source data fails deterministic validation."""


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")
