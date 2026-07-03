"""Router: Stage-1 deterministic rules, Stage-2 model classification (A.4),
tier + agent dispatch decision (A.3)."""
import json
import re

import local_client
from config import PROMPTS

SLASH_MAP = {
    "brief": ("BRIEF", 3, "briefing"),
    "research": ("RESEARCH", 3, "research"),
    "task": ("TASK", 4, "task"),
    "remember": ("CAPTURE", 3, "memory"),
    "recall": ("RECALL", 2, "memory"),
    "lead": ("BUSINESS", 3, "business"),
    "prep": ("PREP", 3, "pre-call"),
    "study": ("LEARNING", 3, "learning"),
    "pipeline": ("BUSINESS", 3, "business"),
    "check": ("BRIEF", 3, "briefing"),
    "new": ("SYSTEM", 1, None),
    "cost": ("SYSTEM", 1, None),
}

AGENT_FOR_INTENT = {
    "RECALL": "memory", "CAPTURE": "memory", "RESEARCH": "research",
    "TASK": "task", "BUSINESS": "business", "LEARNING": "learning",
    "BRIEF": "briefing", "PREP": "pre-call",
    "CHAT": None, "SYSTEM": None,
}

STAGE1_RULES = [
    (re.compile(r"^(just got off|just off|just finished|spoke to|talked to|met with)\b", re.I),
     ("CAPTURE", 3)),
    (re.compile(r"^(remember|note:|log:|save this)\b", re.I), ("CAPTURE", 3)),
    (re.compile(r"^(what should i do|what's next|what now)\b", re.I), ("BRIEF", 3)),
]

_router_prompt = None


def _system() -> str:
    global _router_prompt
    if _router_prompt is None:
        _router_prompt = (PROMPTS / "router.txt").read_text()
    return _router_prompt


def _finish(intent: str, score: int, confidence: float, reason: str,
            agent_override=None, candidates=None) -> dict:
    score = max(1, min(5, score))
    agent = agent_override if agent_override is not None else AGENT_FOR_INTENT.get(intent)
    # All traffic routes through Claude Code (subscription, zero marginal cost).
    # Local tier disabled: gemma4:12b (7.6GB) is too heavy for 16GB machines.
    # Re-enable by swapping tier assignment if you pull a <=4B local model.
    tier = "cc"
    # score 5 / TASK = too heavy for headless → interactive Claude Code queue
    queue = score >= 5 or intent == "TASK"
    return {"intent": intent, "score": score, "confidence": confidence,
            "tier": tier, "agent": agent, "reason": reason,
            "queue": queue, "candidates": candidates or []}


def classify(message: str, is_command: bool = False, command: str = "") -> dict:
    # Stage 1: slash commands
    if is_command and command in SLASH_MAP:
        intent, score, agent = SLASH_MAP[command]
        return _finish(intent, score, 1.0, f"/{command}", agent_override=agent)

    # Stage 1: regex rules
    for rx, (intent, score) in STAGE1_RULES:
        if rx.search(message):
            return _finish(intent, score, 0.95, "stage-1 rule")
    if re.search(r"https?://\S+", message):
        intent = "CAPTURE" if re.search(r"\b(save|remember|note|keep)\b", message, re.I) else "RESEARCH"
        return _finish(intent, 3, 0.9, "url rule")

    # Stage 1.5: short conversational messages have no classifiable intent —
    # skip Stage 2 entirely and send straight to CHAT to save one cc cold-start.
    INTENT_KEYWORDS = re.compile(
        r"\b(research|find|look up|search|remind|remember|note|save|log|task|"
        r"brief|study|learn|lead|pipeline|prep|call|meeting|price|cost|"
        r"schedule|plan|write|draft|email|message|dm)\b", re.I)
    if len(message.split()) <= 8 and not INTENT_KEYWORDS.search(message):
        return _finish("CHAT", 1, 0.9, "short-message fast-path")

    # Stage 2: classify via cc haiku (subscription, zero marginal cost).
    # Local classifier disabled — gemma4:12b too heavy for 16GB machines.
    result = None
    try:
        import cc_client
        raw = cc_client.run(f"Message: {message}", system=_system(),
                            model="haiku", allowed_tools="", max_turns=1,
                            timeout=60)
        m = re.search(r"\{.*\}", raw, re.S)
        result = json.loads(m.group(0)) if m else None
    except Exception:
        result = None
    if result is None:
        return _finish("CHAT", 3, 0.5, "classifier unavailable — defaulting to cc chat")

    intent = str(result.get("intent", "CHAT")).upper()
    if intent == "CLARIFY" or float(result.get("confidence", 0)) < 0.6:
        cands = result.get("candidates") or ["CHAT", "CAPTURE"]
        return _finish("CLARIFY", 1, 0.5, result.get("reason", ""), candidates=cands[:2])
    if intent not in AGENT_FOR_INTENT:
        intent = "CHAT"
    score = int(result.get("score", 3))
    return _finish(intent, score, float(result.get("confidence", 0.7)),
                   result.get("reason", "stage-2"))
