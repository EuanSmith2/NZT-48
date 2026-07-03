"""NZT-48 config — loads .env + config.yml. Single source of truth."""
import os
import shutil as _shutil
from pathlib import Path

import yaml
from dotenv import load_dotenv

NZT = Path(__file__).resolve().parent
load_dotenv(NZT / ".env")

# launchd/cron start with a bare PATH — homebrew tools (markitdown, ffmpeg)
# and ~/.local/bin (claude) must be findable from any entrypoint
_extra = f"/opt/homebrew/bin:{Path.home()}/.local/bin"
if "/opt/homebrew/bin" not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{_extra}:{os.environ.get('PATH', '/usr/bin:/bin')}"


def _load_cfg() -> dict:
    p = NZT / "config.yml"
    if p.exists():
        with open(p) as f:
            return yaml.safe_load(f) or {}
    return {}


_cfg = _load_cfg()
_user = _cfg.get("user", {})
_mon = _cfg.get("monitoring", {})

# user identity
USER_NAME = _user.get("name", "User")
BRIEF_TIME = _user.get("brief_time", "09:00")
USER_PROFILE = _user.get("profile", "freelancer")

# vault
VAULT = Path(os.path.expanduser(_user.get("vault", "~/Documents/Notes")))

# paths
STATE_DB = NZT / "state.db"
LOGS = NZT / "logs"
PROMPTS = NZT / "prompts"

# models
MODEL_LOCAL = "nzt-lite"
MODEL_CHEAP = "claude-haiku-4-5-20251001"
MODEL_MAIN = "claude-sonnet-4-6"
MODEL_DEEP = "claude-opus-4-8"

# runtimes
OLLAMA_URL = "http://localhost:11434"
CLAUDE_BIN = _shutil.which("claude") or str(Path.home() / ".local/bin/claude")

# secrets
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID") or "0")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp-mail.outlook.com")
SMTP_PORT = int(os.getenv("SMTP_PORT") or "587")
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

# token budgets
BUDGET = {"local": 800, "cc": 3000, "sonnet": 3000, "fable": 6000}
HOT_CAPS = {"hot_cache": 600, "priorities": 300}
WARM_MAX_FILES = 3
WARM_TOKEN_CEILING = 4000
SESSION_TURNS = 10
SESSION_TOKEN_CAP = 1200

# pricing per 1M tokens (USD) for cost logging
PRICING = {
    MODEL_CHEAP: (1.0, 5.0),
    MODEL_MAIN: (3.0, 15.0),
    MODEL_DEEP: (15.0, 75.0),
}

# vault hot files — read every request for context
HOT_FILES = {
    "hot_cache": VAULT / "00-META/HOT-CACHE.md",
    "priorities": VAULT / "00-META/PRIORITIES.md",
}

# claude usage bar (TUI) — reads the LOCAL logged-in account's ~/.claude only
_claude = _cfg.get("claude", {})
CLAUDE_USAGE = _claude.get("usage", "auto")            # auto | off
CLAUDE_WINDOW_BUDGET = int(_claude.get("window_budget_tokens", 500_000))

# monitoring
MON_ENABLED = _mon.get("enabled", True)
MON_INTERVAL = _mon.get("interval_minutes", 30)
MON_START = _mon.get("window_start", "08:00")
MON_END = _mon.get("window_end", "20:30")
MON_MAX_PER_DAY = _mon.get("max_per_day", 2)


def est_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def truncate_tokens(text: str, cap: int) -> str:
    if est_tokens(text) <= cap:
        return text
    return text[: cap * 4] + "\n[...truncated]"
