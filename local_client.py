"""Ollama client + thermal guard (A.6)."""
import json
import subprocess
import time

import requests

import state
from config import MODEL_LOCAL, OLLAMA_URL

_thermal_block_until = 0.0


def thermal_ok() -> tuple[bool, str]:
    """True if it's safe to run local inference. Checks macOS throttle state."""
    global _thermal_block_until
    if time.time() < _thermal_block_until:
        return False, "thermal TTL active"
    try:
        out = subprocess.run(
            ["pmset", "-g", "therm"], capture_output=True, text=True, timeout=5
        ).stdout
        for line in out.splitlines():
            if "CPU_Speed_Limit" in line:
                limit = int(line.split("=")[-1].strip())
                if limit < 100:
                    _thermal_block_until = time.time() + 600  # 10 min TTL
                    return False, f"CPU throttled to {limit}%"
    except Exception:
        pass  # pmset unavailable → don't block on the check itself
    return True, "ok"


def ollama_up() -> bool:
    try:
        requests.get(f"{OLLAMA_URL}/api/ps", timeout=2)
        return True
    except requests.RequestException:
        return False


def generate(prompt: str, system: str | None = None, max_tokens: int = 400,
             json_mode: bool = False, timeout: int = 60) -> str:
    """Blocking local generation. Caller must have decided thermal is OK.
    Raises RuntimeError on failure so the fallback chain (A.7) can act."""
    if not state.acquire_lock("ollama", wait_s=30):
        raise RuntimeError("backend lock timeout")
    try:
        body = {
            "model": MODEL_LOCAL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.4, "num_predict": max_tokens},
        }
        if system:
            body["system"] = system
        if json_mode:
            body["format"] = "json"
        r = requests.post(f"{OLLAMA_URL}/api/generate", json=body, timeout=timeout)
        r.raise_for_status()
        return r.json()["response"].strip()
    finally:
        state.release_lock("ollama")


def classify(prompt: str, system: str) -> dict | None:
    """Strict-JSON classification call. Returns None on any failure."""
    try:
        raw = generate(prompt, system=system, max_tokens=150, json_mode=True, timeout=30)
        return json.loads(raw)
    except Exception:
        return None
