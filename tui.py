"""NZT-48 terminal dashboard — riced neofetch/btop aesthetic.
Run: .venv/bin/python tui.py
Keys: Q quit · R refresh · B restart bot"""
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Static

sys.path.insert(0, str(Path(__file__).parent))
import state
from config import ROLE_KEY, USER_NAME

try:
    import finance as _finance
    _HAS_FINANCE = True
except Exception:
    _HAS_FINANCE = False

try:
    import psutil
    _HAS_PSUTIL = True
except Exception:
    _HAS_PSUTIL = False

try:
    import claude_usage as _cu
    _HAS_CU = True
except Exception:
    _HAS_CU = False

# ── palette ──────────────────────────────────────────────────────────────────
G    = "#00ff66"   # primary green
G2   = "#00cc55"   # dim green
DIM  = "#2a2a2a"   # dimmest text / separators
BORD = "#1a3d2b"   # borders (dark forest green)
BG   = "#0a0a0a"   # background
BG2  = "#080808"   # card background
YEL  = "#f0b429"   # warning
RED  = "#ff5f57"   # error
GRY  = "#444444"   # muted text

# ── CSS ──────────────────────────────────────────────────────────────────────
CSS = f"""
Screen {{
    background: {BG};
    color: {G};
}}

#header {{
    height: 9;
    width: 100%;
    background: {BG};
    padding: 0 2;
    border-bottom: solid {BORD};
}}

#clock {{
    dock: right;
    width: 10;
    height: 1;
    margin-right: 2;
    margin-top: 1;
    background: {BG};
}}

#logo {{
    width: 32;
    height: 100%;
    padding-top: 1;
}}

#sysinfo {{
    width: 1fr;
    height: 100%;
    padding-top: 1;
    padding-left: 4;
}}

#top-row {{
    height: 1fr;
    width: 100%;
}}

#bottom-row {{
    height: 12;
    width: 100%;
    border-top: solid {BORD};
}}

.panel {{
    background: {BG2};
    border: solid {BORD};
    padding: 0 1;
    height: 100%;
}}

#status-panel   {{ width: 24; }}
#messages-panel {{ width: 1fr; }}
#pipeline-panel {{ width: 28; }}
#tasks-panel    {{ width: 1fr; }}
#alerts-panel   {{ width: 1fr; }}

Footer {{
    background: {BG};
    color: {GRY};
}}
"""

LOGO = (
    "███╗  ██╗███████╗████████╗\n"
    "████╗ ██║╚══███╔╝╚══██╔══╝\n"
    "██╔██╗██║  ███╔╝    ██║\n"
    "██║╚████║███████╗   ██║\n"
    "╚═╝ ╚═══╝╚══════╝   ╚═╝"
)

BAR_W = 12


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


def _sys_stats() -> dict:
    """cpu%, ram used/total GB, uptime — all graceful when psutil is absent."""
    out = {"cpu_pct": None, "ram_used": None, "ram_total": None, "uptime": "—"}
    if not _HAS_PSUTIL:
        return out
    try:
        out["cpu_pct"] = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        out["ram_used"] = mem.used / 1e9
        out["ram_total"] = mem.total / 1e9
        secs = int(datetime.now().timestamp() - psutil.boot_time())
        h, m = secs // 3600, (secs % 3600) // 60
        out["uptime"] = f"{h}h {m}m"
    except Exception:
        pass
    return out


