"""
LangChain agent — full tool registry.

Phase 2: Calendar (list, create)
Phase 3: Gmail (read, send, reply), Web (search, browse page)
"""

from __future__ import annotations

import os
import textwrap
from datetime import datetime, timezone
from typing import Optional

from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from googleapiclient.discovery import build

from routes.auth import load_credentials


# ── Google service helpers ────────────────────────────────────────────────────

def _require_google(service_name: str, version: str):
    creds = load_credentials()
    if not creds:
        raise RuntimeError(
            "Not authenticated with Google. "
            "Click 'Connect Google' in the sidebar to complete the OAuth flow."
        )
    return build(service_name, version, credentials=creds)


# ═════════════════════════════════════════════════════════════════════════════
# CALENDAR TOOLS
# ═════════════════════════════════════════════════════════════════════════════

@tool
def list_calendar_events(max_results: int = 10) -> str:
    """
    List the user's upcoming Google Calendar events, ordered by start time.

    Args:
        max_results: How many events to return (1–25, default 10).
    """
    svc = _require_google("calendar", "v3")
    now = datetime.now(timezone.utc).isoformat()
    result = (
        svc.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=min(int(max_results), 25),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = result.get("items", [])
    if not events:
        return "No upcoming events found."

    lines = ["Upcoming calendar events:"]
    for e in events:
        start = e["start"].get("dateTime", e["start"].get("date", "?"))
        guests = ", ".join(a["email"] for a in e.get("attendees", []))
        line = f"  • {e.get('summary', '(no title)')} — {start}"
        if guests:
            line += f"  [guests: {guests}]"
        line += f"  [id: {e['id']}]"
        lines.append(line)
    return "\n".join(lines)


@tool
def create_calendar_event(
    summary: str,
    start_datetime: str,
    end_datetime: str,
    description: Optional[str] = None,
    attendee_emails: Optional[str] = None,
    timezone: str = "UTC",
) -> str:
    """
    Create a new Google Calendar event.

    Args:
        summary: Event title.
        start_datetime: ISO 8601 datetime, e.g. '2025-08-01T14:00:00Z'.
        end_datetime: ISO 8601 datetime for the end.
        description: Optional agenda or notes.
        attendee_emails: Comma-separated guest email addresses (optional).
        timezone: IANA timezone, e.g. 'America/New_York'. Default 'UTC'.
    """
    svc = _require_google("calendar", "v3")
    body: dict = {
        "summary": summary,
        "start": {"dateTime": start_datetime, "timeZone": timezone},
        "end": {"dateTime": end_datetime, "timeZone": timezone},
    }
    if description:
        body["description"] = description
    if attendee_emails:
        body["attendees"] = [
            {"email": e.strip()} for e in attendee_emails.split(",") if e.strip()
        ]
    event = svc.events().insert(calendarId="primary", body=body).execute()
    return (
        f"Event created: '{event['summary']}'\n"
        f"  Start : {start_datetime}\n"
        f"  End   : {end_datetime}\n"
        f"  Link  : {event.get('htmlLink', 'N/A')}"
    )


# ═════════════════════════════════════════════════════════════════════════════
# GMAIL TOOLS
# ═════════════════════════════════════════════════════════════════════════════

def _extract_body(payload: dict) -> str:
    import base64
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        result = _extract_body(part)
        if result:
            return result
    return ""


@tool
def read_latest_emails(max_results: int = 8, query: str = "in:inbox") -> str:
    """
    Read the user's latest Gmail messages.

    Args:
        max_results: Number of emails to fetch (1–15, default 8).
        query: Gmail search query. Examples:
               'in:inbox' (default), 'is:unread', 'from:boss@company.com',
               'subject:invoice', 'in:inbox is:unread newer_than:1d'
    """
    import base64

    svc = _require_google("gmail", "v1")
    result = (
        svc.users()
        .messages()
        .list(userId="me", maxResults=min(int(max_results), 15), q=query)
        .execute()
    )
    msgs = result.get("messages", [])
    if not msgs:
        return "No emails found matching that query."

    lines = [f"Found {len(msgs)} email(s):"]
    for m in msgs:
        full = svc.users().messages().get(userId="me", id=m["id"], format="full").execute()
        headers = {h["name"]: h["value"] for h in full["payload"].get("headers", [])}
        body = _extract_body(full["payload"])
        lines.append(
            f"\n--- Email id: {full['id']} (thread: {full['threadId']}) ---\n"
            f"From   : {headers.get('From', '?')}\n"
            f"Subject: {headers.get('Subject', '(no subject)')}\n"
            f"Date   : {headers.get('Date', '?')}\n"
            f"Body   :\n{textwrap.shorten(body.strip(), 600, placeholder=' …[truncated]')}"
        )
    return "\n".join(lines)


@tool
def send_email(to: str, subject: str, body: str, cc: Optional[str] = None) -> str:
    """
    Compose and send a new email via Gmail.

    Args:
        to: Recipient email address (or comma-separated list).
        subject: Email subject line.
        body: Plain-text email body.
        cc: Optional CC addresses (comma-separated).
    """
    import base64
    from email.mime.text import MIMEText

    svc = _require_google("gmail", "v1")
    mime = MIMEText(body, "plain")
    mime["To"] = to
    mime["Subject"] = subject
    if cc:
        mime["Cc"] = cc

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")
    result = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    return f"Email sent successfully. Message ID: {result['id']}"


@tool
def reply_to_email(
    thread_id: str,
    in_reply_to_header: str,
    to: str,
    subject: str,
    body: str,
) -> str:
    """
    Reply to an existing Gmail thread.

    Args:
        thread_id: The threadId of the email being replied to.
        in_reply_to_header: The Message-ID header value from the original email
                            (looks like '<abc123@mail.example.com>').
        to: Reply-to address (usually the sender of the original).
        subject: Subject line (prefix with 'Re: ' if not already present).
        body: Plain-text reply body.
    """
    import base64
    from email.mime.text import MIMEText

    svc = _require_google("gmail", "v1")
    subject = subject if subject.startswith("Re:") else f"Re: {subject}"
    mime = MIMEText(body, "plain")
    mime["To"] = to
    mime["Subject"] = subject
    mime["In-Reply-To"] = in_reply_to_header
    mime["References"] = in_reply_to_header

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")
    result = (
        svc.users()
        .messages()
        .send(userId="me", body={"raw": raw, "threadId": thread_id})
        .execute()
    )
    return f"Reply sent. Message ID: {result['id']}"


# ═════════════════════════════════════════════════════════════════════════════
# WEB TOOLS
# ═════════════════════════════════════════════════════════════════════════════

@tool
def search_web(query: str, max_results: int = 6) -> str:
    """
    Search the web using DuckDuckGo and return the top results.
    Use this when the user asks for current information, news, prices, or
    anything that requires looking something up online.

    Args:
        query: The search query.
        max_results: Number of results to return (default 6).
    """
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return "duckduckgo-search package not installed. Run: pip install duckduckgo-search"

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=min(int(max_results), 10)))
    except Exception as e:
        return f"Search failed: {e}"

    if not results:
        return "No results found."

    lines = [f"Web search results for '{query}':"]
    for i, r in enumerate(results, 1):
        lines.append(
            f"\n[{i}] {r.get('title', 'No title')}\n"
            f"    URL: {r.get('href', '')}\n"
            f"    {textwrap.shorten(r.get('body', ''), 200, placeholder=' …')}"
        )
    return "\n".join(lines)


