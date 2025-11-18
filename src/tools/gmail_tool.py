from __future__ import annotations
import mimetypes
from base64 import urlsafe_b64decode, urlsafe_b64encode
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Sequence
from googleapiclient.discovery import build
from src.core import mcp
from ..auth.google_auth import get_google_creds

def _build_gmail_service():
    creds = get_google_creds()
    return build("gmail", "v1", credentials=creds)

def _summarize_message(service, message_id: str) -> Dict[str, Any]:
    msg = service.users().messages().get(
        userId="me",
        id=message_id,
        format="metadata",
        metadataHeaders=["From", "Subject", "Date"],
    ).execute()
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    return {
        "id": message_id,
        "from": headers.get("From"),
        "subject": headers.get("Subject"),
        "date": headers.get("Date"),
    }

def _extract_text(payload: Dict[str, Any]) -> str:
    body = payload.get("body", {})
    data = body.get("data")
    if data and payload.get("mimeType") == "text/plain":
        return urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    for part in payload.get("parts") or []:
        text = _extract_text(part)
        if text:
            return text
    return ""

@mcp.tool(name="gmail_list_unread", description="List unread emails (INBOX).")
def gmail_list_unread(max_results: int = 10) -> List[Dict[str, Any]]:
    """Returns sender, subject, date and message id."""
    service = _build_gmail_service()
    resp = service.users().messages().list(
        userId="me",
        labelIds=["INBOX", "UNREAD"],
        maxResults=max_results,
    ).execute()
    messages = resp.get("messages", [])
    return [_summarize_message(service, m["id"]) for m in messages]

@mcp.tool(
    name="gmail_search_messages",
    description="Search emails using Gmail query syntax. Returns message metadata (id, from, subject, date). Use 'subject:keyword' to search in subject, 'from:email' to filter by sender, or just text to search everywhere."
)
def gmail_search_messages(query_text: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search emails using Gmail query syntax.
    Examples:
    - "subject:invoice" - search for "invoice" in subject
    - "from:noreply@example.com" - emails from specific sender
    - "is:unread" - unread emails
    - "has:attachment" - emails with attachments
    - "newer_than:7d" - emails from last 7 days
    """
    service = _build_gmail_service()
    resp = service.users().messages().list(
        userId="me",
        q=query_text,
        maxResults=max_results,
    ).execute()
    messages = resp.get("messages", [])
    return [_summarize_message(service, m["id"]) for m in messages]

@mcp.tool(name="gmail_get_message", description="Get the body (text) of a single email by id.")
def gmail_get_message(message_id: str) -> Dict[str, Any]:
    """Get full content of a single email message."""
    service = _build_gmail_service()
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    payload = msg.get("payload", {})
    headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
    body_text = _extract_text(payload)
    return {
        "id": message_id,
        "from": headers.get("From"),
        "to": headers.get("To"),
        "subject": headers.get("Subject"),
        "date": headers.get("Date"),
        "snippet": msg.get("snippet"),
        "text": body_text[:10000],
    }

@mcp.tool(
    name="gmail_get_messages_bulk",
    description="Get full content of multiple emails by their IDs (up to 50 messages). Returns from, to, subject, date, snippet and full text for each message."
)
def gmail_get_messages_bulk(message_ids: List[str], max_messages: int = 50) -> List[Dict[str, Any]]:
    """
    Get full content of multiple email messages in bulk.

    Args:
        message_ids: List of message IDs to retrieve
        max_messages: Maximum number of messages to retrieve (default 50)

    Returns:
        List of message objects with full content
    """
    service = _build_gmail_service()

    # Limit to max_messages
    ids_to_fetch = message_ids[:max_messages]

    results = []
    for msg_id in ids_to_fetch:
        try:
            msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
            payload = msg.get("payload", {})
            headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
            body_text = _extract_text(payload)

            results.append({
                "id": msg_id,
                "from": headers.get("From"),
                "to": headers.get("To"),
                "subject": headers.get("Subject"),
                "date": headers.get("Date"),
                "snippet": msg.get("snippet"),
                "text": body_text[:10000],  # Limit each message to 10k chars
            })
        except Exception as e:
            # Include error info but continue processing other messages
            results.append({
                "id": msg_id,
                "error": str(e),
            })

    return results

@mcp.tool(
    name="gmail_search_and_read",
    description="Search for emails using Gmail query syntax and immediately retrieve their full content (up to 50 messages). Combines search and bulk read in one operation."
)
def gmail_search_and_read(query_text: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search for emails and immediately get their full content.
    This is more efficient than calling search + get_messages_bulk separately.

    Args:
        query_text: Gmail search query (e.g., "subject:invoice", "from:example.com")
        max_results: Maximum number of messages to retrieve (max 50)

    Returns:
        List of messages with full content
    """
    # Limit to 50 messages max
    max_results = min(max_results, 50)

    service = _build_gmail_service()

    # Search for messages
    resp = service.users().messages().list(
        userId="me",
        q=query_text,
        maxResults=max_results,
    ).execute()

    messages = resp.get("messages", [])
    if not messages:
        return []

    # Get message IDs
    message_ids = [m["id"] for m in messages]

    # Fetch full content for all messages
    return gmail_get_messages_bulk(message_ids, max_messages=max_results)

@mcp.tool(name="gmail_modify_message", description="Add or remove labels on a Gmail message.")
def gmail_modify_message(
    message_id: str,
    add_labels: Sequence[str] | None = None,
    remove_labels: Sequence[str] | None = None,
) -> Dict[str, Any]:
    if not add_labels and not remove_labels:
        raise ValueError("Must specify add_labels or remove_labels.")
    service = _build_gmail_service()
    body: Dict[str, Any] = {}
    if add_labels:
        body["addLabelIds"] = list(add_labels)
    if remove_labels:
        body["removeLabelIds"] = list(remove_labels)
    resp = service.users().messages().modify(userId="me", id=message_id, body=body).execute()
    return {"id": resp.get("id"), "labelIds": resp.get("labelIds", [])}

@mcp.tool(name="gmail_mark_as_read", description="Mark an email as read and optionally archive it.")
def gmail_mark_as_read(message_id: str, archive: bool = False) -> Dict[str, Any]:
    remove = ["UNREAD"]
    if archive:
        remove.append("INBOX")
    return gmail_modify_message(message_id=message_id, remove_labels=remove)

@mcp.tool(name="gmail_send_message", description="Send a simple email with optional CC/BCC and attachments.")
def gmail_send_message(
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    attachments: Sequence[str] | None = None,
    thread_id: str | None = None,
    reply_to_message_id: str | None = None,
) -> Dict[str, Any]:
    service = _build_gmail_service()
    message = EmailMessage()
    message["To"] = to
    message["Subject"] = subject
    if cc:
        message["Cc"] = cc
    if bcc:
        message["Bcc"] = bcc
    if reply_to_message_id:
        message["In-Reply-To"] = reply_to_message_id
        message["References"] = reply_to_message_id
    message.set_content(body)

    for attachment in attachments or []:
        path = Path(attachment).expanduser()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Attachment not found: {path}")
        mime_type, _ = mimetypes.guess_type(str(path))
        maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)
        message.add_attachment(
            path.read_bytes(),
            maintype=maintype,
            subtype=subtype,
            filename=path.name,
        )

    encoded = urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    payload: Dict[str, Any] = {"raw": encoded}
    if thread_id:
        payload["threadId"] = thread_id
    resp = service.users().messages().send(userId="me", body=payload).execute()
    return {"id": resp.get("id"), "threadId": resp.get("threadId"), "labelIds": resp.get("labelIds", [])}
