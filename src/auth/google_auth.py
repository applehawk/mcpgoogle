from __future__ import annotations
import os, pathlib
from typing import Sequence
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

CREDS_PATH = pathlib.Path(os.getenv("GOOGLE_CREDENTIALS_PATH", "secrets/credentials.google.json"))
TOKEN_PATH = pathlib.Path(os.getenv("GOOGLE_TOKEN_PATH", "data/token.google.json"))

_DEFAULT_SCOPES: Sequence[str] = [
    # Cobertura base para Gmail y Drive en el hub.
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
]

def _resolve_scopes() -> Sequence[str]:
    raw = os.getenv("GOOGLE_SCOPES")
    if raw:
        scopes = [s for s in raw.split() if s]
        if scopes:
            return scopes
    return _DEFAULT_SCOPES

SCOPES: Sequence[str] = _resolve_scopes()

def get_google_creds() -> Credentials:
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
                    f"No encuentro tu credentials.json en {CREDS_PATH}. Descargalo de Google Cloud Console (OAuth Client)."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)  # abre navegador para login
        TOKEN_PATH.write_text(creds.to_json())
    return creds
