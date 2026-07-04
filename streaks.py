"""Streak tracker — derived entirely from data that already exists (Ponytail
rule 1: nothing new to log). Bot usage from cost_log (append-only, one row per
model call), learning sessions from dated lines in the progress file, outreach
calls from the pipeline Activity Log. A daily snapshot lands in vault
STREAKS.json when the morning brief runs."""
import json
import re
from datetime import date, timedelta

import memory
import state
from config import LEARNING_PROGRESS_FILE, PIPELINE_FILE, VAULT


def _streak(days: set[str]) -> int:
    """Consecutive active days ending today (or yesterday — today isn't over)."""
    d = date.today()
    if d.isoformat() not in days:
        d -= timedelta(days=1)
    n = 0
    while d.isoformat() in days:
        n += 1
        d -= timedelta(days=1)
    return n


def compute() -> dict:
    with state.db() as con:
        rows = con.execute(
            "SELECT DISTINCT date(ts,'unixepoch','localtime') FROM cost_log"
        ).fetchall()
    usage = {r[0] for r in rows}
    learning = set(re.findall(r"\d{4}-\d{2}-\d{2}",
                              memory.vault_read(LEARNING_PROGRESS_FILE) or ""))
    calls = {m.group(1) for m in re.finditer(
        r"- \[(\d{4}-\d{2}-\d{2})[^\]]*\]\s*(?:cold )?call",
        memory.vault_read(PIPELINE_FILE) or "", re.I)}
    return {"usage": _streak(usage), "learning": _streak(learning),
            "calls": _streak(calls)}


def snapshot() -> dict:
    s = compute()
    try:
        (VAULT / "STREAKS.json").write_text(
            json.dumps({"date": date.today().isoformat(), **s}, indent=1))
    except OSError:
        pass  # streaks are derived — a failed snapshot loses nothing
    return s


if __name__ == "__main__":
    print(compute())
