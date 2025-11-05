"""
Google Authentication Module with Multi-Mode Support

Supports two authentication modes:
1. OMA Backend (recommended): Centralized OAuth management via OMA backend server
2. Local File (legacy): Traditional file-based OAuth with local credentials.json

Mode is controlled by AUTH_MODE environment variable in config.py
"""

from __future__ import annotations
import pathlib
from typing import Sequence
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Import configuration
from src.config import (
    AUTH_MODE,
    GOOGLE_CREDENTIALS_PATH,
    GOOGLE_TOKEN_PATH,
    GOOGLE_SCOPES,
    is_oma_backend_mode,
    is_local_file_mode,
)

# Legacy paths for local file mode
CREDS_PATH = pathlib.Path(GOOGLE_CREDENTIALS_PATH)
TOKEN_PATH = pathlib.Path(GOOGLE_TOKEN_PATH)
SCOPES: Sequence[str] = GOOGLE_SCOPES


def get_google_creds() -> Credentials:
    """
    Get Google OAuth credentials using configured authentication mode

    Modes:
    - oma_backend: Fetch credentials from OMA backend (server-to-server)
    - local_file: Use local credentials.json and token.json (legacy)

    Returns:
        google.oauth2.credentials.Credentials object

    Raises:
        ValueError: If OMA backend is not configured or Google account not connected
        FileNotFoundError: If local credentials file not found (local_file mode)
    """
    if is_oma_backend_mode():
        return _get_google_creds_from_oma()
    elif is_local_file_mode():
        return _get_google_creds_from_local_file()
    else:
        raise ValueError(f"Unknown AUTH_MODE: {AUTH_MODE}")


def _get_google_creds_from_oma() -> Credentials:
    """
    Get credentials from OMA backend (server-to-server OAuth)

    This method contacts the OMA backend to retrieve Google OAuth credentials
    that were previously authorized by the user through the web interface.
    """
    from src.auth.oma_client import get_google_creds_from_oma

    try:
        return get_google_creds_from_oma()
    except ValueError as e:
        raise ValueError(
            f"Failed to get Google credentials from OMA backend: {e}\n\n"
            f"Please ensure:\n"
            f"1. OMA_ACCESS_TOKEN is set in your .env file\n"
            f"2. User has connected their Google account via the web interface\n"
            f"3. OMA backend is running and accessible"
        ) from e


def _get_google_creds_from_local_file() -> Credentials:
    """
    Get credentials from local file (legacy mode)

    This is the original authentication flow using local credentials.json
    and token.json files. Interactive browser-based OAuth flow.
    """
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    creds: Credentials | None = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_PATH.exists():
                raise FileNotFoundError(
                    f"Google credentials file not found at {CREDS_PATH}. "
                    f"Download it from Google Cloud Console (OAuth 2.0 Client ID)."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)  # Opens browser for OAuth
        TOKEN_PATH.write_text(creds.to_json())

    return creds
