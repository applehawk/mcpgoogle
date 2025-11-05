from __future__ import annotations
import mimetypes
from base64 import urlsafe_b64decode, urlsafe_b64encode
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Sequence
from googleapiclient.discovery import build
from mcp_hub.core import mcp
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

@mcp.tool(name="gmail_list_unread", description="Lista correos no leidos (INBOX).")
def gmail_list_unread(max_results: int = 10) -> List[Dict[str, Any]]:
    """Retorna remitente, asunto, fecha y el id del mensaje."""
    service = _build_gmail_service()
    resp = service.users().messages().list(
        userId="me",
        labelIds=["INBOX", "UNREAD"],
        maxResults=max_results,
    ).execute()
    messages = resp.get("messages", [])
    return [_summarize_message(service, m["id"]) for m in messages]

@mcp.tool(name="gmail_search_messages", description="Busca correos usando la sintaxis de Gmail.")
def gmail_search_messages(query_text: str, max_results: int = 10) -> List[Dict[str, Any]]:
    service = _build_gmail_service()
    resp = service.users().messages().list(
        userId="me",
        q=query_text,
        maxResults=max_results,
    ).execute()
    messages = resp.get("messages", [])
    return [_summarize_message(service, m["id"]) for m in messages]

@mcp.tool(name="gmail_get_message", description="Obtiene el cuerpo (texto) de un correo por id.")
def gmail_get_message(message_id: str) -> Dict[str, Any]:
    service = _build_gmail_service()
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    payload = msg.get("payload", {})
    body_text = _extract_text(payload)
    return {"snippet": msg.get("snippet"), "text": body_text[:10000]}

@mcp.tool(name="gmail_modify_message", description="Anade o quita labels en un mensaje de Gmail.")
def gmail_modify_message(
    message_id: str,
    add_labels: Sequence[str] | None = None,
    remove_labels: Sequence[str] | None = None,
) -> Dict[str, Any]:
    if not add_labels and not remove_labels:
        raise ValueError("Debes indicar add_labels o remove_labels.")
    service = _build_gmail_service()
    body: Dict[str, Any] = {}
    if add_labels:
        body["addLabelIds"] = list(add_labels)
    if remove_labels:
        body["removeLabelIds"] = list(remove_labels)
    resp = service.users().messages().modify(userId="me", id=message_id, body=body).execute()
    return {"id": resp.get("id"), "labelIds": resp.get("labelIds", [])}

@mcp.tool(name="gmail_mark_as_read", description="Marca un correo como leido y opcionalmente lo archiva.")
def gmail_mark_as_read(message_id: str, archive: bool = False) -> Dict[str, Any]:
    remove = ["UNREAD"]
    if archive:
        remove.append("INBOX")
    return gmail_modify_message(message_id=message_id, remove_labels=remove)

@mcp.tool(name="gmail_send_message", description="Envia un correo simple con opcionales CC/BCC y adjuntos.")
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
            raise FileNotFoundError(f"No encuentro el adjunto: {path}")
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
