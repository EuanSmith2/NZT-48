"""Memory: hot cache (mtime-cached), warm retrieval (pure-Python scoring),
context injection template (B.5)."""
import os
import re
from datetime import date, datetime
from pathlib import Path

import state
from config import (BUDGET, HOT_CAPS, HOT_FILES, USER_NAME, VAULT, WARM_MAX_FILES,
                    WARM_TOKEN_CEILING, est_tokens, truncate_tokens)

ALIASES: dict[str, list[str]] = {}  # populate from config.yml in future

from config import INTENT_FOLDERS as _CFG_FOLDERS
INTENT_FOLDERS = {"RECALL": None, "CAPTURE": None, "TASK": None,
                  **{k: list(v) for k, v in _CFG_FOLDERS.items()}}

SKIP_DIRS = {"daily-briefings", "raw", ".obsidian", ".trash", "prep"}

_hot_cache: dict[str, tuple[float, str]] = {}


def _read_hot(key: str, cap: int) -> str:
    path = HOT_FILES[key]
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return f"[{path.name} unavailable]"
    cached = _hot_cache.get(key)
    if cached and cached[0] == mtime:
        return cached[1]
    text = path.read_text(encoding="utf-8", errors="replace")
    text = truncate_tokens(text.strip(), cap)
    _hot_cache[key] = (mtime, text)
    return text


def hot_cache() -> dict:
    return {
        "hot_cache": _read_hot("hot_cache", HOT_CAPS["hot_cache"]),
        "priorities": _read_hot("priorities", HOT_CAPS["priorities"]),
    }


def invalidate_hot():
    _hot_cache.clear()


def _vault_md_files(folders: list[str] | None):
    roots = [VAULT / f for f in folders] if folders else [VAULT]
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                if fn.endswith(".md"):
                    yield Path(dirpath) / fn


