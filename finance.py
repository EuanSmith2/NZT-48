"""Pipeline parsing + J.2 maths + the I.9 ONE ACTION decision tree."""
import math
import re
from datetime import date, datetime, timedelta

import memory
from config import BIZ_ASSUMPTIONS, BUSINESS_ENABLED, PIPELINE_FILE, VAULT

PIPELINE = PIPELINE_FILE


def _snapshot_and_text():
    text = memory.vault_read(PIPELINE) or ""
    snap = dict(re.findall(r"^(\w+):\s*([^\s<]+)", _section(text, "Snapshot"), re.M))
    return snap, text


def _section(text: str, name: str) -> str:
    m = re.search(rf"## {name}\n(.*?)(?=\n## |\Z)", text, re.S)
    return m.group(1) if m else ""


def _table_rows(section_text: str) -> list[list[str]]:
    rows = []
    for line in section_text.splitlines():
        if line.startswith("|") and "---" not in line:
            cells = [c.strip() for c in line.strip("|").split("|")]
            rows.append(cells)
    return rows[1:] if rows else []  # drop header


def assumptions(text: str) -> dict:
    sec = _section(text, "Assumptions")
    vals = dict(re.findall(r"^(\w+):\s*([\d.]+)", sec, re.M))
    d = BIZ_ASSUMPTIONS  # config defaults; vault Assumptions section wins
    return {
        "c2c": float(vals.get("call_to_conversation", d.get("call_to_conversation", 0.40))),
        "c2p": float(vals.get("conversation_to_proposal", d.get("conversation_to_proposal", 0.25))),
        "p2w": float(vals.get("proposal_to_won", d.get("proposal_to_won", 0.40))),
        "avg_deal": float(vals.get("avg_deal_eur", d.get("avg_deal_eur", 500))),
    }


def calls_this_week(text: str) -> int:
    monday = date.today() - timedelta(days=date.today().weekday())
    n = 0
    for line in _section(text, "Activity Log").splitlines():
        m = re.match(r"- \[(\d{4}-\d{2}-\d{2})[^\]]*\]\s*(call|cold call)", line, re.I)
        if m and date.fromisoformat(m.group(1)) >= monday:
            n += 1
    return n


EMPTY = {"clients_needed": 0, "weeks_left": 0, "calls_needed": 0,
         "weekly_call_target": 0, "calls_this_week": 0, "pipeline_value": 0,
         "stages": {}, "untouched_a": [], "outstanding": [],
         "income_received": 0, "call_to_client": 0, "mrr": 0}


def compute() -> dict:
    if not BUSINESS_ENABLED:
        return dict(EMPTY)
    snap, text = _snapshot_and_text()
    a = assumptions(text)
    target = int(snap.get("target_clients", 3))
    won = int(snap.get("clients_won", 1))
    deadline = date.fromisoformat(snap.get("deadline", "2026-09-01"))
    weeks_left = max(1, round((deadline - date.today()).days / 7))
    call_to_client = a["c2c"] * a["c2p"] * a["p2w"]
    needed = max(0, target - won)
    calls_needed = math.ceil(needed / call_to_client) if needed else 0
    prospects = _table_rows(_section(text, "Prospects"))
    stage_rate = {"contacted": 0.10, "interested": 0.25, "proposal": 0.40}
    pipeline_value = 0.0
    stages: dict[str, int] = {}
    untouched_a = []
    for row in prospects:
        if len(row) < 12:
            continue
        status = row[10].lower()
        stages[status] = stages.get(status, 0) + 1
        pipeline_value += stage_rate.get(status, 0) * a["avg_deal"]
        if row[6].upper() == "A" and status == "cold":
            untouched_a.append({"name": row[0], "phone": row[3], "area": row[2],
                                "notes": row[11]})
    outstanding = []
    for row in _table_rows(_section(text, "Income Outstanding")):
        if len(row) >= 5 and row[4].lower() == "awaiting":
            sent = date.fromisoformat(row[2]) if re.match(r"\d{4}-", row[2]) else None
            outstanding.append({"client": row[0], "amount": row[1], "sent": sent,
                                "days": (date.today() - sent).days if sent else 0})
    return {
        "clients_needed": needed, "weeks_left": weeks_left,
        "calls_needed": calls_needed,
        "weekly_call_target": math.ceil(calls_needed / weeks_left) if needed else 0,
        "calls_this_week": calls_this_week(text),
        "pipeline_value": round(pipeline_value),
        "stages": stages, "untouched_a": untouched_a,
        "outstanding": outstanding,
        "income_received": snap.get("income_received_eur", "?"),
        "call_to_client": call_to_client,
        "mrr": int(float(snap.get("mrr_eur", 0) or 0)),
    }


MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def _month_name_date(text: str) -> date | None:
    """Parse 'Jul 7' / 'July 7' style; assumes current year, rolls to next."""
    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})\b",
                  text, re.I)
    if not m:
        return None
    try:
        d = date(date.today().year, MONTHS[m.group(1).lower()[:3]], int(m.group(2)))
    except ValueError:
        return None
    return d.replace(year=d.year + 1) if (d - date.today()).days < -300 else d


def events_within(days: int) -> list[dict]:
    """Dated items from 08-EVENTS files + dated lines in PRIORITIES.md (E.1)."""
    out = []
    events_dir = VAULT / "08-EVENTS"
    for p in events_dir.glob("*.md") if events_dir.exists() else []:
        text = p.read_text(encoding="utf-8", errors="replace")[:2000]
        m = re.search(r"^date:\s*(\d{4}-\d{2}-\d{2})", text, re.M) or \
            re.search(r"\*\*Date:?\*\*:?\s*(\d{4}-\d{2}-\d{2})", text) or \
            re.search(r"(\d{4}-\d{2}-\d{2})", text)
        d = None
        if m:
            try:
                d = date.fromisoformat(m.group(1))
            except ValueError:
                pass
        d = d or _month_name_date(text[:600])
        if d and 0 <= (d - date.today()).days <= days:
            out.append({"name": p.stem, "date": d, "days": (d - date.today()).days})
    pri = memory.vault_read("00-META/PRIORITIES.md") or ""
    for line in memory.parse_priorities(pri, n=10):
        d = _month_name_date(line) or None
        if not d:
            m = re.search(r"(\d{4}-\d{2}-\d{2})", line)
            if m:
                try:
                    d = date.fromisoformat(m.group(1))
                except ValueError:
                    d = None
        if d and 0 <= (d - date.today()).days <= days:
            name = re.sub(r"[*_`]", "", line)[:50].strip()
            out.append({"name": name, "date": d, "days": (d - date.today()).days})
    seen, dedup = set(), []
    for e in sorted(out, key=lambda e: e["days"]):
        if e["name"] not in seen:
            seen.add(e["name"])
            dedup.append(e)
    return dedup


def one_action() -> str:
    """I.9 decision tree — first match wins, exactly one action."""
    f = compute()
    # 1. payment overdue >=7d
    for o in f["outstanding"]:
        if o["days"] >= 7:
            return (f"Send the follow-up to {o['client']} — {o['amount']}, day {o['days']}. "
                    f"Money owed beats everything else on the list.")
    # 2. deadline <=48h
    ev = events_within(2)
    if ev:
        return (f"{ev[0]['name']} is in {ev[0]['days']} day(s). Close out its open "
                f"actions today — nothing else matters if this slips.")
    # 3. behind on calls
    if f["clients_needed"] > 0 and f["calls_this_week"] < f["weekly_call_target"]:
        if f["untouched_a"]:
            lead = f["untouched_a"][0]
            return (f"Call {lead['name']} ({lead['area']}) at 10:00 — {lead['phone']}. "
                    f"{f['clients_needed']} clients needed in {f['weeks_left']} weeks; "
                    f"{f['calls_this_week']}/{f['weekly_call_target']} calls this week.")
        return (f"No scored leads left to call. Run a lead scrape today — "
                f"you need {f['weekly_call_target']} calls/week and the queue is empty.")
    # 4. event within 7d lacking prep
    for e in events_within(7):
        if not list((VAULT / "08-EVENTS/prep").glob(f"{e['name']}*")):
            return f"/prep {e['name']} — it's in {e['days']} days and there's no prep file."
    # 5/6. fall through to priorities
    items = memory.parse_priorities(memory.hot_cache()["priorities"], n=1)
    return items[0] if items else "Vault priorities are empty — set them."
