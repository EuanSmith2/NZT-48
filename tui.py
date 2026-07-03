"""NZT-48 terminal dashboard — riced Arch/Ubuntu aesthetic.
Run: .venv/bin/python tui.py
Keys: Q quit · R refresh · B restart bot"""
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Static
from textual.containers import Horizontal, Vertical

sys.path.insert(0, str(Path(__file__).parent))
import state
from config import USER_NAME

try:
    import finance as _finance
    _HAS_FINANCE = True
except Exception:
    _HAS_FINANCE = False

# ── palette ──────────────────────────────────────────────────────────────────
G  = "#00ff66"   # primary green
G2 = "#00cc55"   # dim green
DIM = "#2a2a2a"  # borders
BG  = "#0a0a0a"  # background
BG2 = "#0d0d0d"  # card background
YEL = "#f0b429"  # warning
RED = "#ff5f57"  # error
GRY = "#444444"  # muted text

# ── CSS ──────────────────────────────────────────────────────────────────────
CSS = f"""
Screen {{
    background: {BG};
    color: {G};
    layers: base;
}}

#infobar {{
    height: 4;
    width: 100%;
    background: {BG};
    color: {G};
    padding: 0 2;
    border-bottom: solid {DIM};
}}

#top-row {{
    height: 1fr;
    width: 100%;
}}

#bottom-row {{
    height: 12;
    width: 100%;
    border-top: solid {DIM};
}}

.panel {{
    background: {BG2};
    border: solid {DIM};
    padding: 0 1;
    height: 100%;
}}

#status-panel   {{ width: 22; }}
#messages-panel {{ width: 1fr; }}
#pipeline-panel {{ width: 28; }}
#tasks-panel    {{ width: 1fr; }}
#alerts-panel   {{ width: 1fr; }}

Footer {{
    background: {BG};
    color: {GRY};
}}
"""

# ── helpers ───────────────────────────────────────────────────────────────────

def _midnight() -> float:
    return datetime.combine(date.today(), datetime.min.time()).timestamp()


def _bot_status() -> tuple[str, str]:
    try:
        out = subprocess.check_output(
            ["launchctl", "list", "com.nzt48"], text=True, stderr=subprocess.DEVNULL)
        pid_line = next((l for l in out.splitlines() if '"PID"' in l), "")
        pid = pid_line.split("=")[-1].strip().rstrip(";").strip('"') if pid_line else None
        if pid and pid != "0":
            return "running", pid
        return "stopped", ""
    except Exception:
        return "unknown", ""


def _gather() -> dict:
    state.init()
    midnight = _midnight()
    with state.db() as con:
        msgs = con.execute(
            "SELECT role, text, ts FROM messages ORDER BY ts DESC LIMIT 10"
        ).fetchall()
        alerts = con.execute(
            "SELECT monitor, key FROM alerts WHERE sent=1 AND ts>? ORDER BY ts DESC LIMIT 6",
            (midnight,),
        ).fetchall()
        tasks = con.execute(
            "SELECT title, status FROM tasks ORDER BY id DESC LIMIT 8"
        ).fetchall()
        cost_row = con.execute(
            "SELECT COALESCE(SUM(usd),0), COALESCE(SUM(tok_in+tok_out),0) "
            "FROM cost_log WHERE ts>?", (midnight,)
        ).fetchone()
        pending = con.execute(
            "SELECT COUNT(*) FROM drafts WHERE status='pending'"
        ).fetchone()[0]

    fin = {}
    if _HAS_FINANCE:
        try:
            fin = _finance.compute()
        except Exception:
            pass

    status, pid = _bot_status()
    return {
        "bot_status": status,
        "bot_pid": pid,
        "cost_usd": round(cost_row[0], 4),
        "tokens": int(cost_row[1]),
        "pending_drafts": pending,
        "messages": list(reversed(msgs)),
        "alerts": alerts,
        "tasks": tasks,
        "fin": fin,
        "date": date.today().strftime("%a %d %b %Y"),
    }


