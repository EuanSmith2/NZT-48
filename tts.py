"""ElevenLabs TTS — REST API only, no SDK (Ponytail rule #4: requests is
already installed). Key + voice live in private/*.yml (voice.elevenlabs)."""
import tempfile

import requests

from config import ELEVEN_API_KEY, ELEVEN_VOICE_ID

API = "https://api.elevenlabs.io/v1/text-to-speech"
MAX_CHARS = 2500  # free-tier credit guard — a brief is ~1.5k chars


def available() -> bool:
    return bool(ELEVEN_API_KEY and ELEVEN_VOICE_ID)


def speak(text: str) -> str:
    """Text → mp3 file path. Raises RuntimeError with a plain cause."""
    if not available():
        raise RuntimeError("ElevenLabs not configured — set voice.elevenlabs "
                           "api_key + voice_id in private/local.yml")
    r = requests.post(
        f"{API}/{ELEVEN_VOICE_ID}",
        headers={"xi-api-key": ELEVEN_API_KEY, "Accept": "audio/mpeg"},
        json={"text": text[:MAX_CHARS], "model_id": "eleven_multilingual_v2",
              "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
        timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"elevenlabs {r.status_code}: {r.text[:150]}")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(r.content)
        return f.name
