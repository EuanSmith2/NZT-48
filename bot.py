"""NZT-48 Telegram bot — long polling, router dispatch, approval gates.
Run: .venv/bin/python bot.py   (or via launchd, see SETUP.md)"""
import asyncio
import json
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

import agents
import cc_client
import finance
import local_client
import memory
import router
import state
from config import TELEGRAM_TOKEN, TELEGRAM_USER_ID, USER_NAME

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # suppress token-bearing URLs
log = logging.getLogger("nzt-48")


def authed(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == TELEGRAM_USER_ID


async def send(update: Update, text: str, markup=None):
    for i in range(0, len(text), 3900):  # telegram 4096 limit
        await update.effective_chat.send_message(
            text[i:i + 3900], reply_markup=markup if i + 3900 >= len(text) else None)


def generalist_reply(message: str, context: str, tier: str) -> str:
    return cc_client.run(f"{context}\n\n{USER_NAME}: {message}",
                         system=agents.assemble("generalist"),
                         model="sonnet", allowed_tools="Read,Glob,Grep",
                         max_turns=6, timeout=180)


def local_reply(message: str, context: str) -> str | None:
    try:
        raw = local_client.generate(f"{context}\n\n{USER_NAME}: {message}", max_tokens=400)
        try:  # nzt-lite escalation protocol (K.10)
            j = json.loads(raw)
            if isinstance(j, dict) and j.get("escalate"):
                return None
        except (json.JSONDecodeError, ValueError):
            pass
        return raw
    except RuntimeError:
        return None


async def handle_envelope(update: Update, env: dict):
    lines = [env.get("response_md") or ""]
    applied, gated = agents.apply_writes(env.get("vault_writes"))
    for a in applied:
        lines.append(f"✅ vault: {a}")
    if env.get("status") == "escalate" and env.get("escalate"):
        esc = env["escalate"]
        lines.append(f"⚠️ needs you: {esc.get('reason', '')} — {esc.get('needs', '')}")
    na = env.get("next_action")
    if na:
        lines.append(f"\n▶️ next: {na}")
    await send(update, "\n".join(filter(None, lines)))

    if env.get("status") == "needs_approval" and not gated:
        # draft (email/DM) approval — content is the response itself
        did = state.save_draft("draft", env.get("response_md", ""), {})
        await send(update, "approve this draft?", markup=_gate_markup(did))
    for w in gated:
        did = state.save_draft("vault_write", _describe_write(w), {"write": w})
        await send(update, f"📝 vault change needs approval:\n{_describe_write(w)}",
                   markup=_gate_markup(did))


def _describe_write(w: dict) -> str:
    return f"{w.get('mode')} → {w.get('path')}\n---\n{w.get('content', '')[:800]}"


def _gate_markup(draft_id: int):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"d:{draft_id}:ok"),
        InlineKeyboardButton("✏️ Rework", callback_data=f"d:{draft_id}:rework"),
        InlineKeyboardButton("🗑 Drop", callback_data=f"d:{draft_id}:drop"),
    ]])


async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not authed(update):
        return
    q = update.callback_query
    await q.answer()
    _, did, action = q.data.split(":")
    draft = state.get_draft(int(did))
    if not draft or draft["status"] != "pending":
        await q.edit_message_text("(expired)")
        return
    if action == "ok":
        if draft["kind"] == "vault_write":
            try:
                result = agents.apply_gated(draft["payload"]["write"])
                memory.log_line(f"approved write: {draft['payload']['write']['path']}")
                await q.edit_message_text(f"✅ {result}")
            except (ValueError, OSError) as e:
                await q.edit_message_text(f"⚠️ failed: {e}")
        else:
            await q.edit_message_text(f"✅ final — copy below:\n\n{draft['content']}")
        state.set_draft_status(int(did), "approved")
    elif action == "rework":
        state.set_draft_status(int(did), "rework")
        state.kv_set("rework_draft", did)
        await q.edit_message_text("what should change? (next message = revision notes)")
    else:
        state.set_draft_status(int(did), "dropped")
        await q.edit_message_text("🗑 dropped")


