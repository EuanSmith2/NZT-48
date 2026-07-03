"""NZT-48 local dashboard — http://localhost:5748
Run: .venv/bin/python dashboard.py  (or launchd, see com.nzt48.dashboard.plist)"""
import json
import subprocess
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

import finance
import state
from config import USER_NAME

PORT = 5748


def _midnight() -> float:
    return datetime.combine(date.today(), datetime.min.time()).timestamp()


def get_data() -> dict:
    state.init()
    midnight = _midnight()
    with state.db() as con:
        msgs = con.execute(
            "SELECT role, text, ts FROM messages ORDER BY ts DESC LIMIT 8"
        ).fetchall()
        alerts = con.execute(
            "SELECT monitor, key, ts FROM alerts WHERE sent=1 AND ts>? ORDER BY ts DESC",
            (midnight,),
        ).fetchall()
        pending = con.execute(
            "SELECT id, kind, content FROM drafts WHERE status='pending' ORDER BY ts DESC"
        ).fetchall()
        cost_row = con.execute(
            "SELECT COALESCE(SUM(usd),0), COALESCE(SUM(tok_in+tok_out),0) "
            "FROM cost_log WHERE ts>?", (midnight,)
        ).fetchone()
        tasks = con.execute(
            "SELECT title, status FROM tasks ORDER BY id DESC LIMIT 5"
        ).fetchall()

    # bot status
    try:
        out = subprocess.check_output(
            ["launchctl", "list", "com.nzt48"], text=True, stderr=subprocess.DEVNULL
        )
        pid_line = next((l for l in out.splitlines() if '"PID"' in l), "")
        pid = pid_line.split("=")[-1].strip().rstrip(";").strip('"') if pid_line else None
        bot_status = f"running (PID {pid})" if pid and pid != "0" else "stopped"
    except Exception:
        bot_status = "unknown"

    fin = {}
    try:
        fin = finance.compute()
    except Exception:
        pass

    return {
        "user": USER_NAME,
        "date": date.today().strftime("%a %d %b %Y"),
        "bot_status": bot_status,
        "messages": [{"role": r, "text": t[:180], "ts": ts} for r, t, ts in msgs],
        "alerts": [{"monitor": m, "key": k, "ts": ts} for m, k, ts in alerts],
        "pending_drafts": [{"id": i, "kind": k, "preview": c[:120]} for i, k, c in pending],
        "cost_usd": round(cost_row[0], 4),
        "tokens_today": int(cost_row[1]),
        "tasks": [{"title": t, "status": s} for t, s in tasks],
        "finance": {
            "outstanding": fin.get("outstanding", []),
            "mrr": fin.get("mrr", 0),
        },
    }


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NZT-48</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#0a0a0a;color:#00ff66;font-family:'SF Mono','Fira Code',monospace;font-size:13px;line-height:1.7;padding:24px}
  h1{font-size:11px;letter-spacing:4px;text-transform:uppercase;color:#00ff66;margin-bottom:4px}
  .sub{color:#333;font-size:11px;letter-spacing:2px;margin-bottom:28px}
  .grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:16px}
  .grid2{display:grid;grid-template-columns:2fr 1fr;gap:16px}
  .card{background:#0f0f0f;border:1px solid #1a1a1a;border-radius:6px;padding:16px}
  .card-title{font-size:9px;letter-spacing:3px;text-transform:uppercase;color:#333;margin-bottom:12px;border-bottom:1px solid #1a1a1a;padding-bottom:8px}
  .val{font-size:22px;color:#00ff66;font-weight:bold}
  .dim{color:#333}
  .green{color:#00ff66}
  .yellow{color:#f59e0b}
  .red{color:#ff5f57}
  .row{display:flex;justify-content:space-between;align-items:baseline;padding:4px 0;border-bottom:1px solid #111}
  .row:last-child{border-bottom:none}
  .pill{font-size:9px;padding:2px 8px;border-radius:3px;letter-spacing:1px;text-transform:uppercase}
  .pill-g{background:#00ff661a;color:#00ff66}
  .pill-y{background:#f59e0b1a;color:#f59e0b}
  .pill-r{background:#ff5f571a;color:#ff5f57}
  .msg{padding:6px 0;border-bottom:1px solid #111;font-size:12px}
  .msg:last-child{border-bottom:none}
  .role{color:#333;margin-right:8px;font-size:10px;text-transform:uppercase;letter-spacing:1px}
  .role.euan{color:#00ff66}
  footer{margin-top:24px;color:#1a1a1a;font-size:10px;text-align:center;letter-spacing:2px}
  #refresh{color:#1a1a1a;font-size:10px;float:right;letter-spacing:1px}
</style>
</head>
<body>
<h1>NZT-48</h1>
<div class="sub" id="meta">loading...</div>

<div class="grid" id="stats">
  <div class="card"><div class="card-title">Bot</div><div class="val" id="bot-status">—</div></div>
  <div class="card"><div class="card-title">Cost today</div><div class="val" id="cost">—</div><div class="dim" id="tokens"></div></div>
  <div class="card"><div class="card-title">MRR</div><div class="val" id="mrr">—</div></div>
</div>

<div class="grid2">
  <div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-title">Recent conversation</div>
      <div id="messages"><div class="dim">loading...</div></div>
    </div>
    <div class="card">
      <div class="card-title">Outstanding</div>
      <div id="outstanding"><div class="dim">—</div></div>
    </div>
  </div>
  <div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-title">Pending approvals</div>
      <div id="drafts"><div class="dim">none</div></div>
    </div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-title">Alerts today</div>
      <div id="alerts"><div class="dim">none</div></div>
    </div>
    <div class="card">
      <div class="card-title">Tasks</div>
      <div id="tasks"><div class="dim">none</div></div>
    </div>
  </div>
</div>

<footer>Built by Euan Smith · github.com/EuanSmith2 · NZT-48 <span id="refresh"></span></footer>

<script>
async function load() {
  try {
    const d = await fetch('/api').then(r => r.json());
    document.getElementById('meta').textContent = d.user + ' · ' + d.date;
    const bs = d.bot_status;
    const bel = document.getElementById('bot-status');
    bel.textContent = bs.startsWith('running') ? '● running' : '○ stopped';
    bel.className = 'val ' + (bs.startsWith('running') ? 'green' : 'red');
    document.getElementById('cost').textContent = '$' + d.cost_usd.toFixed(4);
    document.getElementById('tokens').textContent = d.tokens_today.toLocaleString() + ' tokens';
    document.getElementById('mrr').textContent = '€' + (d.finance.mrr || 0);

    document.getElementById('messages').innerHTML = d.messages.length
      ? d.messages.map(m =>
          `<div class="msg"><span class="role ${m.role}">${m.role}</span>${esc(m.text)}</div>`
        ).join('')
      : '<div class="dim">no messages yet</div>';

    document.getElementById('outstanding').innerHTML = (d.finance.outstanding||[]).length
      ? d.finance.outstanding.map(o =>
          `<div class="row"><span>${esc(o.client)}</span><span class="yellow">€${o.amount} · day ${o.days}</span></div>`
        ).join('')
      : '<div class="dim">none</div>';

    document.getElementById('drafts').innerHTML = d.pending_drafts.length
      ? d.pending_drafts.map(dr =>
          `<div class="row"><span class="pill pill-y">${dr.kind}</span><span style="font-size:11px;color:#555;margin-left:8px">${esc(dr.preview)}</span></div>`
        ).join('')
      : '<div class="dim">none</div>';

    document.getElementById('alerts').innerHTML = d.alerts.length
      ? d.alerts.map(a =>
          `<div class="row"><span class="dim">${a.monitor}</span><span style="font-size:11px;color:#555">${esc(a.key)}</span></div>`
        ).join('')
      : '<div class="dim">none</div>';

    document.getElementById('tasks').innerHTML = d.tasks.length
      ? d.tasks.map(t => {
          const cls = t.status === 'done' ? 'pill-g' : t.status === 'failed' ? 'pill-r' : 'pill-y';
          return `<div class="row"><span style="font-size:11px">${esc(t.title)}</span><span class="pill ${cls}">${t.status}</span></div>`;
        }).join('')
      : '<div class="dim">none</div>';

    document.getElementById('refresh').textContent = 'updated ' + new Date().toLocaleTimeString();
  } catch(e) {
    document.getElementById('meta').textContent = 'error: ' + e.message;
  }
}

function esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

load();
setInterval(load, 30000);
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api":
            try:
                data = json.dumps(get_data(), default=str)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data.encode())))
                self.end_headers()
                self.wfile.write(data.encode())
            except Exception as e:
                err = json.dumps({"error": str(e)})
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(err.encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(HTML.encode())))
            self.end_headers()
            self.wfile.write(HTML.encode())

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"NZT-48 dashboard → http://localhost:{PORT}")
    server.serve_forever()
