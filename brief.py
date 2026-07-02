"""Extended daily brief (I). Cron: 0 9 * * *. Replaces daily-brief/brief.py.
Deterministic data gathering; Sonnet composes when a key exists, otherwise a
clean deterministic fallback — the brief NEVER fails to arrive."""
import re
import time
from datetime import date, datetime, timedelta

import requests

import agents
import finance
import memory
import notify
import state
from config import BRAVE_API_KEY, USER_NAME, VAULT


def weather() -> str:
    try:
        return requests.get("https://wttr.in/?format=3", timeout=8).text.strip()
    except requests.RequestException:
        return ""


def news() -> list[str]:
    if not BRAVE_API_KEY:
        return []
    out = []
    for q in ("cybersecurity vulnerability news", "technology business news",
              "AI tools productivity"):
        try:
            r = requests.get(
                "https://api.search.brave.com/res/v1/news/search",
                params={"q": q, "count": 2, "country": "ie", "freshness": "pd"},
                headers={"X-Subscription-Token": BRAVE_API_KEY}, timeout=10)
            for item in r.json().get("results", [])[:1]:
                out.append(f"{item['title']} ({item.get('meta_url', {}).get('hostname', '')})")
            time.sleep(1.2)  # free tier: 1 req/s
        except Exception:
            continue
    return out


def gap_line() -> str:
    text = memory.vault_read("09-FINANCE/web-business-pipeline.md") or ""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    acts = [l for l in text.splitlines()
            if l.startswith(f"- [{yesterday}") and re.search(r"call|email|dm|proposal", l, re.I)]
    if acts:
        return f"GAP: none — {len(acts)} outreach action(s) yesterday."
    # count consecutive zero-days
    n = 0
    for i in range(1, 30):
        d = (date.today() - timedelta(days=i)).isoformat()
        if any(l.startswith(f"- [{d}") for l in text.splitlines()):
            break
        n = i
    run = f" That's {n} days running." if n > 1 else ""
    return f"GAP: yesterday had no income-generating activity. No calls, no outreach.{run}"


def suppressed() -> list[str]:
    midnight = datetime.combine(date.today(), datetime.min.time()).timestamp()
    with state.db() as con:
        rows = con.execute(
            "SELECT monitor, key FROM alerts WHERE sent=0 AND ts>?",
            (midnight - 86400,)).fetchall()
    return [f"{m}: {k}" for m, k in rows]


def gather() -> dict:
    pri = memory.hot_cache()["priorities"]
    pri_items = memory.parse_priorities(pri)
    f = finance.compute()
    learning = memory.vault_read("06-LEARNING/platform-progress.md") or ""
    pri_mtime_days = 0
    try:
        pri_mtime_days = (time.time() - (VAULT / "00-META/PRIORITIES.md").stat().st_mtime) / 86400
    except OSError:
        pass
    return {
        "date": datetime.now().strftime("%A %b %-d"),
        "weather": weather(),
        "priorities": pri_items,
        "priorities_stale": pri_mtime_days > 7,
        "deadlines": finance.events_within(7),
        "finance": f,
        "learning_head": learning[:800],
        "news": news(),
        "gap": gap_line(),
        "one_action": finance.one_action(),
        "suppressed": suppressed(),
    }


def fallback_compose(d: dict) -> str:
    f = d["finance"]
    lines = [f"{USER_NAME.upper()} — {d['date']} · {d['weather'] or ''}".strip(), ""]
    if d["priorities_stale"]:
        lines.append("⚠️ priorities file is stale — still true?")
    lines.append("TODAY:")
    lines += [f"• {p}" for p in d["priorities"]] or ["• (priorities empty)"]
    lines.append("\nDEADLINES:")
    lines += [f"• {e['name']} — {e['days']}d ({e['date']})" for e in d["deadlines"]] or ["• none tracked"]
    stages = " · ".join(f"{k}:{v}" for k, v in f["stages"].items()) or "empty"
    lines += ["\nPIPELINE:", f"• {stages} · value €{f['pipeline_value']}",
              f"• €{f['income_received']} of 3-client target · {f['clients_needed']} needed, "
              f"{f['weeks_left']} wks left · calls {f['calls_this_week']}/{f['weekly_call_target']}"]
    lines += ["\nLEARNING:", "• see 06-LEARNING/platform-progress.md"]
    if d["news"]:
        lines.append("\nNEWS:")
        lines += [f"• {n}" for n in d["news"]]
    else:
        lines.append("\nNEWS: search offline")
    if f["outstanding"]:
        lines.append("\nWAITING ON:")
        lines += [f"• {o['client']}: {o['amount']}, day {o['days']}" for o in f["outstanding"]]
    lines += ["", d["gap"], "", f"▶️ ONE ACTION: {d['one_action']}"]
    if d["suppressed"]:
        lines.append("\nSUPPRESSED YESTERDAY: " + "; ".join(d["suppressed"]))
    return "\n".join(lines)


def compose(d: dict) -> str:
    data = fallback_compose(d)  # deterministic data block as source material
    try:
        import cc_client
        env = agents.parse_envelope(cc_client.run(
            f"DATA (pre-fetched, complete):\n{data}\n\nLEARNING FILE HEAD:\n"
            f"{d['learning_head']}\n\nCompose today's brief. The ONE ACTION is: "
            f"{d['one_action']} — use it verbatim in section 9.",
            system=agents.assemble("briefing"), model="sonnet",
            allowed_tools="Read,Glob,Grep", max_turns=6, timeout=180))
        return env["response_md"] or data
    except Exception:
        return data


def run():
    state.init()
    text = compose(gather())
    memory.vault_write(f"00-META/daily-briefings/{date.today().isoformat()}.md",
                       "create", text)
    notify.send(text)


if __name__ == "__main__":
    run()