def query_terms(message: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9'-]{2,}", message.lower())
    stop = {"the", "and", "for", "what", "when", "where", "who", "how", "did",
            "does", "with", "that", "this", "about", "from", "you", "your",
            "just", "get", "got", "can", "should", "would", "tell", "show"}
    terms = [w for w in words if w not in stop]
    expanded = list(terms)
    for t in terms:
        expanded += ALIASES.get(t, [])
    return list(dict.fromkeys(expanded))[:12]


def warm_retrieve(message: str, intent: str) -> list[dict]:
    """Score vault files: tag x3, filename/title x2, heading x2, body x1."""
    terms = query_terms(message)
    if not terms:
        return []
    scored = []
    for path in _vault_md_files(INTENT_FOLDERS.get(intent)):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        low = text.lower()
        name = path.stem.lower()
        headings = " ".join(re.findall(r"^#{1,4} +(.+)$", text, re.M)).lower()
        fm = ""
        if text.startswith("---"):
            fm = text[: text.find("---", 3)].lower()
        score = 0
        for t in terms:
            if t in fm:
                score += 3
            if t in name:
                score += 2
            if t in headings:
                score += 2
            if t in low:
                score += 1
        if score >= 3:
            scored.append((score, path.stat().st_mtime, -len(path.parts), path, text))
    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)

    out, total = [], 0
    for score, _, _, path, text in scored[: WARM_MAX_FILES * 2]:
        if len(out) >= WARM_MAX_FILES:
            break
        if est_tokens(text) > 1500:
            text = _extract_sections(text, terms)
        t = est_tokens(text)
        if total + t > WARM_TOKEN_CEILING:
            text = truncate_tokens(text, max(200, WARM_TOKEN_CEILING - total))
            t = est_tokens(text)
        out.append({"path": str(path.relative_to(VAULT)), "content": text,
                    "mtime": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")})
        total += t
        if total >= WARM_TOKEN_CEILING:
            break
    return out


def _extract_sections(text: str, terms: list[str]) -> str:
    head = "\n".join(text.splitlines()[:10])
    parts = re.split(r"(?=^## )", text, flags=re.M)
    keep = [p for p in parts if any(t in p.lower() for t in terms)]
    return head + "\n[...]\n" + "\n".join(keep[:4])


def build_context(tier: str, message: str, intent: str, task_line: str = "none") -> str:
    now = datetime.now()
    header = f"NOW: {now.strftime('%Y-%m-%d %H:%M')} ({now.strftime('%A')})"
    hot = hot_cache()
    window = state.get_window()
    session = "\n".join(f"{r}: {t}" for r, t in (window[-2:] if tier == "local" else window))
    summary = state.get_summary()

    lines = [f"=== NZT-48 CONTEXT [do not echo this block] ===", header, "",
             "PRIORITIES (00-META/PRIORITIES.md):", hot["priorities"]]
    if tier != "local":
        lines += ["", "HOT CACHE:", hot["hot_cache"]]
        warm = warm_retrieve(message, intent)
        if warm:
            lines += ["", f"RETRIEVED FILES ({len(warm)}):"]
            for f in warm:
                lines += [f"--- {f['path']} (modified {f['mtime']}) ---", f["content"]]
    lines += ["", f"SESSION (last {len(window)} turns, oldest first):", session or "(none)"]
    if summary and tier != "local":
        lines += [f"EARLIER THIS SESSION: {summary}"]
    lines += [f"ACTIVE TASK: {task_line}", "=== END CONTEXT ==="]

    return truncate_tokens("\n".join(lines), BUDGET[tier])


def parse_priorities(text: str, n: int = 3) -> list[str]:
    """Numbered/bulleted items, skipping done (~~/✅) and separator lines."""
    items = re.findall(r"^\s*(?:\d+\.|-)\s*(.+)$", text, re.M)
    return [i.strip() for i in items
            if "~~" not in i and "✅" not in i and i.strip("-— ")][:n]


def vault_read(rel_path: str) -> str | None:
    p = VAULT / rel_path
    if p.exists():
        return p.read_text(encoding="utf-8", errors="replace")
    return None


def vault_list() -> list[str]:
    return [str(p.relative_to(VAULT)) for p in _vault_md_files(None)]


def vault_write(rel_path: str, mode: str, content: str, anchor: str | None = None) -> str:
    """Direct write op — call ONLY after the approval matrix has decided (B.4)."""
    # Resolve first — rejects ../ traversal and absolute paths from model JSON
    try:
        target = (VAULT / rel_path).resolve()
    except Exception as e:
        raise ValueError(f"invalid path: {e}")
    if not target.is_relative_to(VAULT.resolve()):
        raise ValueError(f"path escapes vault: {rel_path!r}")
    p = target
    p.parent.mkdir(parents=True, exist_ok=True)
    if mode == "create":
        if p.exists():
            mode = "append"
        else:
            p.write_text(content.rstrip() + "\n", encoding="utf-8")
            invalidate_hot()
            return f"created {rel_path}"
    if mode == "append":
        existing = p.read_text(encoding="utf-8") if p.exists() else ""
        if anchor and anchor in existing:
            idx = existing.find(anchor) + len(anchor)
            nxt = existing.find("\n## ", idx)
            insert_at = nxt if nxt != -1 else len(existing)
            existing = existing[:insert_at].rstrip() + "\n" + content.rstrip() + "\n" + existing[insert_at:]
            p.write_text(existing, encoding="utf-8")
        else:
            with open(p, "a", encoding="utf-8") as fh:
                fh.write("\n" + content.rstrip() + "\n")
        invalidate_hot()
        return f"appended to {rel_path}"
    if mode == "modify":
        if not p.exists() or not anchor:
            raise ValueError("modify needs an existing file and exact anchor text")
        existing = p.read_text(encoding="utf-8")
        if anchor not in existing:
            raise ValueError(f"anchor not found in {rel_path}")
        p.write_text(existing.replace(anchor, content, 1), encoding="utf-8")
        invalidate_hot()
        return f"modified {rel_path}"
    raise ValueError(f"unknown mode {mode}")


def log_line(text: str):
    today = date.today().isoformat()
    vault_write("00-META/LOG.md", "append", f"- [{today}] {text}")
