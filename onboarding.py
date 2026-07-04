"""First-run onboarding wizard — 7 Telegram questions → config.yml + vault
scaffold + PRIORITIES.md. Turns NZT-48 from "Euan's bot that others clone"
into a system that personalises itself. State machine lives in kv (same
pattern as rework-draft/CLARIFY); survives restarts mid-wizard.

Trigger: /setup, or automatically on first message when config.yml is absent.
"""
import json
import re
from datetime import date
from pathlib import Path

import state

NZT = Path(__file__).resolve().parent
DEFAULT_VAULT = "~/Documents/NZT-Vault"

QUESTIONS = {
    "Q1": "hey — quick setup, 7 questions. first: what's your name?",
    "Q2": "one line: what do you do? (e.g. freelance web dev / student / developer)",
    "Q3": "your main goal right now + by when? (e.g. '3 clients by September')",
    "Q4": "do you make money through a pipeline of clients/leads worth tracking? (yes/no)",
    "Q5": "studying anything? name the platforms, or say 'no'.",
    "Q6": "what time do you want the morning brief? (e.g. 09:00)",
    "Q7": "3 news topics you care about (comma-separated)",
}
ORDER = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7"]

MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"])}


def active() -> bool:
    step = state.kv_get("onboarding_step")
    return bool(step) and step != "done"


def start() -> str:
    state.kv_set("onboarding_step", "Q1")
    state.kv_set("onboarding_answers", "{}")
    return QUESTIONS["Q1"]


def _profile_of(text: str) -> str:
    low = text.lower()
    if re.search(r"freelanc|client|agency|consult", low):
        return "freelancer"
    if re.search(r"student|study|uni|college|school", low):
        return "student"
    if re.search(r"dev|engineer|program|coder|software", low):
        return "developer"
    return "other"


def _deadline_of(text: str) -> str:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if m:
        return m.group(1)
    low = text.lower()
    for name, num in MONTHS.items():
        if name in low or low.find(name[:3] + " ") != -1:
            year = date.today().year
            if num < date.today().month:
                year += 1
            return f"{year}-{num:02d}-01"
    return str(date.today().replace(year=date.today().year + 1))


def _yes(text: str) -> bool:
    return bool(re.match(r"\s*(y|yes|yeah|yep|si|sì|ja)\b", text.lower()))


def build_config(a: dict) -> dict:
    name = a.get("Q1", "User").strip().split("\n")[0][:40]
    platforms = [] if a.get("Q5", "no").strip().lower() in ("no", "nope", "n") \
        else [p.strip() for p in re.split(r"[,;/]| and ", a["Q5"]) if p.strip()]
    time_m = re.search(r"\d{1,2}:\d{2}", a.get("Q6", ""))
    return {
        "user": {
            "name": name,
            "role_key": re.sub(r"[^a-z0-9]", "", name.split()[0].lower()) or "user",
            "profile": _profile_of(a.get("Q2", "")),
            "background": a.get("Q2", "").strip()[:120],
            "locale": "en",
        },
        "goals": {
            "headline": a.get("Q3", "").strip()[:120],
            "deadline": _deadline_of(a.get("Q3", "")),
        },
        "brief": {
            "time": time_m.group(0) if time_m else "09:00",
            "news_topics": [t.strip() for t in a.get("Q7", "").split(",") if t.strip()][:3]
                           or ["technology news"],
        },
        "modules": {
            "business": {"enabled": _yes(a.get("Q4", "no"))},
            "learning": {"enabled": bool(platforms), "platforms": platforms},
        },
        "vault": {"path": DEFAULT_VAULT},
        "models": {"local": {"enabled": False, "model": "nzt-lite",
                             "max_short_score": 1},
                   "cloud": {"main": "sonnet", "cheap": "haiku"}},
        "monitoring": {"enabled": True, "max_per_day": 2},
    }


def _finalise(answers: dict) -> str:
    import yaml
    cfg = build_config(answers)
    (NZT / "config.yml").write_text(
        yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    vault = Path(cfg["vault"]["path"]).expanduser()
    vault.mkdir(parents=True, exist_ok=True)
    meta = vault / "00-META"
    meta.mkdir(parents=True, exist_ok=True)
    pri = meta / "PRIORITIES.md"
    if not pri.exists() or "Set your priorities here" in pri.read_text():
        pri.write_text(f"# Priorities\n\n- {cfg['goals']['headline']}\n"
                       f"- (add the second)\n- (add the third)\n")
    goals_dir = vault / "02-GOALS"
    goals_dir.mkdir(parents=True, exist_ok=True)
    gp = goals_dir / "goals.md"
    if not gp.exists():
        gp.write_text(f"# Goals\n\n## Current\n- {cfg['goals']['headline']} "
                      f"(by {cfg['goals']['deadline']})\n")
    state.kv_set("onboarding_step", "done")
    mods = [m for m, on in (("business", cfg["modules"]["business"]["enabled"]),
                            ("learning", cfg["modules"]["learning"]["enabled"])) if on]
    return (f"done, {cfg['user']['name']}. config written, vault at "
            f"{cfg['vault']['path']} ({'modules: ' + ', '.join(mods) if mods else 'no optional modules'}). "
            f"restarting to load it — say hi in ~10s, or /brief for your first brief.")


def handle_answer(text: str) -> tuple[str, bool]:
    """Consume one answer. Returns (reply, finished). finished=True means the
    caller should restart the process so the new config loads."""
    step = state.kv_get("onboarding_step")
    answers = json.loads(state.kv_get("onboarding_answers") or "{}")
    answers[step] = text.strip()
    state.kv_set("onboarding_answers", json.dumps(answers))
    idx = ORDER.index(step)
    if idx + 1 < len(ORDER):
        nxt = ORDER[idx + 1]
        state.kv_set("onboarding_step", nxt)
        return QUESTIONS[nxt], False
    return _finalise(answers), True
