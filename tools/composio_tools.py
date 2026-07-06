"""Composio tool layer — typed functions for the connected apps
(Outlook email, HubSpot CRM, Google Calendar, GitHub, Notion).

Two kinds of function, one hard rule:
  READ  — executes immediately, returns display text. Runs silently.
  WRITE — NEVER executes here. Returns a staged dict
          {"action", "slug", "payload", "preview_text"} that must go through
          tools.approval_gate (drafts table + approve tap) first;
          execute_staged() is what the gate calls after the yes.

The API key lives in private/*.yml (`composio_api_key`) — never in git.
Action slugs match the installed composio SDK (0.7.x, verified against its
local enum stubs); tests/test_composio_tools.py re-verifies slugs and our
param names against the LIVE schemas once a key is configured.
"""
import threading
from datetime import datetime, timedelta

from config import (COMPOSIO_API_KEY, COMPOSIO_CALENDAR_ID,
                    COMPOSIO_DEFAULT_REPO, COMPOSIO_ENABLED, COMPOSIO_ENTITY,
                    COMPOSIO_NOTION_DB, TIMEZONE)


class ComposioNotConfigured(RuntimeError):
    pass


class ComposioError(RuntimeError):
    pass


SETUP_HINT = (
    "Composio isn't configured. One-time setup:\n"
    "1. app.composio.dev → create account → Settings → copy API key\n"
    "2. add `composio_api_key: \"...\"` to private/euan.yml (top level)\n"
    "3. on app.composio.dev connect: outlook, hubspot, googlecalendar, "
    "github, notion\n"
    "4. run tests/test_composio_tools.py to verify, then restart the bot")

_toolset_lock = threading.Lock()
_toolset = None


def configured() -> bool:
    return COMPOSIO_ENABLED and bool(COMPOSIO_API_KEY)


def toolset():
    """Lazy singleton — importing composio is slow, only pay it on first use."""
    global _toolset
    if not configured():
        raise ComposioNotConfigured(SETUP_HINT)
    with _toolset_lock:
        if _toolset is None:
            from composio import ComposioToolSet
            _toolset = ComposioToolSet(api_key=COMPOSIO_API_KEY,
                                       entity_id=COMPOSIO_ENTITY)
    return _toolset


def _execute(slug: str, params: dict) -> dict:
    """Run one Composio action, normalise the 0.7 response envelope."""
    res = toolset().execute_action(action=slug, params=params)
    if isinstance(res, dict):
        ok = res.get("successful", res.get("successfull", True))
        if not ok:
            # error text can embed request URLs — keep it short, never log keys
            raise ComposioError(str(res.get("error") or "action failed")[:300])
        data = res.get("data")
        return data if isinstance(data, dict) else {"result": data}
    return {"result": res}


def _staged(action: str, slug: str, payload: dict, preview: str) -> dict:
    return {"action": action, "slug": slug, "payload": payload,
            "preview_text": preview}


def execute_staged(staged: dict) -> str:
    """Run a previously staged WRITE action — only the approval gate calls
    this, after the user's explicit yes."""
    slug, name = staged.get("slug", ""), staged.get("action", "?")
    if slug not in {t["slug"] for t in _WRITE_SLUGS}:
        raise ComposioError(f"unknown staged action: {name}")
    data = _execute(slug, staged.get("payload") or {})
    return _summarise_result(name, data)


def _summarise_result(name: str, data: dict) -> str:
    """One phone-readable line per executed action, id/url if the app gave one."""
    ref = data.get("id") or data.get("html_url") or data.get("url") or ""
    rd = data.get("response_data")
    if not ref and isinstance(rd, dict):
        ref = rd.get("id") or rd.get("htmlLink") or rd.get("url") or ""
    return f"{name} done" + (f" — {ref}" if ref else "")


