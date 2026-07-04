"""Personas: named injectable system prompts, loaded from the vault
(00-META/personas/*.md) and private/personas/*.md. /persona <name> arms one
for the NEXT dispatch only (one-shot) — it prepends to whatever agent's
system prompt handles that message."""
from pathlib import Path

import state
from config import NZT, VAULT

DIRS = [VAULT / "00-META/personas", NZT / "private/personas"]
KV = "persona_next"


def available() -> dict[str, Path]:
    out: dict[str, Path] = {}
    for d in DIRS:
        if d.exists():
            for p in sorted(d.glob("*.md")):
                out.setdefault(p.stem.lower(), p)
    return out


def load(name: str) -> str | None:
    p = available().get(name.strip().lower())
    return p.read_text(encoding="utf-8", errors="replace") if p else None


def arm(name: str) -> str:
    """Set the persona for the next dispatch. Returns the user-facing reply."""
    if not name:
        names = ", ".join(available()) or "(none found)"
        return f"personas: {names}\nusage: /persona <name>"
    if load(name) is None:
        return f"no persona '{name}'. available: {', '.join(available()) or 'none'}"
    state.kv_set(KV, name.strip().lower())
    return f"🎭 {name} armed — applies to your next message."


def take() -> str:
    """Pop the armed persona text (one-shot). Empty string if none."""
    name = state.kv_get(KV)
    if not name:
        return ""
    state.kv_set(KV, "")
    return load(name) or ""