@tool
def browse_page(url: str) -> str:
    """
    Open a specific URL with a headless browser and extract the readable text.
    Use this after search_web to read the full content of a page, or when
    the user provides a URL they want you to read.

    Args:
        url: The full URL to visit (must start with http:// or https://).
    """
    if not url.startswith(("http://", "https://")):
        return "Invalid URL — must start with http:// or https://"

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "Playwright not installed. Run: pip install playwright && playwright install chromium"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=20_000, wait_until="domcontentloaded")
            # Extract all visible text, stripping scripts/styles
            text = page.evaluate("""() => {
                const remove = document.querySelectorAll('script,style,nav,footer,header,aside');
                remove.forEach(el => el.remove());
                return document.body.innerText;
            }""")
            browser.close()
        # Truncate to keep the agent context manageable
        clean = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        return f"Content from {url}:\n\n{clean[:4000]}" + (" …[truncated]" if len(clean) > 4000 else "")
    except Exception as e:
        return f"Failed to browse {url}: {e}"


# ═════════════════════════════════════════════════════════════════════════════
# AGENT FACTORY
# ═════════════════════════════════════════════════════════════════════════════

_SYSTEM = """\
You are a helpful, concise personal AI assistant running on the user's desktop.
Current UTC time: {now}

You have access to:
  • Google Calendar — list and create events
  • Gmail — read emails, send new emails, reply to threads
  • Web search — DuckDuckGo search + page browsing via Playwright

Guidelines:
- Be direct and action-oriented. Prefer doing over asking.
- For event creation, infer end times when duration is obvious ("1-hour" → add 1h).
- For emails, always confirm the recipient and subject before sending unless the user made it explicit.
- When browsing the web, first search, then read the most relevant page.
- If a Google action fails because of missing auth, tell the user to click "Connect Google".
- Format dates and times in a readable way (e.g., "Monday June 2 at 3:00 PM").
"""

TOOLS = [
    # Calendar
    list_calendar_events,
    create_calendar_event,
    # Gmail
    read_latest_emails,
    send_email,
    reply_to_email,
    # Web
    search_web,
    browse_page,
]

def _build_agent() -> AgentExecutor:
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0, google_api_key=os.getenv("GEMINI_API_KEY"))
    prompt = ChatPromptTemplate.from_messages([("system", _SYSTEM), MessagesPlaceholder("chat_history", optional=True), ("human", "{input}"), MessagesPlaceholder("agent_scratchpad")])
    agent = create_structured_chat_agent(llm, TOOLS, prompt)
    return AgentExecutor(agent=agent, tools=TOOLS, verbose=True, max_iterations=8)

_agent_instance: AgentExecutor | None = None


def get_agent() -> AgentExecutor:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = _build_agent()
    return _agent_instance


def serialize_history(raw: list[dict]) -> list:
    out = []
    for msg in raw:
        if msg.get("role") == "user":
            out.append(HumanMessage(content=msg["content"]))
        elif msg.get("role") == "assistant":
            out.append(AIMessage(content=msg["content"]))
    return out
