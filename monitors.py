"""Proactive intelligence layer (E). Cron: */30 8-20 * * *.
Hard ceiling: 2 proactive messages/day. Suppressed alerts roll into the brief."""
import re
import time
from datetime import date, datetime, timedelta

import finance
import memory
import notify
import state
from config import MON_MAX_PER_DAY, VAULT


def _today_sent(con) -> int:
    midnight = datetime.combine(date.today(), datetime.min.time()).timestamp()
    return con.execute(
        "SELECT COUNT(*) FROM alerts WHERE sent=1 AND ts>?", (midnight,)
    ).fetchone()[0]


def _already(con, monitor: str, key: str, cooldown_s: float) -> bool:
    row = con.execute(
        "SELECT MAX(ts) FROM alerts WHERE monitor=? AND key=? AND sent=1",
        (monitor, key),
    ).fetchone()
    return bool(row[0] and time.time() - row[0] < cooldown_s)


def _record(con, monitor: str, key: str, sent: int):
    con.execute("INSERT INTO alerts(monitor, key, ts, sent) VALUES(?,?,?,?)",
                (monitor, key, time.time(), sent))


# --- monitors: each returns (priority, key, message) or None ---

def deadline_monitor(con):
    for ev in finance.events_within(14):
        for threshold, label in ((2, "48h"), (7, "7d"), (14, "14d")):
            if ev["days"] <= threshold:
                dkey = f"{ev['name']}:{label}"
                hit = con.execute(
                    "SELECT 1 FROM events_sent WHERE deadline_key=? AND threshold=?",
                    (ev["name"], label)).fetchone()
                if not hit:
                    con.execute("INSERT INTO events_sent VALUES(?,?)", (ev["name"], label))
                    prio = 1 if threshold == 2 else 4
                    return (prio, dkey,
                            f"⏳ {ev['name']} is in {ev['days']} day(s) "
                            f"({ev['date']}). /prep {ev['name']} if you haven't.")
                break  # only the tightest un-sent threshold
    return None


def cold_call_nudge(con):
    now = datetime.now()
    if now.weekday() == 6 or not (9 <= now.hour < 11 or (now.hour == 11 and now.minute == 0)):
        return None
    if _already(con, "coldcall", "nudge", 48 * 3600):
        return None
    text = memory.vault_read("09-FINANCE/web-business-pipeline.md") or ""
    m = re.findall(r"- \[(\d{4}-\d{2}-\d{2})[^\]]*\]\s*(call|email|dm)", text, re.I)
    last = max((date.fromisoformat(d) for d, _ in m), default=None)
    if last and (date.today() - last).days < 2:
        return None
    f = finance.compute()
    # second consecutive nudge with no activity between → blocker question (E.2)
    prev = con.execute(
        "SELECT MAX(ts) FROM alerts WHERE monitor='coldcall' AND sent=1").fetchone()[0]
    second = bool(prev and (not last or last < date.fromtimestamp(prev)))
    if f["untouched_a"]:
        lead = f["untouched_a"][0]
        if second:
            msg = (f"Two nudges, zero dials. Straight question: what would make you "
                   f"call {lead['name']} at 10 tomorrow? Reply with the real blocker — "
                   f"script, fear, lead quality — and we fix that instead.")
        else:
            msg = (f"📞 {lead['name']} ({lead['area']}) — no website, {lead['phone']}. "
                   f"It's {now.strftime('%H:%M')}. One call before lunch: this one. "
                   f"/prep {lead['name'].split()[0].lower()} for the opening line.")
    else:
        msg = (f"📞 No outreach in 48h and the lead queue is empty. "
               f"{f['weekly_call_target']} calls/week is the target — "
               f"say 'find leads' and I'll build today's list.")
    return (2, "nudge", msg)


def payment_monitor(con):
    for o in finance.compute()["outstanding"]:
        if o["days"] >= 7 and not _already(con, "payment", o["client"], 5 * 86400):
            first = o["client"].split()[0]
            return (3, o["client"],
                    f"💶 {o['client']} — day {o['days']}, no reply on the {o['amount']}. "
                    f"Ready to send:\n\n\"Hi {first}, hope the staff meeting went well. "
                    f"Just checking in on the invoice from the automation work — no rush "
                    f"if it's in the pipeline, just want to make sure it didn't get "
                    f"buried. Payment details are in the original email.\"")
    return None


def lead_freshness(con):
    text = memory.vault_read("09-FINANCE/web-business-pipeline.md") or ""
    sec = re.search(r"## Prospects\n(.*?)(?=\n## |\Z)", text, re.S)
    if not sec:
        return None
    best = None
    for line in sec.group(1).splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 12 or cells[10].lower() not in ("contacted", "interested", "proposal"):
            continue
        m = re.match(r"\d{4}-\d{2}-\d{2}", cells[7])
        if not m:
            continue
        days = (date.today() - date.fromisoformat(m.group(0))).days
        if days >= 5 and not _already(con, "freshness", cells[0], 5 * 86400):
            score = int(cells[5]) if cells[5].isdigit() else 0
            if best is None or score > best[0]:
                best = (score, cells[0], days, cells[8], cells[11])
    if best:
        _, name, days, ctype, notes = best
        return (5, name, f"🕳 {name} has gone quiet — {days}d since {ctype}. "
                         f"({notes}). Next move: one-line follow-up, no pressure.")
    return None


def learning_streak(con):
    if datetime.now().hour < 20:
        return None
    if _already(con, "streak", date.today().isoformat(), 20 * 3600):
        return None
    text = memory.vault_read("06-LEARNING/platform-progress.md") or ""
    if date.today().isoformat() in text:
        return None
    return (6, date.today().isoformat(),
            "🧠 Nothing logged today — check your learning tracker and log progress.")


def run():
    state.init()
    fired = []
    with state.db() as con:
        for mon, fn in (("deadline", deadline_monitor), ("coldcall", cold_call_nudge),
                        ("payment", payment_monitor), ("freshness", lead_freshness),
                        ("streak", learning_streak)):
            try:
                r = fn(con)
                if r:
                    fired.append((r[0], mon, r[1], r[2]))
            except Exception as e:
                print(f"[monitor {mon}] error: {e}")
        fired.sort()
        budget = MON_MAX_PER_DAY - _today_sent(con)
        for prio, mon, key, msg in fired:
            sent = 1 if budget > 0 and notify.send(msg) else 0
            budget -= sent
            _record(con, mon, key, sent)  # unsent rows roll into the brief


if __name__ == "__main__":
    run()