def _color_role(role: str) -> str:
    return G if role == USER_NAME or role == "euan" else G2


def _status_icon(s: str) -> tuple[str, str]:
    if s == "running":  return "●", G
    if s == "stopped":  return "○", RED
    return "?", YEL


# ── widgets ───────────────────────────────────────────────────────────────────

LOGO = (
    " ███╗  ██╗███████╗████████╗\n"
    " ████╗ ██║╚══███╔╝╚══██╔══╝\n"
    " ██╔██╗██║  ███╔╝    ██║   \n"
    " ██║╚████║███████╗   ██║   \n"
    " ╚═╝ ╚═══╝╚══════╝   ╚═╝   "
)


class InfoBar(Static):
    def render(self) -> Text:
        import platform, socket
        t = Text()
        t.append("  NZT-48", style=f"bold {G}")
        t.append("  //  ", style=f"{DIM}")
        t.append(USER_NAME.upper(), style=f"bold {G2}")
        t.append("  //  ", style=f"{DIM}")
        t.append(socket.gethostname().split(".")[0], style=GRY)
        t.append("  //  ", style=DIM)
        t.append(f"macOS {platform.mac_ver()[0]}", style=GRY)
        t.append("  //  ", style=DIM)
        t.append(date.today().strftime("%a %d %b %Y"), style=GRY)
        return t


class StatusPanel(Static):
    DEFAULT_CSS = ".panel {}"

    def build(self, d: dict) -> Text:
        t = Text()
        t.append("─ STATUS ─\n\n", style=f"bold {G}")
        icon, col = _status_icon(d["bot_status"])
        t.append(f" {icon} bot     ", style=col)
        t.append(d["bot_status"] + "\n", style=col)
        t.append(f" $ cost    ", style=GRY)
        t.append(f"${d['cost_usd']:.4f}\n", style=G)
        t.append(f" ~ tokens  ", style=GRY)
        t.append(f"{d['tokens']:,}\n", style=G)
        t.append(f" ✉ pending ", style=GRY)
        pending = d["pending_drafts"]
        t.append(str(pending) + "\n", style=YEL if pending else G)

        t.append("\n─ SYSTEM ─\n\n", style=f"bold {G}")
        try:
            import psutil
            cpu = f"{psutil.cpu_percent(interval=0.1):.0f}%"
            mem = psutil.virtual_memory()
            ram = f"{mem.used/1e9:.1f}/{mem.total/1e9:.1f}GB"
        except Exception:
            cpu = "—"
            ram = "—"
        t.append(" ⚙ cpu     ", style=GRY)
        t.append(cpu + "\n", style=G)
        t.append(" ⚡ ram     ", style=GRY)
        t.append(ram + "\n", style=G)
        return t


class MessagesPanel(Static):
    def build(self, d: dict) -> Text:
        t = Text()
        t.append("─ MESSAGES ─\n\n", style=f"bold {G}")
        if not d["messages"]:
            t.append("  no messages yet", style=GRY)
            return t
        for role, text, ts in d["messages"][-8:]:
            label = "▶ euan " if role in ("euan", USER_NAME) else "◀ nzt  "
            t.append(f" {label}", style=f"bold {_color_role(role)}")
            snippet = text[:72].replace("\n", " ").strip()
            if len(text) > 72:
                snippet += "…"
            t.append(snippet + "\n", style=G2 if role in ("euan", USER_NAME) else GRY)
        return t