def connection_status() -> str:
    """Which apps are connected on the Composio account — used by /connect."""
    apps = {}
    for acc in toolset().get_connected_accounts():
        app = str(getattr(acc, "appName", getattr(acc, "appUniqueId", "?"))).lower()
        status = str(getattr(acc, "status", "?")).upper()
        apps.setdefault(app, status)
    wanted = ["outlook", "hubspot", "googlecalendar", "github", "notion"]
    lines = [f"{'✅' if apps.get(a) == 'ACTIVE' else '❌'} {a}"
             + (f" ({apps[a].lower()})" if apps.get(a) not in (None, "ACTIVE") else "")
             for a in wanted]
    extra = sorted(set(apps) - set(wanted))
    if extra:
        lines.append(f"also connected: {', '.join(extra)}")
    lines.append("connect missing apps at app.composio.dev → Apps")
    return "\n".join(lines)


# ── Outlook (email) ──────────────────────────────────────────────────────────
# Sender identity comes from the connected Outlook account on Composio —
# never hardcoded here (private repo rule: the address lives in config/OAuth).

def outlook_draft_email(to: str, subject: str, body: str) -> dict:
    """Stage an email DRAFT in the connected Outlook mailbox (write-gated).

    Example:
        staged = outlook_draft_email("owner@cafe.ie", "your booking link",
                                     "Hey — the booking link on your site 404s…")
        approval_gate.stage(staged)   # user must tap approve
    """
    return _staged(
        "outlook_draft_email", "OUTLOOK_OUTLOOK_CREATE_DRAFT",
        {"to_email": to, "subject": subject, "body": body, "is_html": False},
        f"📧 CREATE DRAFT (outlook)\nto: {to}\nsubject: {subject}\n---\n{body[:800]}")


def outlook_send_email(to: str, subject: str, body: str) -> dict:
    """Stage a SEND from the connected Outlook mailbox (write-gated).

    Example:
        staged = outlook_send_email("owner@cafe.ie", "one-page mock-up",
                                    "Said I'd send this over — link below.")
    """
    domain = to.rsplit("@", 1)[-1] if "@" in to else "?"
    return _staged(
        "outlook_send_email", "OUTLOOK_OUTLOOK_SEND_EMAIL",
        {"to_email": to, "subject": subject, "body": body, "is_html": False},
        f"📧 SEND EMAIL (outlook)\nto: {to}\n⚠️ sends to domain: {domain.upper()}\n"
        f"subject: {subject}\n---\n{body[:800]}")


# ── HubSpot (CRM) ────────────────────────────────────────────────────────────

def hubspot_create_contact(email: str, first_name: str, last_name: str = "",
                           company: str = "", phone: str = "") -> dict:
    """Stage a new HubSpot contact (write-gated).

    Example:
        staged = hubspot_create_contact("owner@cafe.ie", "Mary", "Byrne",
                                        company="The Corner Cafe", phone="+3531…")
    """
    props = {"email": email, "firstname": first_name}
    if last_name:
        props["lastname"] = last_name
    if company:
        props["company"] = company
    if phone:
        props["phone"] = phone
    human = " · ".join(f"{k}: {v}" for k, v in props.items())
    return _staged(
        "hubspot_create_contact", "HUBSPOT_CREATE_CONTACT_OBJECT_WITH_PROPERTIES",
        {"properties": props},
        f"👤 CREATE CRM CONTACT (hubspot)\n{human}")


def hubspot_log_note(contact_id: str, note: str) -> dict:
    """Stage a note/activity on a HubSpot contact (write-gated).

    Uses the generic CRM-objects action with objectType=notes, associated to
    the contact (association typeId 202 = note→contact).

    Example:
        staged = hubspot_log_note("union://cafe/12345",
                                  "Called 14:10 — Fridays are dead, wants booking.")
    """
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    payload = {
        "objectType": "notes",
        "properties": {"hs_note_body": note, "hs_timestamp": ts},
        "associations": [{
            "to": {"id": contact_id},
            "types": [{"associationCategory": "HUBSPOT_DEFINED",
                       "associationTypeId": 202}],
        }],
    }
    return _staged(
        "hubspot_log_note", "HUBSPOT_CREATE_CRM_OBJECT_WITH_PROPERTIES", payload,
        f"📝 LOG CRM NOTE (hubspot)\ncontact: {contact_id}\n---\n{note[:600]}")


# ── Google Calendar ──────────────────────────────────────────────────────────

