"""Voice pipeline: Telegram voice note → whisper (base) → transcript echoed
→ router dispatch. The transcript is shown ("🎙 heard: …") before the routed
reply so a mishear is visible immediately; protected vault writes still go
through the approval gate regardless.

Whisper resolution order (no blind pip installs):
1. An existing whisper env at ~/.claude/mcp_servers/whisper-env/ (subprocess —
   keeps torch out of the bot process)
2. `import whisper` in this venv, if the user installed it
3. Neither → clear error telling the user what to install
"""
import subprocess
import tempfile
from pathlib import Path

import state
from config import LOCALE

WHISPER_ENV_PY = Path.home() / ".claude/mcp_servers/whisper-env/bin/python3"
MAX_VOICE_MB = 20

_SNIPPET = """
import sys, whisper
model = whisper.load_model("base")
result = model.transcribe(sys.argv[1], language=sys.argv[2], fp16=False)
print(result["text"].strip())
"""


def _transcribe_subprocess(audio_path: str, timeout: int) -> str:
    r = subprocess.run([str(WHISPER_ENV_PY), "-c", _SNIPPET, audio_path, LOCALE],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"whisper failed: {r.stderr.strip()[-200:]}")
    return r.stdout.strip()


def _transcribe_inprocess(audio_path: str) -> str:
    try:
        import whisper  # optional dep — see requirements.txt
    except ImportError:
        raise RuntimeError(
            "no whisper available — run: .venv/bin/pip install openai-whisper "
            "(and `brew install ffmpeg` if missing)")
    model = whisper.load_model("base")
    return model.transcribe(audio_path, language=LOCALE, fp16=False)["text"].strip()


def transcribe(audio_path: str, timeout: int = 180) -> str:
    """Blocking transcription. Holds the single-backend lock — whisper on CPU
    must never stack with local Gemma inference (fanless-machine rule)."""
    if not state.acquire_lock("whisper", wait_s=30):
        raise RuntimeError("backend busy — try again in a minute")
    try:
        if WHISPER_ENV_PY.exists():
            text = _transcribe_subprocess(audio_path, timeout)
        else:
            text = _transcribe_inprocess(audio_path)
        return text
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"transcription timed out after {timeout}s")
    finally:
        state.release_lock("whisper")


async def handle(update, ctx):
    """Full voice flow. Caller (bot.on_voice) has already checked authed()."""
    import asyncio
    from bot import dispatch, send  # runtime import — bot is loaded by now
    import router

    media = update.message.voice or update.message.audio
    if media.file_size and media.file_size > MAX_VOICE_MB * 1024 * 1024:
        await send(update, f"voice note too big (>{MAX_VOICE_MB}MB)")
        return
    with tempfile.NamedTemporaryFile(suffix=".oga", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        f = await media.get_file()
        await f.download_to_drive(tmp_path)
        try:
            text = await asyncio.to_thread(transcribe, tmp_path)
        except RuntimeError as e:
            await send(update, f"⚠️ transcription failed: {e}")
            return
        if not text:
            await send(update, "couldn't catch that, try again")
            return
        await send(update, f"🎙 heard: {text}")
        route = await asyncio.to_thread(router.classify, text)
        await dispatch(update, text, route)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
