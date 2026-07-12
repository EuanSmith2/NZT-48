"""Transport abstraction — adding a platform is ONE new file in transports/.

A transport does exactly two things:
  1. deliver inbound user text to `handle_message(text, send)`
  2. implement `send(text)` so replies (and gate prompts) go back out

Everything else — routing, tiers, agents, memory, the approval matrix — is
shared and lives behind `handle_message`. Rich approval UI (inline buttons)
is a Telegram luxury; text-only transports gate with "approve <id>" replies,
handled here by `maybe_handle_approval`.

Telegram predates this module and keeps its own richer loop in telegram.py
(buttons, voice, documents, photos). New transports (whatsapp today,
iMessage later via AppleScript) build on this instead.
"""
from abc import ABC, abstractmethod
from typing import Callable

import agents
import cc_client
import memory
import personas
import router
import state
from config import ROLE_KEY, USER_NAME

Send = Callable[[str], None]


class Transport(ABC):
    name = "base"

    @abstractmethod
    def send(self, text: str) -> None:
        """Deliver one outbound message to the user."""

    @abstractmethod
    def run(self) -> None:
        """Blocking receive loop; call handle_message per inbound text."""


def _describe_write(w: dict) -> str:
    return f"{w.get('mode')} → {w.get('path')}\n---\n{w.get('content', '')[:500]}"


def maybe_handle_approval(message: str, send: Send) -> bool:
    """Text-gate protocol: 'approve 12' / 'drop 12'. True if consumed."""
    parts = message.strip().lower().split()
    if len(parts) != 2 or parts[0] not in ("approve", "drop") or not parts[1].isdigit():
        return False
    draft = state.get_draft(int(parts[1]))
    if not draft or draft["status"] != "pending":
        send("(no pending draft with that id)")
        return True
    if parts[0] == "drop":
        state.set_draft_status(int(parts[1]), "dropped")
        send("🗑 dropped")
        return True
    if draft["kind"] == "vault_write":
        try:
            send(f"✅ {agents.apply_gated(draft['payload']['write'])}")
        except (ValueError, OSError) as e:
            send(f"⚠️ failed: {e}")
    elif draft["kind"] == "email":
        import emailer
        p = draft["payload"]
        send(f"✅ email {emailer.send(p.get('to',''), p.get('subject',''), p.get('body',''))}")
    else:
        send(f"✅ final — copy below:\n\n{draft['content']}")
    state.set_draft_status(int(parts[1]), "approved")
    return True


def handle_message(message: str, send: Send, untrusted: bool = False) -> None:
    """Platform-neutral dispatch. Blocking — run in the transport's worker."""
    if maybe_handle_approval(message, send):
        return
    route = router.classify(message)
    tier, agent = route["tier"], route["agent"]
    context = memory.build_context(tier, message, route["intent"])
    state.add_message(ROLE_KEY, message)
    persona = personas.take()
    if persona and tier == "local":
        tier = "cc"

    if route.get("queue"):
        reply = cc_client.queue_task(message, route["reason"])
    elif route["intent"] == "DEVILS":
        import devils_advocate
        reply = devils_advocate.run(message, context)
    elif agent:
        try:
            env = agents.run(agent, message, context, tier, "", untrusted, persona)
        except RuntimeError as e:
            env = {"response_md": cc_client.queue_task(message, f"headless failed: {e}"),
                   "vault_writes": [], "status": "error"}
        lines = [env.get("response_md") or ""]
        applied, gated = agents.apply_writes(env.get("vault_writes"),
                                             bool(env.get("untrusted")) or untrusted)
        lines += [f"✅ vault: {a}" for a in applied]
        if env.get("next_action"):
            lines.append(f"▶️ next: {env['next_action']}")
        reply = "\n".join(filter(None, lines))
        for w in gated:
            did = state.save_draft("vault_write", _describe_write(w), {"write": w})
            reply += (f"\n\n📝 gated write #{did}:\n{_describe_write(w)}\n"
                      f"reply 'approve {did}' or 'drop {did}'")
    else:
        from transports.telegram import generalist_reply, local_reply
        reply = None
        if tier == "local":
            reply = local_reply(message, context)
        if reply is None:
            try:
                reply = generalist_reply(message, context, "cc", persona)
            except RuntimeError as e:
                reply = cc_client.queue_task(message, f"headless failed: {e}")

    state.add_message("nzt-48", reply[:1000])
    send(reply)
