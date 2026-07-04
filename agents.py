"""Agent dispatch: prompt assembly from shared blocks (K.0), envelope parsing,
vault-write application under the B.4 approval matrix.
Runtime: Claude Code headless (cc_client) — vault CLAUDE.md loads as the
operating manual, read-only tools let agents pull vault files natively."""
import json
import re

import cc_client
import memory
from config import (BRIEF_NEWS_TOPICS, BRIEF_PRIORITY_ORDERING, BUSINESS_OFFER,
                    CC_MAIN, GOAL_HEADLINE, LEARNING_PLATFORMS, PROMPTS,
                    PROTECTED_PREFIXES, USER_BACKGROUND, USER_NAME,
                    USER_PROFILE, USER_WEBSITE, VAULT)

_blocks = None


PRIVATE = PROMPTS.parent / "private"


def _block_file(name: str):
    """private/blocks/ overrides prompts/blocks/ — personal voice wins."""
    for p in (PRIVATE / "blocks" / name, PROMPTS / "blocks" / name):
        if p.exists():
            return p
    return PROMPTS / "blocks" / name


def blocks() -> dict:
    global _blocks
    if _blocks is None:
        _blocks = {
            "{USER_CONTEXT}": _block_file("user_context.txt").read_text(),
            "{VOICE_RULES}": _block_file("voice_rules.txt").read_text(),
            "{ESCALATION_PROTOCOL}": _block_file("escalation.txt").read_text(),
            "{OUTPUT_ENVELOPE}": _block_file("envelope.txt").read_text(),
        }
    return _blocks


def assemble(name: str) -> str:
    # private/ (gitignored, personal) beats the shipped generic prompts
    for path in (PRIVATE / "agents" / f"{name}.txt", PRIVATE / f"{name}.txt",
                 PROMPTS / "agents" / f"{name}.txt", PROMPTS / f"{name}.txt"):
        if path.exists():
            break
    text = path.read_text()
    for k, v in blocks().items():
        text = text.replace(k, v)
    # fill template vars from config — every {PLACEHOLDER} a prompt can use
    fills = {
        "{USER_NAME}": USER_NAME,
        "{USER_PROFILE}": USER_PROFILE,
        "{VAULT_PATH}": str(VAULT),
        "{USER_GOAL}": GOAL_HEADLINE or "(no headline goal set)",
        "{USER_BUSINESS}": USER_BACKGROUND or USER_PROFILE,
        "{USER_WEBSITE}": USER_WEBSITE,
        "{BUSINESS_OFFER}": BUSINESS_OFFER or "(business module disabled)",
        "{USER_LEARNING_PLATFORMS}": ", ".join(LEARNING_PLATFORMS) or "(none)",
        "{PRIORITY_ORDERING}": " > ".join(
            p.replace("_", " ").upper() for p in BRIEF_PRIORITY_ORDERING),
        "{NEWS_TOPICS}": ", ".join(BRIEF_NEWS_TOPICS),
        "{EUAN_CONTEXT}": "",  # safety: clear any missed legacy refs
    }
    for k, v in fills.items():
        text = text.replace(k, v)
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
        extra: str = "", untrusted: bool = False, persona: str = "") -> dict:
    system = f"{persona}\n\n{assemble(agent)}" if persona else assemble(agent)
    search_block = ""
    if agent == "research":
        import brave_search
        search_block = brave_search.search(message)
        untrusted = True  # web snippets are attacker-reachable content (audit C1)
    user = f"{context}\n\n{search_block}\n\n{extra}\n\n{USER_NAME}: {message}".strip()
    raw = cc_client.run(user, system=system, model=CC_MAIN,
                        allowed_tools="Read,Glob,Grep", max_turns=12)
    env = parse_envelope(raw)
    env["agent"] = agent
    env["untrusted"] = untrusted  # provenance: writes from ingested content
    return env


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
    except Exception:
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
