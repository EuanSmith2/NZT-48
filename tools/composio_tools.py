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


# ── tool registry ────────────────────────────────────────────────────────────
# name → (function, "read"|"write"). Agents request tools by these names in
# the envelope's "actions" list; anything not in here is refused.
TOOLS: dict = {}
_WRITE_SLUGS: list = []


def _register(name: str, fn, kind: str, slug: str = ""):
    TOOLS[name] = (fn, kind)
    if kind == "write" and slug:
        _WRITE_SLUGS.append({"tool": name, "slug": slug})


def run_tool_request(tool: str, args: dict) -> tuple[str, object]:
    """One agent-requested action → ("read", display_text) executed now, or
    ("write", staged_dict) for the approval gate. Raises ComposioNotConfigured
    / ComposioError / ValueError upward — callers turn those into chat lines."""
    if tool not in TOOLS:
        raise ValueError(f"unknown tool: {tool}")
    fn, kind = TOOLS[tool]
    result = fn(**(args or {}))
    return kind, result