class PipelinePanel(Static):
    def build(self, d: dict) -> Text:
        t = Text()
        fin = d.get("fin", {})
        t.append("─ PIPELINE ─\n\n", style=f"bold {G}")
        t.append(" mrr      ", style=GRY)
        t.append(f"€{fin.get('mrr', 0)}\n", style=G)
        outstanding = fin.get("outstanding", [])
        t.append(" invoices ", style=GRY)
        t.append(f"{len(outstanding)}\n", style=YEL if outstanding else G)
        t.append(" calls/wk ", style=GRY)
        calls = fin.get("calls_this_week", 0)
        target = fin.get("weekly_call_target", 10)
        t.append(f"{calls}/{target}\n", style=G if calls >= target else YEL)
        t.append(" pipeline ", style=GRY)
        t.append(f"€{fin.get('pipeline_value', 0)}\n", style=G)
        t.append(" wks left ", style=GRY)
        t.append(f"{fin.get('weeks_left', '—')}\n", style=G)
        if outstanding:
            t.append("\n─ OUTSTANDING ─\n", style=f"bold {YEL}")
            for inv in outstanding[:4]:
                t.append(f" {inv.get('client','?')[:12]:<12} ", style=GRY)
                t.append(f"€{inv.get('amount',0)} d{inv.get('days',0)}\n", style=YEL)
        return t


STATUS_PILL = {"done": (G, "done"), "failed": (RED, "fail"), "running": (YEL, "run ")}


class TasksPanel(Static):
    def build(self, d: dict) -> Text:
        t = Text()
        t.append("─ TASKS ─\n\n", style=f"bold {G}")
        if not d["tasks"]:
            t.append("  no tasks", style=GRY)
            return t
        for title, status in d["tasks"]:
            col, lbl = STATUS_PILL.get(status, (GRY, status[:4]))
            t.append(f" [{lbl}] ", style=col)
            t.append(title[:45] + "\n", style=G2)
        return t


class AlertsPanel(Static):
    def build(self, d: dict) -> Text:
        t = Text()
        t.append("─ ALERTS TODAY ─\n\n", style=f"bold {G}")
        if not d["alerts"]:
            t.append("  none", style=GRY)
            return t
        for monitor, key in d["alerts"]:
            t.append(f" {monitor[:14]:<14} ", style=GRY)
            t.append(key[:30] + "\n", style=YEL)
        return t


# ── app ───────────────────────────────────────────────────────────────────────

class NZT48TUI(App):
    CSS = CSS
    TITLE = "NZT-48"
    BINDINGS = [
        Binding("q", "quit",    "Quit",         show=True),
        Binding("r", "refresh", "Refresh",       show=True),
        Binding("b", "restart", "Restart bot",   show=True),
    ]

    def compose(self) -> ComposeResult:
        yield InfoBar(id="infobar")
        with Horizontal(id="top-row"):
            yield StatusPanel(id="status-panel", classes="panel")
            yield MessagesPanel(id="messages-panel", classes="panel")
            yield PipelinePanel(id="pipeline-panel", classes="panel")
        with Horizontal(id="bottom-row"):
            yield TasksPanel(id="tasks-panel", classes="panel")
            yield AlertsPanel(id="alerts-panel", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_data()
        self.set_interval(10, self._refresh_data)

    def _refresh_data(self) -> None:
        try:
            d = _gather()
        except Exception as e:
            self.notify(f"refresh error: {e}", severity="error")
            return
        self.query_one("#status-panel",   StatusPanel).update(
            self.query_one("#status-panel", StatusPanel).build(d))
        self.query_one("#messages-panel", MessagesPanel).update(
            self.query_one("#messages-panel", MessagesPanel).build(d))
        self.query_one("#pipeline-panel", PipelinePanel).update(
            self.query_one("#pipeline-panel", PipelinePanel).build(d))
        self.query_one("#tasks-panel",    TasksPanel).update(
            self.query_one("#tasks-panel", TasksPanel).build(d))
        self.query_one("#alerts-panel",   AlertsPanel).update(
            self.query_one("#alerts-panel", AlertsPanel).build(d))

    def action_refresh(self) -> None:
        self._refresh_data()
        self.notify("refreshed", timeout=1)

    def action_restart(self) -> None:
        try:
            import os
            uid = os.getuid()
            subprocess.run(
                ["launchctl", "kickstart", "-k", f"gui/{uid}/com.nzt48"],
                timeout=5, capture_output=True)
            self.notify("bot restart triggered", timeout=2)
        except Exception as e:
            self.notify(f"restart failed: {e}", severity="error", timeout=3)


if __name__ == "__main__":
    NZT48TUI().run()
