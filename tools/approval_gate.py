"""Approval gate for external (Composio) actions — the non-negotiable layer.

Reuses the existing drafts machinery rather than inventing a parallel gate:
stage() saves the staged action as a pending draft (kind="action"), the
transport shows preview_text with the same ✅/✏️/🗑 buttons as vault writes
and emails, and the user's tap lands in run() — which executes only if the
draft is still pending AND younger than TTL_S. "Waiting for the yes" is
event-driven (Telegram callback / 'approve <id>' text), not a blocking poll,
so the bot never freezes on an unanswered gate.

Outcomes land in the drafts table: approved | dropped (the no — this IS the
declined log) | expired (>5 min) | failed (app error). memory.log_line
mirrors approvals into the vault LOG like approved vault writes.
"""
import time

import state

TTL_S = 300  # 5 min — a stale "send this email?" must never fire hours later


def stage(staged: dict) -> int:
    """Persist a staged write action; returns the draft id the buttons carry.

    Example:
        staged = composio_tools.outlook_send_email(to, subject, body)
        did = approval_gate.stage(staged)   # → show gate markup for did
    """
    return state.save_draft("action", staged.get("preview_text", ""), staged)


def run(draft_id: int, draft: dict) -> str:
    """Execute an approved action draft. Sets the draft's final status itself
    (approved/expired/failed) — callers just display the returned line."""
    from tools import composio_tools
    if time.time() - float(draft.get("ts") or 0) > TTL_S:
        state.set_draft_status(draft_id, "expired")
        return "⏱ expired (no answer within 5 min) — ask again to re-stage"
    try:
        result = composio_tools.execute_staged(draft["payload"])
    except composio_tools.ComposioNotConfigured as e:
        state.set_draft_status(draft_id, "failed")
        return f"⚠️ {e}"
    except (composio_tools.ComposioError, TypeError, KeyError) as e:
        state.set_draft_status(draft_id, "failed")
        return f"⚠️ action failed: {e}"
    state.set_draft_status(draft_id, "approved")
    import memory
    memory.log_line(f"approved action: {draft['payload'].get('action', '?')}")
    return f"✅ {result}"
