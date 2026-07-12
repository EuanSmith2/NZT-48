"""/devils — dual-opinion advisor. Runs the same question through the
diplomat (business agent, Claude Code / cc tier) and machiavelli (local
Ollama persona) and returns both, labeled. Text-only: reads neither side's
vault_writes, applies nothing, queues nothing. No side effects beyond a reply.
"""
import agents
import local_client
from config import DEVILS_ADVOCATE_ENABLED, MODEL_DEVILS

DIPLOMAT_LABEL = "🕊 DIPLOMAT"
MACHIAVELLI_LABEL = "🐍 MACHIAVELLI"


def _diplomat(question: str, context: str) -> str:
    env = agents.run("business", question, context, tier="cc")
    return (env.get("response_md") or "").strip()


def _machiavelli(question: str) -> tuple[str | None, str | None]:
    """Returns (response, fail_reason). Exactly one is None."""
    ok, reason = local_client.thermal_ok()
    if not ok:
        return None, reason
    try:
        return local_client.generate(question, model=MODEL_DEVILS, max_tokens=500), None
    except Exception as e:
        return None, str(e)


def run(question: str, context: str) -> str:
    if not DEVILS_ADVOCATE_ENABLED:
        return "devils advocate is off (DEVILS_ADVOCATE_ENABLED in config.py)"

    try:
        diplomat_text = _diplomat(question, context)
        diplomat_fail = None
    except Exception as e:
        diplomat_text, diplomat_fail = None, str(e)

    machiavelli_text, machiavelli_fail = _machiavelli(question)

    parts = []
    if diplomat_text:
        parts.append(f"{DIPLOMAT_LABEL}\n{diplomat_text}")
    else:
        parts.append(f"{DIPLOMAT_LABEL}\n(unavailable: {diplomat_fail})")

    if machiavelli_text:
        parts.append(f"{MACHIAVELLI_LABEL}\n{machiavelli_text}")
    else:
        parts.append(f"{MACHIAVELLI_LABEL}\n(unavailable: {machiavelli_fail})")

    return "\n\n".join(parts)
