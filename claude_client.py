"""Anthropic API wrapper with cost logging and the single-backend lock."""
import anthropic

import state
from config import ANTHROPIC_API_KEY, MODEL_MAIN, PRICING

_client = None


def client():
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY missing — add it to your .env file")
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def complete(user: str, system: str = "", model: str = MODEL_MAIN,
             max_tokens: int = 1200, retries: int = 1) -> str:
    if not state.acquire_lock("claude", wait_s=30):
        raise RuntimeError("backend lock timeout")
    try:
        last_err = None
        for attempt in range(retries + 1):
            try:
                msg = client().messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system or anthropic.NOT_GIVEN,
                    messages=[{"role": "user", "content": user}],
                )
                tok_in = msg.usage.input_tokens
                tok_out = msg.usage.output_tokens
                p_in, p_out = PRICING.get(model, (3.0, 15.0))
                state.log_cost(model, tok_in, tok_out,
                               tok_in / 1e6 * p_in + tok_out / 1e6 * p_out)
                return "".join(b.text for b in msg.content if b.type == "text")
            except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
                last_err = e
                if attempt < retries:
                    import time
                    time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"Claude API failed: {last_err}")
    finally:
        state.release_lock("claude")