async def dispatch(update: Update, message: str, route: dict):
    await update.effective_chat.send_action(ChatAction.TYPING)
    tier, agent = route["tier"], route["agent"]
    context = memory.build_context(tier, message, route["intent"])
    state.add_message("euan", message)

    if route["intent"] == "CLARIFY":
        a, b = (route["candidates"] + ["CHAT", "CAPTURE"])[:2]
        reply = f"two ways to take that — ({a.lower()}) or ({b.lower()})? one word."
    elif route.get("queue"):
        # score 5 / TASK: too heavy for headless — flag to interactive Claude Code
        reply = cc_client.queue_task(message, route["reason"])
    elif agent:
        status = await update.effective_chat.send_message(f"🔎 on it — {agent} agent (claude code)")
        try:
            env = await asyncio.to_thread(agents.run, agent, message, context, tier)
        except RuntimeError as e:
            env = {"status": "error", "vault_writes": [], "next_action": None,
                   "escalate": None,
                   "response_md": cc_client.queue_task(message, f"headless failed: {e}")}
        try:
            await status.delete()
        except Exception:
            pass
        state.add_message("nzt-48", env.get("response_md", "")[:1000])
        await handle_envelope(update, env)
        return
    else:
        reply = None
        if tier == "local":
            reply = await asyncio.to_thread(local_reply, message, context)
            if reply is None:  # escalated or local failed → Claude Code (A.7)
                tier = "cc"
                context = memory.build_context(tier, message, route["intent"])
        if reply is None:
            try:
                reply = await asyncio.to_thread(generalist_reply, message, context, tier)
            except RuntimeError as e:
                reply = cc_client.queue_task(message, f"headless failed: {e}")

    state.add_message("nzt-48", reply[:1000])
    await send(update, reply)


async def on_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not authed(update):
        return
    import voice
    await update.effective_chat.send_action(ChatAction.TYPING)
    await voice.handle(update, ctx)


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not authed(update):
        return
    message = update.message.text.strip()

    rework_id = state.kv_get("rework_draft")
    if rework_id:
        state.kv_set("rework_draft", "")
        if rework_id:
            draft = state.get_draft(int(rework_id))
            if draft and draft["status"] == "rework":
                message = (f"Rework this draft per the notes.\nDRAFT:\n{draft['content']}"
                           f"\nNOTES: {message}")
                route = router.classify(message, is_command=True, command="lead") \
                    if draft["kind"] == "draft" else router.classify(message)
                await dispatch(update, message, route)
                return

    route = await asyncio.to_thread(router.classify, message)
    await dispatch(update, message, route)


def make_command(cmd: str):
    async def handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not authed(update):
            return
        args = " ".join(ctx.args) if ctx.args else ""
        if cmd == "new":
            state.clear_session()
            await send(update, "fresh session.")
            return
        if cmd == "cost":
            await send(update, f"runs on Claude Code subscription + local Gemma — "
                               f"€0 marginal. API fallback spend, 7d: "
                               f"${state.week_cost_usd():.2f}")
            return
        if cmd == "check":
            await update.effective_chat.send_action(ChatAction.TYPING)
            action = await asyncio.to_thread(finance.one_action)
            await send(update, f"▶️ {action}")
            return
        if cmd == "pipeline" and not args:
            f = await asyncio.to_thread(finance.compute)
            stages = " · ".join(f"{k}:{v}" for k, v in f["stages"].items()) or "empty"
            await send(update,
                       f"pipeline: {stages}\n€{f['income_received']} in · "
                       f"{f['clients_needed']} clients needed, {f['weeks_left']} wks\n"
                       f"calls: {f['calls_this_week']}/{f['weekly_call_target']} this week · "
                       f"value €{f['pipeline_value']}")
            return
        message = args or cmd
        route = router.classify(message, is_command=True, command=cmd)
        await dispatch(update, message, route)
    return handler


def main():
    if not TELEGRAM_TOKEN or not TELEGRAM_USER_ID:
        raise SystemExit("Set TELEGRAM_TOKEN and TELEGRAM_USER_ID in your .env file")
    state.init()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    for cmd in router.SLASH_MAP:
        app.add_handler(CommandHandler(cmd, make_command(cmd)))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(
        (filters.VOICE | filters.AUDIO) & filters.ChatType.PRIVATE, on_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    log.info("NZT-48 starting")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
