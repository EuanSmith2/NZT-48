<div align="center">

<img src="assets/swallow.gif" width="200" alt="NZT-48" />
<img src="assets/brain.gif" width="200" alt="brain scan" />

# NZT-48

`// your AI took the pill`

![Free Tier](https://img.shields.io/badge/free_tier-complete-00ff66?style=flat-square&labelColor=0d0d0d)
![Pro DLC](https://img.shields.io/badge/pro_DLC-gumroad-a855f7?style=flat-square&labelColor=0d0d0d)
![Claude Code](https://img.shields.io/badge/Claude_Code-required-f59e0b?style=flat-square&labelColor=0d0d0d)
![Telegram](https://img.shields.io/badge/Telegram-native-58a6ff?style=flat-square&labelColor=0d0d0d)
![Obsidian](https://img.shields.io/badge/Obsidian-memory-7c3aed?style=flat-square&labelColor=0d0d0d)
![Installs](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.counterapi.dev%2Fv1%2Fnzt48-installs%2Finstalls%2F&query=count&label=installs&color=00ff66&style=flat-square&labelColor=0d0d0d)

</div>

**One line, whole system** — hover the block, hit <kbd>⧉</kbd>, paste in a terminal:

```bash
git clone https://github.com/EuanSmith2/NZT-48 && cd NZT-48 && ./install.sh
```

Or hand it straight to your AI and let it do the work:

```text
Clone github.com/EuanSmith2/NZT-48, run ./install.sh, and walk me through setup.
```

---

NZT-48 is a self-hosted personal AI system. It runs on your machine, keeps its memory in your own notes, and reaches you through Telegram. It briefs you each morning before you're up, watches your deadlines and pipeline in the background, drafts what needs drafting — and asks permission before anything leaves your machine.

Marginal cost per message: zero. It runs on a Claude Code subscription and a small local model, not per-token API billing.

---

## Demo

```
$ /brief

USER — Thu 02 Jul · cloudy, 17°C

TODAY
  ↳ Follow up with client re: invoice
  ↳ Make 3 cold calls before 5pm
  ↳ Complete module 7 assessment

PIPELINE
  ↳ Murphy & Co — proposal sent, awaiting reply
  ↳ €400 of target, 8 weeks left

LEARNING
  ↳ Platform — active path · day 12 streak

WAITING ON
  ↳ Payment from client (invoiced Jul 1)
```

---

## Design

**Two-speed routing.** A deterministic router classifies every message. Trivial exchanges run on a local 3B model in under a second; anything that thinks runs on Claude Code headless, with your vault mounted as context. The local tier knows its limits — when uncertain, it escalates rather than answers.

**Memory is your vault.** Your Obsidian notes are the context: hot-cached state, scored retrieval per query, and a strict write protocol. Appends are automatic; edits require approval; and any write originating from ingested content — a PDF, a screenshot, a web page — is gated regardless of destination. External documents cannot silently become memories.

**Seven agents, one contract.** Briefing, research, business, learning, memory, pre-call and task agents share a single output envelope and a single escalation rule: uncertain means ask, never guess.

**Proactive, with a ceiling.** Five background monitors; a hard maximum of two unprompted messages a day. Deadlines outrank nudges, nudges outrank streaks, and anything suppressed surfaces in the next brief instead of disappearing.

**Approval gates on everything outbound.** Emails, vault edits, file moves — each shows exactly what will happen before it happens, down to the recipient's domain.

**Multi-modal in.** Voice notes are transcribed locally and echoed back before they're acted on; documents and screenshots are converted, extracted and filed — as untrusted input, per the write protocol above.

**Configured, not assumed.** `config.yml` defines the person: identity, goals, brief priorities, vault layout. The business and learning modules are optional — disabled, the engine carries no pipeline, no sales nudges, nothing of anyone else's life. A 7-question Telegram wizard (`/setup`) generates a working configuration from scratch.

The system has been red-teamed against prompt injection, path traversal and vault poisoning. Findings and fixes are in the commit history.

---

## Comparison

| | NZT-48 | Typical "Jarvis" repo |
|---|---|---|
| Cost per message | €0 (Claude Code subscription) | Per-token API billing |
| Memory | Your Obsidian vault | None, or a vector DB to maintain |
| Proactive | Morning brief + 5 monitors | Responds only when asked |
| Interface | Telegram, anywhere | A terminal on one machine |
| Write safety | Approval gates + provenance checks | Unrestricted |
| Setup | One command | Days of configuration |

---

## Install

```bash
git clone https://github.com/EuanSmith2/NZT-48
cd NZT-48
./install.sh
```

The installer verifies dependencies, asks a short series of questions, scaffolds the vault and starts the bot. First run takes about five minutes (model download); subsequent runs under a minute.

**Requirements:** macOS (Linux/WSL in progress) · [Claude Code CLI](https://github.com/anthropics/claude-code), logged in · a Telegram account.

> **Note:** `install.sh` downloads and executes code, as most CLI installers do. Review it first if you prefer: `curl -fsSL https://raw.githubusercontent.com/EuanSmith2/NZT-48/master/install.sh | less`
>
> On success it sends one anonymous ping to increment the installs counter above — a bare HTTP hit, no data. `NZT_NO_TELEMETRY=1 ./install.sh` skips it.

---

## Tiers

**Free** — everything described above. Complete, working, MIT-licensed.

**Pro** — the prompt pack I run myself: three additional agent personalities, enhanced brief templates, lead scoring and cold outreach generators. [Gumroad](https://gumroad.com/euansmith/nzt48pro) — drop the `premium/` folder in and restart.

---

## Roadmap

- [ ] Linux / WSL support
- [x] Voice input (local Whisper pipeline)
- [x] Web dashboard
- [ ] Multi-vault support
- [ ] Multi-user Telegram

---

<div align="center">

Built by [Euan Smith](https://euansmith.net) · [Sponsors](https://github.com/sponsors/EuanSmith2) · MIT · [business.euan@hotmail.com](mailto:business.euan@hotmail.com)

*"It's not that I'm smarter. I just use more of my brain."*

</div>