def _cpu_brand() -> str:
    try:
        return subprocess.check_output(
            ["sysctl", "-n", "machdep.cpu.brand_string"], text=True,
            stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "Apple Silicon"


def _bar(pct: float) -> Text:
    """12-char htop bar: green <60, yellow 60–85, red >85."""
    filled = max(0, min(BAR_W, round(pct / 100 * BAR_W)))
    col = G if pct < 60 else (YEL if pct <= 85 else RED)
    t = Text()
    t.append("▓" * filled, style=col)
    t.append("░" * (BAR_W - filled), style=DIM)
    return t


def _title(t: Text, label: str) -> None:
    t.append(f"▌ {label} ▐\n\n", style=f"bold {G}")


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

    usage = None
    if _HAS_CU:
        try:
            usage = _cu.gather()
        except Exception:
            pass

    status, pid = _bot_status()
    return {
        "bot_status": status,
        "bot_pid": pid,
        "usage": usage,
        "cost_usd": round(cost_row[0], 4),
        "tokens": int(cost_row[1]),
        "pending_drafts": pending,
        "messages": list(reversed(msgs)),
        "alerts": alerts,
        "tasks": tasks,
        "fin": fin,
        "sys": _sys_stats(),
        "refreshed": datetime.now().strftime("%H:%M:%S"),
    }


def _status_icon(s: str) -> tuple[str, str]:
    if s == "running":  return "●", G
    if s == "stopped":  return "○", RED
    return "?", YEL


# ── header widgets ────────────────────────────────────────────────────────────

class LogoPanel(Static):
    def render(self) -> Text:
        t = Text(LOGO, style=f"bold {G}")
        t.append("\n\n nzt-48 ", style=f"bold {G2}")
        t.append("· take the pill", style=DIM)
        return t


class SysInfo(Static):
    d: dict = {}

    def build(self, d: dict) -> Text:
        import platform
        import socket
        s = d.get("sys", {})
        host = socket.gethostname().split(".")[0]
        ram = ("—" if s["ram_used"] is None
               else f"{s['ram_used']:.1f} / {s['ram_total']:.1f} GB")
        icon, col = _status_icon(d["bot_status"])
        bot_val = (f"{icon} running (PID {d['bot_pid']})" if d["bot_status"] == "running"
                   else f"{icon} {d['bot_status']}")
        rows = [
            ("user", f"{USER_NAME}@{host}", GRY),
            ("os", f"macOS {platform.mac_ver()[0]}", GRY),
            ("shell", "zsh", GRY),
            ("uptime", s.get("uptime", "—"), GRY),
            ("cpu", _cpu_brand(), GRY),
            ("memory", ram, GRY),
            ("bot", bot_val, col),
        ]
        t = Text()
        for label, value, vcol in rows:
            t.append(f"{label:<9} ", style=f"bold {G}")
            t.append(f"{value}\n", style=vcol)
        return t


class Clock(Static):
    def render(self) -> Text:
        return Text(datetime.now().strftime("%H:%M:%S"), style=f"bold {G}")


# ── panels ────────────────────────────────────────────────────────────────────

class StatusPanel(Static):
    def build(self, d: dict) -> Text:
        t = Text()
        _title(t, "STATUS")
        icon, col = _status_icon(d["bot_status"])
        t.append(f" {icon} bot     ", style=col)
        t.append(d["bot_status"] + "\n", style=col)
        t.append(" $ cost    ", style=GRY)
        t.append(f"${d['cost_usd']:.4f}\n", style=G)
        t.append(" ~ tokens  ", style=GRY)
        t.append(f"{d['tokens']:,}\n", style=G)
        t.append(" ✉ pending ", style=GRY)
        pending = d["pending_drafts"]
        t.append(str(pending) + "\n\n", style=YEL if pending else G)

        _title(t, "SYSTEM")
        s = d["sys"]
        t.append(" cpu  ", style=GRY)
        if s["cpu_pct"] is None:
            t.append("—\n", style=GRY)
        else:
            t.append_text(_bar(s["cpu_pct"]))
            t.append(f"  {s['cpu_pct']:.0f}%\n", style=G)
        t.append(" ram  ", style=GRY)
        if s["ram_used"] is None:
            t.append("—\n", style=GRY)
        else:
            pct = s["ram_used"] / s["ram_total"] * 100
            t.append_text(_bar(pct))
            t.append(f"  {s['ram_used']:.1f}/{s['ram_total']:.0f}GB\n", style=G)

        u = d.get("usage")
        if u:
            t.append("\n")
            _title(t, "CLAUDE")
            t.append(" 5h   ", style=GRY)
            t.append_text(_bar(u["pct"]))
            t.append(f"  {_cu.fmt(u['win_tokens'])}\n", style=G)
            t.append(" day  ", style=GRY)
            t.append(f"{_cu.fmt(u['day_tokens'])} tok\n", style=G2)

        t.append(f"\n ↻ {d['refreshed']}", style=DIM)
        return t


class MessagesPanel(Static):
    def build(self, d: dict) -> Text:
        t = Text()
        _title(t, "MESSAGES")
        if not d["messages"]:
            t.append("  no messages yet", style=GRY)
            return t
        for role, text, ts in d["messages"][-8:]:
            try:
                stamp = datetime.fromtimestamp(ts).strftime("%H:%M")
            except (TypeError, ValueError, OSError):
                stamp = "--:--"
            t.append(f" [{stamp}] ", style=DIM)
            is_user = role in (ROLE_KEY, USER_NAME)
            t.append("▶ euan " if is_user else "◀ nzt  ",
                     style=f"bold {G if is_user else G2}")
            snippet = text[:64].replace("\n", " ").strip()
            if len(text) > 64:
                snippet += "…"
            t.append(snippet + "\n", style=G2 if is_user else GRY)
        return t


STAGE_ORDER = ["cold", "contacted", "interested", "proposal", "won", "lost"]


class PipelinePanel(Static):
    def build(self, d: dict) -> Text:
        t = Text()
        fin = d.get("fin", {})
        _title(t, "PIPELINE")
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

        stages = {k: v for k, v in (fin.get("stages") or {}).items() if v}
        if stages:
            t.append("\n─ STAGES ─\n", style=f"bold {G}")
            mx = max(stages.values())
            for name in STAGE_ORDER:
                if name not in stages:
                    continue
                n = stages[name]
                bar = "█" * max(1, round(n / mx * 8)) if n else "·"
                t.append(f"{name:>10} ", style=GRY)
                t.append(f"{bar} ", style=G if name == "won" else G2)
                t.append(f"{n}\n", style=GRY)

        if outstanding:
            t.append("\n─ OUTSTANDING ─\n", style=f"bold {YEL}")
            for inv in outstanding[:3]:
                t.append(f" {inv.get('client', '?')[:12]:<12} ", style=GRY)
                t.append(f"€{inv.get('amount', 0)} d{inv.get('days', 0)}\n", style=YEL)
        return t


STATUS_PILL = {"done": (G, "done"), "failed": (RED, "fail"), "running": (YEL, "run ")}


class TasksPanel(Static):
    def build(self, d: dict) -> Text:
        t = Text()
        _title(t, "TASKS")
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
        _title(t, "ALERTS TODAY")
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
        Binding("q", "quit",    "Quit",        show=True),
        Binding("r", "refresh", "Refresh",     show=True),
        Binding("b", "restart", "Restart bot", show=True),
    ]

    def compose(self) -> ComposeResult:
        with Horizontal(id="header"):
            yield Clock(id="clock")
            yield LogoPanel(id="logo")
            yield SysInfo(id="sysinfo")
        with Horizontal(id="top-row"):
            yield StatusPanel(id="status-panel", classes="panel")
            yield MessagesPanel(id="messages-panel", classes="panel")
            yield PipelinePanel(id="pipeline-panel", classes="panel")
        with Horizontal(id="bottom-row"):
            yield TasksPanel(id="tasks-panel", classes="panel")
            yield AlertsPanel(id="alerts-panel", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        if _HAS_PSUTIL:
            psutil.cpu_percent(interval=None)  # prime the counter
        self._refresh_data()
        self.set_interval(10, self._refresh_data)
        self.set_interval(1, self._tick_clock)

    def _tick_clock(self) -> None:
        # clock only — never touches the database
        self.query_one("#clock", Clock).refresh()

    def _refresh_data(self) -> None:
        try:
            d = _gather()
        except Exception as e:
            self.notify(f"refresh error: {e}", severity="error")
            return
        self.query_one("#sysinfo", SysInfo).update(
            self.query_one("#sysinfo", SysInfo).build(d))
        for wid, cls in (("#status-panel", StatusPanel),
                         ("#messages-panel", MessagesPanel),
                         ("#pipeline-panel", PipelinePanel),
                         ("#tasks-panel", TasksPanel),
                         ("#alerts-panel", AlertsPanel)):
            w = self.query_one(wid, cls)
            w.update(w.build(d))

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
