"""
Configuration module for MCP Google Hub with OMA Backend integration

This module provides configuration for:
- OMA Backend connection (OAuth Management & Authentication)
- Google API scopes
- Authentication mode selection (legacy file-based or OMA backend)
"""

from __future__ import annotations
import os
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# Authentication Mode
# ============================================================================

AuthMode = Literal["oma_backend", "local_file"]

# Choose authentication mode:
# - "oma_backend": Use OMA Backend for centralized OAuth management (recommended)
# - "local_file": Use local credentials.json and token.json files (legacy)
AUTH_MODE: AuthMode = os.getenv("AUTH_MODE", "oma_backend")  # type: ignore


# ============================================================================
# OMA Backend Configuration (for server-to-server OAuth)
# ============================================================================

# OMA Backend base URL
OMA_BACKEND_URL = os.getenv("OMA_BACKEND_URL", "https://rndaibot.ru/apib/v1")

# User's access token for OMA backend authentication
# This token should be obtained by logging in to the OMA backend
OMA_ACCESS_TOKEN = os.getenv("OMA_ACCESS_TOKEN")

# SSL verification (set to False for development with self-signed certificates)
OMA_VERIFY_SSL = os.getenv("OMA_VERIFY_SSL", "true").lower() == "true"


# ============================================================================
# Legacy Local File Authentication Configuration
# ============================================================================

# Path to Google OAuth credentials file (from Google Cloud Console)
GOOGLE_CREDENTIALS_PATH = os.getenv(
    "GOOGLE_CREDENTIALS_PATH",
    "secrets/credentials.google.json"
)

# Path to store OAuth token after authentication
GOOGLE_TOKEN_PATH = os.getenv(
    "GOOGLE_TOKEN_PATH",
    "data/token.google.json"
)


# ============================================================================
# Google API Configuration
# ============================================================================

# Google OAuth Client ID and Secret (required for OMA backend mode)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Google API Scopes
# Default scopes for Gmail, Calendar, and Drive access
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]

# You can override scopes via GOOGLE_SCOPES environment variable (space-separated)
def get_google_scopes() -> list[str]:
    """Get Google API scopes from environment or use defaults"""
    raw = os.getenv("GOOGLE_SCOPES")
    if raw:
        scopes = [s.strip() for s in raw.split() if s.strip()]
        if scopes:
            return scopes
    return DEFAULT_SCOPES


GOOGLE_SCOPES = get_google_scopes()


# ============================================================================
# Validation
# ============================================================================

def validate_config() -> None:
    """Validate configuration based on selected auth mode"""
    if AUTH_MODE == "oma_backend":
        if not OMA_ACCESS_TOKEN:
            raise ValueError(
                "OMA_ACCESS_TOKEN environment variable is required when AUTH_MODE=oma_backend. "
                "Please login to OMA backend and set your access token."
            )
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            raise ValueError(
                "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required for OMA backend mode. "
                "These should match the credentials configured in OMA backend."
            )
    elif AUTH_MODE == "local_file":
        import pathlib
        creds_path = pathlib.Path(GOOGLE_CREDENTIALS_PATH)
        if not creds_path.exists():
            raise FileNotFoundError(
                f"Google credentials file not found at {GOOGLE_CREDENTIALS_PATH}. "
                f"Download it from Google Cloud Console (OAuth 2.0 Client ID)."
            )
    else:
        raise ValueError(
            f"Invalid AUTH_MODE: {AUTH_MODE}. Must be 'oma_backend' or 'local_file'."
        )


# ============================================================================
# Helper Functions
# ============================================================================

def get_auth_mode() -> AuthMode:
    """Get current authentication mode"""
    return AUTH_MODE


def is_oma_backend_mode() -> bool:
    """Check if using OMA backend authentication"""
    return AUTH_MODE == "oma_backend"


def is_local_file_mode() -> bool:
    """Check if using local file authentication"""
    return AUTH_MODE == "local_file"
