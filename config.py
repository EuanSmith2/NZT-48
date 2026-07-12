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


def _deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _load_cfg() -> dict:
    """config.yml, then any private/*.yml deep-merged on top. private/ is
    gitignored — the real, personal config lives there; config.yml stays
    shippable placeholders."""
    cfg = {}
    p = NZT / "config.yml"
    if p.exists():
        with open(p) as f:
            cfg = yaml.safe_load(f) or {}
    for priv in sorted((NZT / "private").glob("*.yml")):
        with open(priv) as f:
            cfg = _deep_merge(cfg, yaml.safe_load(f) or {})
    return cfg


_cfg = _load_cfg()
_user = _cfg.get("user", {})
_mon = _cfg.get("monitoring", {})
_goals = _cfg.get("goals", {})
_brief = _cfg.get("brief", {})
_modules = _cfg.get("modules", {})
_biz = _modules.get("business", {})
_learn = _modules.get("learning", {})
_vault = _cfg.get("vault", {})
_models = _cfg.get("models", {})
_local = _models.get("local", {})
_cloud = _models.get("cloud", {})

# user identity
USER_NAME = _user.get("name", "User")
ROLE_KEY = _user.get("role_key", (USER_NAME.split()[0] if USER_NAME else "user").lower())
USER_PROFILE = _user.get("profile", "freelancer")
USER_BACKGROUND = _user.get("background", "")
USER_WEBSITE = _user.get("website", "")
LOCALE = _user.get("locale", "en")
TIMEZONE = _user.get("timezone", "")

# goals
GOAL_HEADLINE = _goals.get("headline", "")
GOAL_DEADLINE = str(_goals.get("deadline", ""))

# brief
BRIEF_TIME = _brief.get("time", _user.get("brief_time", "09:00"))
BRIEF_PRIORITY_ORDERING = _brief.get("priority_ordering",
                                     ["cash_collection", "cold_outreach", "skills_study"])
BRIEF_NEWS_TOPICS = _brief.get("news_topics",
                               ["cybersecurity vulnerability news",
                                "technology business news",
                                "AI tools productivity"])

# modules — OPTIONAL domains. business.enabled=false switches off the entire
# freelance layer (pipeline, cold-call nudge, payment monitor); the engine
# must not assume every human is a Dublin freelancer chasing invoices.
BUSINESS_ENABLED = bool(_biz.get("enabled", True))
BUSINESS_OFFER = _biz.get("offer", "")
PIPELINE_FILE = _biz.get("pipeline_file", "09-FINANCE/web-business-pipeline.md")
LEAD_SCORING = _biz.get("lead_scoring", {
    "no_website": 40, "social_only_recent": 20, "phone_accessible": 15,
    "recent_reviews": 15, "local_to_area": 10, "vertical_match": 5,
    "franchise": -25})
LEAD_TIERS = _biz.get("tiers", {"A": 70, "B": 45})
BIZ_ASSUMPTIONS = _biz.get("assumptions", {})

LEARNING_ENABLED = bool(_learn.get("enabled", True))
LEARNING_PLATFORMS = _learn.get("platforms", [])
LEARNING_PROGRESS_FILE = _learn.get("progress_file", "06-LEARNING/platform-progress.md")

# vault
VAULT = Path(os.path.expanduser(_vault.get("path", _user.get("vault", "~/Documents/Notes"))))
PROTECTED_PREFIXES = tuple(_vault.get("protected_prefixes",
                                      ["03-PEOPLE/", "01-PROFILE/", "02-GOALS/",
                                       # always-injected context files — a silent
                                       # append here is persistent prompt poisoning
                                       "00-META/HOT-CACHE.md",
                                       "00-META/PRIORITIES.md"]))
INTENT_FOLDERS = _vault.get("intent_folders", {
    "BUSINESS": ["04-PROJECTS", "09-FINANCE"],
    "PREP": ["03-PEOPLE", "08-EVENTS", "04-PROJECTS"],
    "LEARNING": ["06-LEARNING"],
    "RESEARCH": ["05-KNOWLEDGE"]})

