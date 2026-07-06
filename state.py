"""SQLite state: messages, session summary, tasks, alerts, locks, drafts, cost."""
import json
import sqlite3
import time
from contextlib import contextmanager

from config import STATE_DB, SESSION_TURNS, est_tokens

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY, ts REAL, role TEXT, text TEXT, tokens INT);
CREATE TABLE IF NOT EXISTS session_summary(
  id INTEGER PRIMARY KEY CHECK (id=1), upto_msg_id INT, text TEXT);
CREATE TABLE IF NOT EXISTS tasks(
  id INTEGER PRIMARY KEY, agent TEXT, title TEXT, plan_json TEXT,
  cursor INT DEFAULT 0, status TEXT DEFAULT 'running', updated REAL);
CREATE TABLE IF NOT EXISTS alerts(
  id INTEGER PRIMARY KEY, monitor TEXT, key TEXT, ts REAL, sent INT DEFAULT 0);
CREATE TABLE IF NOT EXISTS locks(name TEXT PRIMARY KEY, holder TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS events_sent(deadline_key TEXT, threshold TEXT,
  PRIMARY KEY(deadline_key, threshold));
CREATE TABLE IF NOT EXISTS drafts(
  id INTEGER PRIMARY KEY, ts REAL, kind TEXT, content TEXT,
  status TEXT DEFAULT 'pending', payload_json TEXT);
CREATE TABLE IF NOT EXISTS cost_log(
  ts REAL, model TEXT, tok_in INT, tok_out INT, usd REAL);
CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT);
"""


@contextmanager
def db():
    con = sqlite3.connect(STATE_DB, timeout=10)
    con.execute("PRAGMA journal_mode=WAL")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init():
    with db() as con:
        con.executescript(SCHEMA)
    # fresh vault (no priorities file) → lay down the scaffold so finance/
    # monitors/briefing never run on empty. Existing vaults are untouched.
    from config import HOT_FILES, VAULT
    if not HOT_FILES["priorities"].exists():
        import scaffold
        scaffold.ensure_vault(VAULT)


def add_message(role: str, text: str):
    with db() as con:
        con.execute(
            "INSERT INTO messages(ts, role, text, tokens) VALUES(?,?,?,?)",
            (time.time(), role, text, est_tokens(text)),
        )


def get_window(max_turns: int = SESSION_TURNS, token_cap: int = 1200):
    with db() as con:
        rows = con.execute(
            "SELECT role, text FROM messages ORDER BY id DESC LIMIT ?", (max_turns,)
        ).fetchall()
    rows.reverse()
    out, total = [], 0
    for role, text in reversed(rows):
        t = est_tokens(text)
        if total + t > token_cap:
            break
        out.insert(0, (role, text))
        total += t
    return out


def clear_session():
    with db() as con:
        con.execute("DELETE FROM messages")
        con.execute("DELETE FROM session_summary")


def get_summary() -> str:
    with db() as con:
        row = con.execute("SELECT text FROM session_summary WHERE id=1").fetchone()
    return row[0] if row else ""


def set_summary(upto: int, text: str):
    with db() as con:
        con.execute(
            "INSERT OR REPLACE INTO session_summary(id, upto_msg_id, text) VALUES(1,?,?)",
            (upto, text),
        )


# --- single-backend lock (A.6-2): one generation backend at a time ---
LOCK_STALE_S = 900  # must exceed the longest cc call (browser agent: 600s)


def acquire_lock(holder: str, wait_s: float = 30) -> bool:
    deadline = time.time() + wait_s
    while time.time() < deadline:
        with db() as con:
            # single atomic statement — the old SELECT-then-INSERT let two
            # processes (bot + monitors cron) both grab the lock
            cur = con.execute(
                "INSERT INTO locks(name, holder, ts) VALUES('backend',?,?) "
                "ON CONFLICT(name) DO UPDATE SET holder=excluded.holder, ts=excluded.ts "
                "WHERE locks.holder=excluded.holder OR excluded.ts - locks.ts > ?",
                (holder, time.time(), LOCK_STALE_S),
            )
            if cur.rowcount:
                return True
        time.sleep(0.5)
    return False


def release_lock(holder: str):
    with db() as con:
        con.execute("DELETE FROM locks WHERE name='backend' AND holder=?", (holder,))


def log_cost(model: str, tok_in: int, tok_out: int, usd: float):
    with db() as con:
        con.execute(
            "INSERT INTO cost_log VALUES(?,?,?,?,?)",
            (time.time(), model, tok_in, tok_out, usd),
        )


def week_cost_usd() -> float:
    with db() as con:
        row = con.execute(
            "SELECT COALESCE(SUM(usd),0) FROM cost_log WHERE ts > ?",
            (time.time() - 7 * 86400,),
        ).fetchone()
    return row[0]


def save_draft(kind: str, content: str, payload: dict) -> int:
    with db() as con:
        cur = con.execute(
            "INSERT INTO drafts(ts, kind, content, payload_json) VALUES(?,?,?,?)",
            (time.time(), kind, content, json.dumps(payload)),
        )
        return cur.lastrowid


def get_draft(draft_id: int):
    with db() as con:
        row = con.execute(
            "SELECT kind, content, payload_json, status, ts FROM drafts WHERE id=?",
            (draft_id,),
        ).fetchone()
    if not row:
        return None
    return {"kind": row[0], "content": row[1], "payload": json.loads(row[2]),
            "status": row[3], "ts": row[4]}


def pending_drafts() -> list[dict]:
    with db() as con:
        rows = con.execute(
            "SELECT id, kind, content FROM drafts WHERE status='pending' ORDER BY id DESC"
        ).fetchall()
    return [{"id": r[0], "kind": r[1], "content": r[2]} for r in rows]


def set_draft_status(draft_id: int, status: str):
    with db() as con:
        con.execute("UPDATE drafts SET status=? WHERE id=?", (status, draft_id))


def kv_get(key: str, default=None):
    with db() as con:
        row = con.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def kv_set(key: str, value: str):
    with db() as con:
        con.execute("INSERT OR REPLACE INTO kv(key, value) VALUES(?,?)", (key, value))
