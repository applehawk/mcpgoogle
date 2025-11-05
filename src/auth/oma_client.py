"""
OMA Backend Authentication Client for Server-to-Server OAuth 2.0

This module provides integration with the OMA (OAuth Management & Authentication) backend
to obtain Google OAuth credentials for server-to-server communication.
"""

from __future__ import annotations
import os
from typing import Optional
from datetime import datetime
import httpx
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials

load_dotenv()


class OMAAuthClient:
    """Client for authenticating with OMA backend and obtaining Google credentials"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        access_token: Optional[str] = None,
        verify_ssl: bool = True
    ):
        """
        Initialize OMA Authentication Client

        Args:
            base_url: OMA backend base URL (default from env OMA_BACKEND_URL)
            access_token: User's access token for OMA backend (default from env OMA_ACCESS_TOKEN)
            verify_ssl: Whether to verify SSL certificates (default True, set False for dev)
        """
        self.base_url = (base_url or os.getenv("OMA_BACKEND_URL", "https://rndaibot.ru/apib/v1")).rstrip("/")
        self.access_token = access_token or os.getenv("OMA_ACCESS_TOKEN")
        self.verify_ssl = verify_ssl

        if not self.access_token:
            raise ValueError(
                "OMA access token not provided. Set OMA_ACCESS_TOKEN environment variable "
                "or pass access_token parameter."
            )

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers with authorization"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    async def get_google_credentials(self) -> Credentials:
        """
        Fetch Google OAuth credentials from OMA backend

        Returns:
            google.oauth2.credentials.Credentials object ready for use with Google APIs

        Raises:
            httpx.HTTPError: If request fails
            ValueError: If credentials are not found or invalid
        """
        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            response = await client.get(
                f"{self.base_url}/google/credentials",
                headers=self._get_headers(),
                timeout=30.0
            )

            if response.status_code == 404:
                raise ValueError(
                    "Google account not connected. User must connect their Google account "
                    "through the web interface first."
                )

            response.raise_for_status()
            data = response.json()

        # Create Google Credentials object
        credentials = Credentials(
            token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=data.get("scopes", [])
        )

        # Set expiry if provided
        if data.get("token_expiry"):
            # Parse ISO format datetime
            expiry = datetime.fromisoformat(data["token_expiry"].replace("Z", "+00:00"))
            credentials.expiry = expiry

        return credentials

    def get_google_credentials_sync(self) -> Credentials:
        """
        Synchronous version of get_google_credentials

        Returns:
            google.oauth2.credentials.Credentials object ready for use with Google APIs
        """
        with httpx.Client(verify=self.verify_ssl) as client:
            response = client.get(
                f"{self.base_url}/google/credentials",
                headers=self._get_headers(),
                timeout=30.0
            )

            if response.status_code == 404:
                raise ValueError(
                    "Google account not connected. User must connect their Google account "
                    "through the web interface first."
                )

            response.raise_for_status()
            data = response.json()

        # Create Google Credentials object
        credentials = Credentials(
            token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=data.get("scopes", [])
        )

        # Set expiry if provided
        if data.get("token_expiry"):
            expiry = datetime.fromisoformat(data["token_expiry"].replace("Z", "+00:00"))
            credentials.expiry = expiry

        return credentials

    async def check_google_status(self) -> dict[str, bool]:
        """
        Check Google services connection status

        Returns:
            Dict with gmail_connected and calendar_connected status
        """
        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            response = await client.get(
                f"{self.base_url}/google/status",
                headers=self._get_headers(),
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()


# Global instance (lazy initialization)
_oma_client: Optional[OMAAuthClient] = None


def get_oma_client() -> OMAAuthClient:
    """
    Get or create global OMA client instance

    Returns:
        OMAAuthClient instance
    """
    global _oma_client
    if _oma_client is None:
        _oma_client = OMAAuthClient()
    return _oma_client


def get_google_creds_from_oma() -> Credentials:
    """
    Convenience function to get Google credentials from OMA backend

    This replaces the old get_google_creds() function that used local token files.
    Now credentials are managed centrally by OMA backend.

    Returns:
        google.oauth2.credentials.Credentials object

    Example:
        >>> from mcp_hub.auth.oma_client import get_google_creds_from_oma
        >>> creds = get_google_creds_from_oma()
        >>> from googleapiclient.discovery import build
        >>> gmail = build("gmail", "v1", credentials=creds)
    """
    client = get_oma_client()
    return client.get_google_credentials_sync()
