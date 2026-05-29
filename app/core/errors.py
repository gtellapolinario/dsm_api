"""Shared exceptions and API dependencies."""

from app.core.security import DsmValidationError, require_admin_token

__all__ = ["DsmValidationError", "require_admin_token"]
