from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from googleapiclient.discovery import build
from pydantic import BaseModel

from routes.auth import load_credentials

router = APIRouter(prefix="/calendar", tags=["calendar"])


def _service():
    creds = load_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated with Google")
    return build("calendar", "v3", credentials=creds)


# ── Read ─────────────────────────────────────────────────────────────────────

@router.get("/events")
async def list_events(max_results: int = 15, calendar_id: str = "primary"):
    svc = _service()
    now = datetime.now(timezone.utc).isoformat()
    result = (
        svc.events()
        .list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = result.get("items", [])
    # Slim down the payload for the frontend
    slim = [
        {
            "id": e["id"],
            "summary": e.get("summary", "(no title)"),
            "start": e["start"].get("dateTime", e["start"].get("date")),
            "end": e["end"].get("dateTime", e["end"].get("date")),
            "description": e.get("description", ""),
            "attendees": [a["email"] for a in e.get("attendees", [])],
            "htmlLink": e.get("htmlLink", ""),
        }
        for e in events
    ]
    return {"events": slim}


# ── Write ────────────────────────────────────────────────────────────────────

class CreateEventRequest(BaseModel):
    summary: str
    start: str  # ISO 8601 with timezone, e.g. 2025-06-01T10:00:00+02:00
    end: str
    description: Optional[str] = None
    attendees: Optional[list[str]] = None
    calendar_id: str = "primary"
    timezone: str = "UTC"


@router.post("/events", status_code=201)
async def create_event(req: CreateEventRequest):
    svc = _service()
    body: dict = {
        "summary": req.summary,
        "start": {"dateTime": req.start, "timeZone": req.timezone},
        "end": {"dateTime": req.end, "timeZone": req.timezone},
    }
    if req.description:
        body["description"] = req.description
    if req.attendees:
        body["attendees"] = [{"email": e} for e in req.attendees]
        body["guestsCanSeeOtherGuests"] = True

    event = svc.events().insert(calendarId=req.calendar_id, body=body).execute()
    return {
        "id": event["id"],
        "summary": event["summary"],
        "htmlLink": event.get("htmlLink", ""),
    }


class UpdateEventRequest(BaseModel):
    summary: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    description: Optional[str] = None
    timezone: str = "UTC"


@router.patch("/events/{event_id}")
async def update_event(event_id: str, req: UpdateEventRequest, calendar_id: str = "primary"):
    svc = _service()
    existing = svc.events().get(calendarId=calendar_id, eventId=event_id).execute()
    if req.summary:
        existing["summary"] = req.summary
    if req.description is not None:
        existing["description"] = req.description
    if req.start:
        existing["start"] = {"dateTime": req.start, "timeZone": req.timezone}
    if req.end:
        existing["end"] = {"dateTime": req.end, "timeZone": req.timezone}
    updated = svc.events().update(calendarId=calendar_id, eventId=event_id, body=existing).execute()
    return {"id": updated["id"], "summary": updated["summary"]}


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(event_id: str, calendar_id: str = "primary"):
    svc = _service()
    svc.events().delete(calendarId=calendar_id, eventId=event_id).execute()
