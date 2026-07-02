"""Tier-2 brain: Claude Code headless (`claude -p`) on the subscription.

Why this instead of the raw API: cwd is set to the vault, so vault CLAUDE.md
(the operating manual / Fable-approximation layer) loads automatically, the
model gets read-only tools to pull any vault file the injected context missed,
and it runs on Claude Code usage — €0 marginal cost, no API billing.
ANTHROPIC_API_KEY is stripped from the child env so the CLI can never silently
switch to pay-per-token."""
import json
import os
import shutil
import subprocess

import state
from config import ANTHROPIC_API_KEY, CLAUDE_BIN, VAULT


def available() -> bool:
    return bool(CLAUDE_BIN and shutil.which(CLAUDE_BIN))


def run(prompt: str, system: str = "", model: str = "sonnet",
        allowed_tools: str = "Read,Glob,Grep", max_turns: int = 12,
        timeout: int = 240) -> str:
    """Blocking headless Claude Code call. Raises RuntimeError on failure so
    the caller's fallback chain (A.7) can act."""
    if not available():
        # last-resort fallback: direct API, only if a key was deliberately set
        if ANTHROPIC_API_KEY:
            import claude_client
            return claude_client.complete(prompt, system=system, max_tokens=1500)
        raise RuntimeError("claude CLI not found and no API key configured")

    if not state.acquire_lock("claude", wait_s=30):
        raise RuntimeError("backend lock timeout")
    try:
        cmd = [CLAUDE_BIN, "-p", "--output-format", "json",
               "--model", model, "--max-turns", str(max_turns)]
        if allowed_tools:
            cmd += ["--allowedTools", allowed_tools]
        if system:
            cmd += ["--append-system-prompt", system]
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                           timeout=timeout, cwd=VAULT, env=env)
        if r.returncode != 0:
            raise RuntimeError(f"claude -p exit {r.returncode}: {r.stderr[:300]}")
        data = json.loads(r.stdout)
        if data.get("is_error"):
            raise RuntimeError(f"claude -p error result: {str(data.get('result'))[:300]}")
        state.log_cost(f"cc/{model}", 0, 0, 0.0)  # usage happens on subscription
        return data.get("result", "")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"claude -p timed out after {timeout}s")
    finally:
        state.release_lock("claude")


QUEUE_PATH = "00-META/INBOX/claude-code-queue.md"


def queue_task(message: str, reason: str) -> str:
    """Flag heavy work back to an interactive Claude Code session (the primary
    interface for complex tasks). Returns the reply for Telegram."""
    import memory
    from datetime import datetime
    memory.vault_write(
        QUEUE_PATH, "append",
        f"- [ ] [{datetime.now().strftime('%Y-%m-%d %H:%M')}] {message}  "
        f"<!-- reason: {reason} -->")
    return ("📋 that's a Claude Code job — queued it. Open Claude Code and say "
            "\"queue\" (or it'll surface at session start).")
