"""Agent dispatch: prompt assembly from shared blocks (K.0), envelope parsing,
vault-write application under the B.4 approval matrix.
Runtime: Claude Code headless (cc_client) — vault CLAUDE.md loads as the
operating manual, read-only tools let agents pull vault files natively."""
import json
import re

import cc_client
import memory
from config import PROMPTS, USER_NAME, USER_PROFILE, VAULT

_blocks = None


def blocks() -> dict:
    global _blocks
    if _blocks is None:
        b = PROMPTS / "blocks"
        _blocks = {
            "{USER_CONTEXT}": (b / "user_context.txt").read_text(),
            "{VOICE_RULES}": (b / "voice_rules.txt").read_text(),
            "{ESCALATION_PROTOCOL}": (b / "escalation.txt").read_text(),
            "{OUTPUT_ENVELOPE}": (b / "envelope.txt").read_text(),
        }
    return _blocks


def assemble(name: str) -> str:
    path = PROMPTS / "agents" / f"{name}.txt"
    if not path.exists():
        path = PROMPTS / f"{name}.txt"
    text = path.read_text()
    for k, v in blocks().items():
        text = text.replace(k, v)
    # fill template vars from config
    text = text.replace("{USER_NAME}", USER_NAME)
    text = text.replace("{USER_PROFILE}", USER_PROFILE)
    text = text.replace("{VAULT_PATH}", str(VAULT))
    text = text.replace("{EUAN_CONTEXT}", "")  # safety: clear any missed refs
    return text


def parse_envelope(raw: str) -> dict:
    """Tolerant envelope parse: find the outermost JSON object; fall back to
    treating the whole reply as response_md."""
    m = re.search(r"\{.*\}", raw, re.S)
    if m:
        try:
            env = json.loads(m.group(0))
            if "response_md" in env:
                env.setdefault("status", "ok")
                env.setdefault("vault_writes", [])
                env.setdefault("next_action", None)
                env.setdefault("escalate", None)
                return env
        except json.JSONDecodeError:
            pass
    return {"status": "ok", "response_md": raw.strip(), "vault_writes": [],
            "next_action": None, "escalate": None}


def run(agent: str, message: str, context: str, tier: str = "cc",
        extra: str = "", untrusted: bool = False) -> dict:
    system = assemble(agent)
    search_block = ""
    if agent == "research":
        import brave_search
        search_block = brave_search.search(message)
    user = f"{context}\n\n{search_block}\n\n{extra}\n\n{USER_NAME}: {message}".strip()
    raw = cc_client.run(user, system=system, model="sonnet",
                        allowed_tools="Read,Glob,Grep", max_turns=12)
    env = parse_envelope(raw)
    env["agent"] = agent
    env["untrusted"] = untrusted  # provenance: writes from ingested content
    return env


PROTECTED_PREFIXES = ("03-PEOPLE/", "01-PROFILE/", "02-GOALS/")


def needs_gate(write: dict) -> bool:
    """B.4 approval matrix. Normalise the path first so ../ tricks can't bypass
    protected prefix checks — the actual write will also be blocked by
    vault_write's resolve() guard, but we gate here too as defence-in-depth."""
    if write.get("mode") == "modify":
        return True
    try:
        import os
        from config import VAULT
        normalised = str((VAULT / write.get("path", "")).resolve()
                         .relative_to(VAULT.resolve())).replace(os.sep, "/")
    except (ValueError, Exception):
        return True  # can't normalise → treat as gated
    return normalised.startswith(PROTECTED_PREFIXES)


def apply_writes(writes: list[dict],
                 untrusted: bool = False) -> tuple[list[str], list[dict]]:
    """Apply auto-approved writes; return (result lines, gated writes).
    untrusted=True (content ingested from docs/photos/web) forces the gate on
    EVERY write — closes the vault-poisoning path (red-team A5): a poisoned
    document must never silently append attacker text that later re-enters
    context as trusted memory. Costs one extra click, only for external input."""
    applied, gated = [], []
    for w in writes or []:
        if not w.get("path") or not w.get("content"):
            continue
        if untrusted or needs_gate(w):
            gated.append(w)
            continue
        try:
            applied.append(memory.vault_write(
                w["path"], w.get("mode", "append"), w["content"], w.get("anchor")))
        except (ValueError, OSError) as e:
            applied.append(f"⚠️ write failed ({w['path']}): {e}")
    return applied, gated


def apply_gated(write: dict) -> str:
    return memory.vault_write(
        write["path"], write.get("mode", "modify"), write["content"], write.get("anchor"))
