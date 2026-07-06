<div align="center">

<img src="assets/banner.png" width="100%" alt="NZT-48 — Your agent. Your vault. Your rules." />

</div>

---

Your agent. Your vault. Your rules.

[![License: MIT](https://img.shields.io/badge/license-MIT-00ff88?style=flat-square&labelColor=0a0a0a)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-00ff88?style=flat-square&labelColor=0a0a0a)](requirements.txt)
[![Built on Claude Code](https://img.shields.io/badge/built_on-Claude_Code-00ff88?style=flat-square&labelColor=0a0a0a)](https://github.com/anthropics/claude-code)
[![Interface: Telegram](https://img.shields.io/badge/interface-Telegram-00ff88?style=flat-square&labelColor=0a0a0a)](https://telegram.org)
[![Installs](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.counterapi.dev%2Fv1%2Fnzt48-installs%2Finstalls%2F&query=count&label=installs&color=00ff88&style=flat-square&labelColor=0a0a0a)](https://github.com/EuanSmith2/NZT-48)

[Features](#features) · [Install](#install) · [Memory](#memory--the-part-that-compounds) · [Docs](#documentation)

---

NZT-48 is a self-hosted personal AI system that runs on your own machine, keeps its memory in your Obsidian vault, and reaches you through Telegram. Seven specialised agents handle your day — briefing, research, business, tasks, learning, pre-call and memory — each acting only with your explicit approval. No cloud dependency beyond your Claude Code subscription. No per-token bill. One command sets it up:

```bash
git clone https://github.com/EuanSmith2/NZT-48 && cd NZT-48 && ./install.sh
```

## Features

- 🧠 **Morning brief** — 07:30 daily digest assembled before you're awake: tasks, pipeline, weather, streaks, anything waiting on you.
- 🤖 **Seven agents** — briefing, research, business, memory, pre-call, learning, task; each owns its domain, none overlaps.
- 📱 **Phone-first** — Telegram is the only interface. No dashboard, no browser tab to maintain; send a message, get a response.
- 🗂️ **Vault memory** — everything lands in your own Obsidian markdown. Readable offline, searchable forever, exportable any time.
- 🛡️ **Approval gate** — every outbound action — email drafts, vault edits, file moves — shows exactly what will happen before it does.
- 🎙️ **Voice in** — voice notes transcribed locally and echoed back before they're filed or acted on; nothing runs unseen.
- 💼 **Business layer** — cold outreach drafts, pipeline tracking, lead scoring, follow-up nudges. Optional; off by default.
- ⚡ **Two-tier routing** — trivial exchanges hit a local 3B model in under a second; anything that reasons goes to Claude Code headless.
- 📊 **Zero per-token billing** — runs on a Claude Code subscription. Marginal cost per message: nothing extra.
- 🔒 **Private overlay** — your keys, identity and personalised prompts stay in `private/` (gitignored); the public repo stays clean.

## Memory — the part that compounds

```
  07:30 brief
       ↓
  HOT-CACHE.md ──── always in every prompt ────→  agents know you before searching
  (≤ 1,200 chars)
       ↑
  warm retrieval ── scored per query ──────────→  research · pre-call agents
       ↑
  vault writes ──── approval gate ─────────────→  protected paths need a tap
       ↑
  untrusted input ─ docs · web · screenshots ─→  gated regardless of destination
```

- Every message lands verbatim in a daily markdown log — nothing is paraphrased on arrival.
- One core file, `HOT-CACHE.md` (≤ 1,200 chars), rides in every prompt — the system knows the current version of you before it searches anything.
- Protected paths — `01-PROFILE/`, `02-GOALS/`, `03-PEOPLE/`, `HOT-CACHE.md` — require an explicit tap before any write. A prompt cannot silently rewrite your goals.
- Any content that arrived from outside — a PDF, a forwarded message, a web snippet — is treated as untrusted. Its writes are gated regardless of destination. This closed a real prompt-injection hole; the fix is in the commit history.

Full vault architecture and retrieval internals: `docs/memory.md`.

## Install

1. Get a bot token from [@BotFather](https://t.me/BotFather).
2. Install [Claude Code](https://github.com/anthropics/claude-code) and log in once.
3. Run the installer on macOS (Linux / WSL in progress):

```bash
git clone https://github.com/EuanSmith2/NZT-48 && cd NZT-48 && ./install.sh
```

4. Message your bot. The wizard reads your Telegram ID from that first message, generates `config.yml`, scaffolds the vault and starts the agents. First run ~5 minutes (model pull); subsequent runs under a minute.

Headless installs pass `--skip-setup` or `--non-interactive`. Full walkthrough: `docs/install.md`.

## How it works

```
  Telegram
      ↓
  router.py ──── trivial ──→  local 3B model  (<1s, on-device)
      │
      └──── thinks ───→  Claude Code headless
                               ↓
                           agents.py
                               ↓
                       approval gate  (if outbound write)
                               ↓
                       vault / action
```

Long-poll Telegram means no public HTTPS endpoint, no domain, no webhook. The bot and five background monitors run as launchd units on your Mac — operations in `docs/deploy.md`.

## Cost

No per-token billing. One subscription covers everything:

| Component | What you pay |
|---|---|
| Claude Code | Anthropic subscription — fixed monthly |
| Local routing model | Nothing — runs on your hardware |
| Telegram bot | Free |
| Obsidian vault | Free (desktop app) |
| Voice transcription | Local via `faster-whisper` — no API key |

Marginal cost per message: **€0 extra** beyond the subscription.

## Security

```
  inbound ── sanitiser ──→  agent ──→  approval gate ──→  vault / send
  (web · docs · photos)       ↑              ↓
                         untrusted?     tap required
                          gated write
```

Inbound content passes a prompt-injection sanitiser before the model reads it. Outbound actions — emails, vault edits, file moves — surface a plain-language summary and wait for a yes/no. The allowlist fails closed: an empty list answers nobody. Your vault is plain markdown you own. Security internals: `docs/security.md`.

## Commands

| In Telegram | On the machine |
|---|---|
| `/brief` · `/task` · `/research` | `python bot.py` |
| `/setup` · `/new` · `/usage` | `python bot.py --dry-run` |
| `/pipeline` · `/cram` · `/status` | `tail -f logs/nzt.log` |

Full reference including `/usage` breakdowns by agent and by day: `docs/cli.md`.

## Tiers

**Free** — everything above. Complete, working, MIT-licensed.

**Pro** — the prompt pack running on the original system: three additional agent profiles, enhanced brief templates, lead scoring and cold outreach generators. Drop the `premium/` folder in and restart.

## Documentation

[Install](docs/install.md) · [Configuration](docs/config.md) · [Memory](docs/memory.md) · [Security](docs/security.md) · [Deploy](docs/deploy.md) · [CLI](docs/cli.md) · [Extending](docs/extending.md)

## Built on

Claude Code headless runs every agent call — `ANTHROPIC_API_KEY` is stripped from the child environment, so there is no per-token billing path. Python 3.11+, Ollama for the routing tier, SQLite for state, `faster-whisper` for voice. The vault is plain markdown — nothing proprietary, nothing to migrate from.

## License

MIT — take it, fork it, run it on your own machine; just don't hold anyone responsible if something breaks.

---

<div align="center">

Built by [Euan Smith](https://euansmith.net) &nbsp;·&nbsp; [MIT](LICENSE) &nbsp;·&nbsp; open to sponsors

*"It's not that I'm smarter. I just use more of my brain."*

</div>
