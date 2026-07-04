"""WhatsApp transport — Meta Cloud API (free tier), same dispatch core.

Setup (one-time):
  1. developers.facebook.com → create app → add WhatsApp product.
  2. Grab: permanent access token + phone number ID. Put them in
     private/local.yml under transports.whatsapp (token, phone_id), plus
     verify_token (any string you invent) and allowed (YOUR number,
     digits only, e.g. "3538xxxxxxxx") — messages from anyone else are dropped.
  3. Expose the webhook: `cloudflared tunnel --url http://localhost:8090`
     (free, no account) and register <tunnel-url>/webhook in the Meta app's
     WhatsApp → Configuration, using your verify_token. Subscribe to
     `messages`.
  4. Run: .venv/bin/python -m transports.whatsapp

Approvals here are text-based: gated items say "reply 'approve <id>'".
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import requests

import state
from config import WHATSAPP
from transports.base import Transport, handle_message

PORT = int(WHATSAPP.get("port", 8090))
GRAPH = "https://graph.facebook.com/v20.0"
SEEN_KV = "wa_seen_ids"  # dedupe — Meta re-delivers on slow ack


class WhatsAppTransport(Transport):
    name = "whatsapp"

    def __init__(self):
        self.token = WHATSAPP.get("token", "")
        self.phone_id = WHATSAPP.get("phone_id", "")
        self.verify_token = WHATSAPP.get("verify_token", "")
        self.allowed = str(WHATSAPP.get("allowed", ""))
        self.to = self.allowed  # single-user system: replies go to the owner

    def send(self, text: str) -> None:
        for i in range(0, len(text), 3900):
            r = requests.post(
                f"{GRAPH}/{self.phone_id}/messages",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"messaging_product": "whatsapp", "to": self.to,
                      "type": "text", "text": {"body": text[i:i + 3900]}},
                timeout=15)
            if r.status_code >= 400:
                print(f"[whatsapp] send failed {r.status_code}: {r.text[:200]}")

    # -- inbound ---------------------------------------------------------
    def _seen(self, msg_id: str) -> bool:
        seen = (state.kv_get(SEEN_KV) or "").split(",")
        if msg_id in seen:
            return True
        state.kv_set(SEEN_KV, ",".join(([msg_id] + seen)[:50]))
        return False

    def _on_payload(self, payload: dict) -> None:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                for msg in change.get("value", {}).get("messages", []) or []:
                    if msg.get("type") != "text":
                        continue
                    sender = msg.get("from", "")
                    if self.allowed and sender != self.allowed:
                        print(f"[whatsapp] dropped message from {sender}")
                        continue
                    if self._seen(msg.get("id", "")):
                        continue
                    text = msg["text"]["body"].strip()
                    # worker thread: dispatch blocks on model calls
                    threading.Thread(target=handle_message,
                                     args=(text, self.send),
                                     daemon=True).start()

    def run(self) -> None:
        if not (self.token and self.phone_id and self.verify_token):
            raise SystemExit("whatsapp transport not configured — see module "
                             "docstring / private/local.yml transports.whatsapp")
        transport = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):  # keep tokens out of stdout
                pass

            def do_GET(self):  # Meta webhook verification handshake
                q = parse_qs(urlparse(self.path).query)
                if (urlparse(self.path).path == "/webhook"
                        and q.get("hub.verify_token", [""])[0] == transport.verify_token):
                    body = q.get("hub.challenge", [""])[0].encode()
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(403)
                    self.end_headers()

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(min(length, 512 * 1024))
                self.send_response(200)  # ack fast — Meta retries otherwise
                self.end_headers()
                try:
                    transport._on_payload(json.loads(raw))
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"[whatsapp] bad payload: {e}")

        state.init()
        print(f"[whatsapp] webhook on http://localhost:{PORT}/webhook")
        HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    WhatsAppTransport().run()
