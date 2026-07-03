"""Claude Code subscription usage — parsed from the LOCAL logged-in account's
transcript files (~/.claude/projects/**/*.jsonl).

Privacy model: this auto-links to whoever is logged into Claude Code on THIS
machine and never anyone else — there is no account ID, no network call, and
nothing configured per-person. Set `claude.usage: off` in config.yml to
disable entirely; `claude.window_budget_tokens` calibrates the bar to your
plan's feel (limits aren't published, so the bar is a burn-rate gauge, not an
official quota).
"""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from config import CLAUDE_USAGE, CLAUDE_WINDOW_BUDGET

CLAUDE_DIR = Path.home() / ".claude/projects"
WINDOW_S = 5 * 3600
_cache: dict = {"ts": 0.0, "data": None}
CACHE_S = 60  # parsing transcripts is I/O — don't do it every dashboard tick


def _parse_ts(s: str) -> float:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return 0.0


def gather() -> dict | None:
    """{'win_tokens', 'day_tokens', 'pct'} or None when off/unavailable."""
    if CLAUDE_USAGE == "off" or not CLAUDE_DIR.exists():
        return None
    now = time.time()
    if _cache["data"] is not None and now - _cache["ts"] < CACHE_S:
        return _cache["data"]

    midnight = datetime.now().replace(hour=0, minute=0, second=0,
                                      microsecond=0).timestamp()
    win_cut = now - WINDOW_S
    win = day = 0
    try:
        for fp in CLAUDE_DIR.glob("*/*.jsonl"):
            try:
                if fp.stat().st_mtime < midnight:
                    continue  # untouched today — nothing in window either
                with open(fp, errors="replace") as f:
                    for line in f:
                        if '"usage"' not in line:
                            continue
                        try:
                            j = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        u = (j.get("message") or {}).get("usage") or {}
                        if not u:
                            continue
                        ts = _parse_ts(j.get("timestamp", ""))
                        if ts < midnight:
                            continue
                        # output weighs ~5x input on every published price sheet;
                        # cache reads are nearly free — weight accordingly
                        tok = (u.get("input_tokens", 0)
                               + 5 * u.get("output_tokens", 0)
                               + u.get("cache_creation_input_tokens", 0)
                               + u.get("cache_read_input_tokens", 0) // 10)
                        day += tok
                        if ts >= win_cut:
                            win += tok
            except OSError:
                continue
    except OSError:
        return None

    data = {"win_tokens": win, "day_tokens": day,
            "pct": min(100.0, win / CLAUDE_WINDOW_BUDGET * 100)}
    _cache.update(ts=now, data=data)
    return data


def fmt(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1e6:.1f}M"
    if n >= 1_000:
        return f"{n / 1e3:.0f}k"
    return str(n)


if __name__ == "__main__":
    print(gather())