def calendar_create_event(title: str, start_iso: str, duration_minutes: int = 60,
                          description: str = "", attendees: list | None = None,
                          location: str = "") -> dict:
    """Stage a Google Calendar event (write-gated).

    Example:
        staged = calendar_create_event("Call — Corner Cafe site",
                                       "2026-07-08T14:00:00", 30,
                                       description="walk through the mock-up")
    """
    payload = {
        "calendar_id": COMPOSIO_CALENDAR_ID,
        "summary": title,
        "start_datetime": start_iso,
        "event_duration_hour": duration_minutes // 60,
        "event_duration_minutes": duration_minutes % 60,
        "timezone": TIMEZONE or "Europe/Dublin",
    }
    if description:
        payload["description"] = description
    if attendees:
        payload["attendees"] = attendees
    if location:
        payload["location"] = location
    who = f"\nattendees: {', '.join(attendees)}" if attendees else ""
    return _staged(
        "calendar_create_event", "GOOGLECALENDAR_CREATE_EVENT", payload,
        f"📅 CREATE EVENT (google calendar)\n{title}\n"
        f"start: {start_iso} · {duration_minutes} min{who}"
        + (f"\n{description[:200]}" if description else ""))


def calendar_list_events(days: int = 7) -> str:
    """READ — upcoming events in the next `days` days; runs immediately.

    Example:
        text = calendar_list_events(3)   # "Tue 08 14:00 Call — Corner Cafe…"
    """
    now = datetime.now().astimezone()
    data = _execute("GOOGLECALENDAR_FIND_EVENT", {
        "calendar_id": COMPOSIO_CALENDAR_ID,
        "timeMin": now.isoformat(timespec="seconds"),
        "timeMax": (now + timedelta(days=days)).isoformat(timespec="seconds"),
        "single_events": True,
        "order_by": "startTime",
    })
    items = _find_items(data)
    if not items:
        return f"no events in the next {days} days"
    lines = []
    for ev in items[:15]:
        start = (ev.get("start") or {})
        when = start.get("dateTime", start.get("date", "?"))[:16].replace("T", " ")
        lines.append(f"• {when} — {ev.get('summary', '(no title)')}")
    return "\n".join(lines)


def _find_items(data: dict) -> list:
    """Composio nests list payloads differently per app/version — dig for it."""
    for key in ("items", "events", "event_data"):
        v = data.get(key)
        if isinstance(v, list):
            return v
        if isinstance(v, dict) and isinstance(v.get("event_data"), list):
            return v["event_data"]
    rd = data.get("response_data")
    if isinstance(rd, dict):
        return _find_items(rd)
    return []


# ── tool registry ────────────────────────────────────────────────────────────
# name → (function, "read"|"write"). Agents request tools by these names in
# the envelope's "actions" list; anything not in here is refused.
TOOLS: dict = {}
_WRITE_SLUGS: list = []


def _register(name: str, fn, kind: str, slug: str = ""):
    TOOLS[name] = (fn, kind)
    if kind == "write" and slug:
        _WRITE_SLUGS.append({"tool": name, "slug": slug})


_register("calendar_create_event", calendar_create_event, "write",
          "GOOGLECALENDAR_CREATE_EVENT")
_register("calendar_list_events", calendar_list_events, "read")
_register("hubspot_create_contact", hubspot_create_contact, "write",
          "HUBSPOT_CREATE_CONTACT_OBJECT_WITH_PROPERTIES")
_register("hubspot_log_note", hubspot_log_note, "write",
          "HUBSPOT_CREATE_CRM_OBJECT_WITH_PROPERTIES")
_register("outlook_draft_email", outlook_draft_email, "write",
          "OUTLOOK_OUTLOOK_CREATE_DRAFT")
_register("outlook_send_email", outlook_send_email, "write",
          "OUTLOOK_OUTLOOK_SEND_EMAIL")


def run_tool_request(tool: str, args: dict) -> tuple[str, object]:
    """One agent-requested action → ("read", display_text) executed now, or
    ("write", staged_dict) for the approval gate. Raises ComposioNotConfigured
    / ComposioError / ValueError upward — callers turn those into chat lines."""
    if tool not in TOOLS:
        raise ValueError(f"unknown tool: {tool}")
    fn, kind = TOOLS[tool]
    result = fn(**(args or {}))
    return kind, result
