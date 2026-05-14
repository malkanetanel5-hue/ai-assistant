import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from fastapi import APIRouter, HTTPException
from googleapiclient.discovery import build
from pydantic import BaseModel

from routes.auth import load_credentials

router = APIRouter(prefix="/gmail", tags=["gmail"])


def _service():
    creds = load_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated with Google")
    return build("gmail", "v1", credentials=creds)


def _parse_message(msg: dict) -> dict:
    headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
    body = _extract_body(msg["payload"])
    return {
        "id": msg["id"],
        "threadId": msg["threadId"],
        "subject": headers.get("Subject", "(no subject)"),
        "from_": headers.get("From", ""),
        "to": headers.get("To", ""),
        "date": headers.get("Date", ""),
        "message_id_header": headers.get("Message-ID", ""),
        "snippet": msg.get("snippet", ""),
        "body": body[:3000],
    }


def _extract_body(payload: dict) -> str:
    """Walk MIME parts to find the plain-text body."""
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
    # Fallback: try any nested part
    for part in payload.get("parts", []):
        result = _extract_body(part)
        if result:
            return result
    return ""


# ── Read ─────────────────────────────────────────────────────────────────────

@router.get("/messages")
async def list_messages(max_results: int = 10, query: str = "in:inbox"):
    svc = _service()
    result = (
        svc.users()
        .messages()
        .list(userId="me", maxResults=min(max_results, 25), q=query)
        .execute()
    )
    messages = []
    for m in result.get("messages", []):
        full = svc.users().messages().get(userId="me", id=m["id"], format="full").execute()
        messages.append(_parse_message(full))
    return {"messages": messages}


@router.get("/messages/{message_id}")
async def get_message(message_id: str):
    svc = _service()
    msg = svc.users().messages().get(userId="me", id=message_id, format="full").execute()
    return _parse_message(msg)


# ── Write ─────────────────────────────────────────────────────────────────────

class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[str] = None
    # For replies: provide both so Gmail threads correctly
    reply_to_thread_id: Optional[str] = None
    in_reply_to_header: Optional[str] = None


@router.post("/send", status_code=201)
async def send_email(req: SendEmailRequest):
    svc = _service()

    mime = MIMEMultipart("alternative")
    mime["To"] = req.to
    mime["Subject"] = req.subject
    if req.cc:
        mime["Cc"] = req.cc
    if req.in_reply_to_header:
        mime["In-Reply-To"] = req.in_reply_to_header
        mime["References"] = req.in_reply_to_header

    mime.attach(MIMEText(req.body, "plain"))

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")
    body: dict = {"raw": raw}
    if req.reply_to_thread_id:
        body["threadId"] = req.reply_to_thread_id

    result = svc.users().messages().send(userId="me", body=body).execute()
    return {"id": result["id"], "threadId": result["threadId"]}
