from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence
from googleapiclient.discovery import build
from mcp_hub.core import mcp
from ..auth.google_auth import get_google_creds

def _build_calendar_service():
    creds = get_google_creds()
    return build("calendar", "v3", credentials=creds)

def _normalize_datetime(dt: str | datetime, default_tz: str = "UTC") -> Dict[str, Any]:
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return {"dateTime": dt.isoformat()}
    if len(dt) == 10:
        return {"date": dt}
    return {"dateTime": dt, "timeZone": default_tz}

@mcp.tool(name="calendar_upcoming", description="Lista proximos eventos del calendario principal.")
def calendar_upcoming(max_events: int = 10) -> List[Dict[str, Any]]:
    service = _build_calendar_service()
    now = datetime.now(timezone.utc).isoformat()
    events_result = service.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=max_events,
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    items = events_result.get("items", [])
    out = []
    for e in items:
        out.append(
            {
                "id": e.get("id"),
                "summary": e.get("summary"),
                "start": e.get("start"),
                "end": e.get("end"),
                "location": e.get("location"),
            }
        )
    return out

@mcp.tool(name="calendar_create_event", description="Crea un evento en el calendario primario.")
def calendar_create_event(
    summary: str,
    start: str,
    end: str,
    description: str | None = None,
    location: str | None = None,
    attendees: Sequence[str] | None = None,
    reminders_minutes: Sequence[int] | None = None,
) -> Dict[str, Any]:
    service = _build_calendar_service()
    body: Dict[str, Any] = {
        "summary": summary,
        "start": _normalize_datetime(start),
        "end": _normalize_datetime(end),
    }
    if description:
        body["description"] = description
    if location:
        body["location"] = location
    if attendees:
        body["attendees"] = [{"email": email} for email in attendees]
    if reminders_minutes:
        body["reminders"] = {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": minutes} for minutes in reminders_minutes],
        }
    created = service.events().insert(calendarId="primary", body=body, sendUpdates="all").execute()
    return {"id": created.get("id"), "htmlLink": created.get("htmlLink")}

@mcp.tool(name="calendar_update_event", description="Actualiza campos de un evento existente.")
def calendar_update_event(
    event_id: str,
    summary: str | None = None,
    start: str | None = None,
    end: str | None = None,
    description: str | None = None,
    location: str | None = None,
    attendees: Sequence[str] | None = None,
    reminders_minutes: Sequence[int] | None = None,
) -> Dict[str, Any]:
    service = _build_calendar_service()
    event = service.events().get(calendarId="primary", eventId=event_id).execute()
    if summary is not None:
        event["summary"] = summary
    if start is not None:
        event["start"] = _normalize_datetime(start)
    if end is not None:
        event["end"] = _normalize_datetime(end)
    if description is not None:
        event["description"] = description
    if location is not None:
        event["location"] = location
    if attendees is not None:
        event["attendees"] = [{"email": email} for email in attendees]
    if reminders_minutes is not None:
        event["reminders"] = {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": minutes} for minutes in reminders_minutes],
        }
    updated = service.events().update(
        calendarId="primary",
        eventId=event_id,
        body=event,
        sendUpdates="all",
    ).execute()
    return {"id": updated.get("id"), "htmlLink": updated.get("htmlLink")}

@mcp.tool(name="calendar_delete_event", description="Elimina un evento del calendario principal.")
def calendar_delete_event(event_id: str, send_updates: bool = False) -> Dict[str, Any]:
    service = _build_calendar_service()
    service.events().delete(
        calendarId="primary",
        eventId=event_id,
        sendUpdates="all" if send_updates else "none",
    ).execute()
    return {"status": "deleted", "id": event_id}

@mcp.tool(name="calendar_export_event", description="Exporta un evento como archivo .ics almacenado localmente.")
def calendar_export_event(event_id: str, destination_path: str) -> Dict[str, Any]:
    service = _build_calendar_service()
    event = service.events().get(calendarId="primary", eventId=event_id).execute()
    dest = Path(destination_path).expanduser()
    dest.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//MCP Hub Ricardo//Calendar Export//ES",
        "BEGIN:VEVENT",
        f"UID:{event.get('id')}",
        f"SUMMARY:{event.get('summary','')}",
        f"DTSTART:{event.get('start',{}).get('dateTime', event.get('start',{}).get('date',''))}",
        f"DTEND:{event.get('end',{}).get('dateTime', event.get('end',{}).get('date',''))}",
        f"LOCATION:{event.get('location','')}",
        f"DESCRIPTION:{event.get('description','')}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    dest.write_text("\r\n".join(lines), encoding="utf-8")
    return {"saved_to": str(dest)}