# paths
STATE_DB = NZT / "state.db"
LOGS = NZT / "logs"
PROMPTS = NZT / "prompts"

# models / tiers
LOCAL_ENABLED = bool(_local.get("enabled", False))
MODEL_LOCAL = _local.get("model", "nzt-lite")
LOCAL_MAX_SHORT_SCORE = int(_local.get("max_short_score", 1))

# /devils — dual-opinion advisor (diplomat via cc, machiavelli via local Ollama)
DEVILS_ADVOCATE_ENABLED = True
MODEL_DEVILS = "machiavelli"
CC_MAIN = _cloud.get("main", "sonnet")     # claude -p model aliases
CC_CHEAP = _cloud.get("cheap", "haiku")
MODEL_CHEAP = "claude-haiku-4-5-20251001"  # API-fallback ids (claude_client)
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
_hot = _vault.get("hot_files", {})
HOT_FILES = {
    "hot_cache": VAULT / _hot.get("hot_cache", "00-META/HOT-CACHE.md"),
    "priorities": VAULT / _hot.get("priorities", "00-META/PRIORITIES.md"),
}

# voice out (ElevenLabs TTS) — keys live in private/*.yml, never in git
_voice = _cfg.get("voice", {}).get("elevenlabs", {})
ELEVEN_API_KEY = _voice.get("api_key", "") or os.getenv("ELEVENLABS_API_KEY", "")
ELEVEN_VOICE_ID = _voice.get("voice_id", "") or os.getenv("ELEVENLABS_VOICE_ID", "")

# browser agent backend: skyvern (vision, unknown sites) | playwright | chrome
_browser = _cfg.get("browser", {})
BROWSER_BACKEND = _browser.get("backend", "playwright")
# MCP tool prefixes per backend — what cc_client passes as --allowedTools
BROWSER_TOOLS = _browser.get("tools", {
    "playwright": "mcp__playwright__*",
    "skyvern": "mcp__skyvern__*",
    "chrome": "mcp__claude-chrome__*",
})

# integrations (Canva MCP, Composio connect-apps) — off unless configured
_integrations = _cfg.get("integrations", {})
CANVA_ENABLED = bool(_integrations.get("canva", {}).get("enabled", False))
_composio = _integrations.get("composio", {})
COMPOSIO_ENABLED = bool(_composio.get("enabled", False))
# key sources, first wins: top-level composio_api_key (private/*.yml),
# integrations.composio.api_key, env. Never hardcode — private/ only.
COMPOSIO_API_KEY = (_cfg.get("composio_api_key", "")
                    or _composio.get("api_key", "")
                    or os.getenv("COMPOSIO_API_KEY", ""))
COMPOSIO_ENTITY = _composio.get("entity_id", "default")
COMPOSIO_DEFAULT_REPO = _composio.get("default_repo", "")      # owner/repo
COMPOSIO_NOTION_DB = _composio.get("notion_database_id", "")
COMPOSIO_CALENDAR_ID = _composio.get("calendar_id", "primary")

# transports
_transports = _cfg.get("transports", {})
WHATSAPP = _transports.get("whatsapp", {})  # enabled, token, phone_id, verify_token

# claude usage bar (TUI) — reads the LOCAL logged-in account's ~/.claude only
_claude = _cfg.get("claude", {})
CLAUDE_USAGE = _claude.get("usage", "auto")            # auto | off
CLAUDE_WINDOW_BUDGET = int(_claude.get("window_budget_tokens", 500_000))

# monitoring
MON_ENABLED = _mon.get("enabled", True)
MON_INTERVAL = _mon.get("interval_minutes", 30)
_mon_win = _mon.get("window", {})  # both `window: {start,end}` and flat keys
MON_START = _mon.get("window_start", _mon_win.get("start", "08:00"))
MON_END = _mon.get("window_end", _mon_win.get("end", "20:30"))
MON_MAX_PER_DAY = _mon.get("max_per_day", 2)


def est_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def truncate_tokens(text: str, cap: int) -> str:
    if est_tokens(text) <= cap:
        return text
    return text[: cap * 4] + "\n[...truncated]"
