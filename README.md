<div align="center">

<img src="assets/swallow.gif" width="200" alt="NZT-48 pill swallowed" />
<img src="assets/brain.gif" width="200" alt="brain scan loop" />

# NZT-48

`// your AI took the pill`

![Free Tier](https://img.shields.io/badge/free_tier-complete-00ff66?style=flat-square&labelColor=0d0d0d)
![Pro DLC](https://img.shields.io/badge/pro_DLC-gumroad-a855f7?style=flat-square&labelColor=0d0d0d)
![Claude Code](https://img.shields.io/badge/Claude_Code-required-f59e0b?style=flat-square&labelColor=0d0d0d)
![Telegram](https://img.shields.io/badge/Telegram-native-58a6ff?style=flat-square&labelColor=0d0d0d)
![Obsidian](https://img.shields.io/badge/Obsidian-memory-7c3aed?style=flat-square&labelColor=0d0d0d)

**The human brain is limited. Artificial intelligence is not.**

</div>

---

NZT-48 is a personal AI OS built by Euan Smith. It runs 24/7 on your machine, briefs you every morning, monitors your pipeline, writes your emails, and routes every request through the cheapest model that can handle it — local Gemma for quick tasks, Claude Code headless for the heavy stuff. €0 per message at scale. It adapts to whoever's running it after a 3-question install.

This is not a chatbot. It's infrastructure.

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

## How it's different

| | NZT-48 | Other "Jarvis" repos |
|---|---|---|
| Cost per message | €0 (Claude Code sub) | API billing |
| Runs locally | Yes | Usually cloud |
| Memory | Your Obsidian vault | None / vector DB |
| Setup | 1 command, 5 min | Days of config |
| Personality | Adapts to you | Generic |
| Coddling | None | Excessive |

---

## What's in it

**Daily Brief** — 09:00 every morning. Priorities, deadlines, pipeline, news. Reads standing up, in 60 seconds.

**Smart Router** — classifies every request. Local Gemma handles quick Q&A. Claude Code headless takes the complex stuff. Score 5 tasks queue to your next interactive session. Nothing gets dropped.

**7 Agents** — Research, Business, Learning, Memory, Pre-call, Briefing, Task. Each prompt-tuned for its job.

**5 Monitors** — background watchers that nudge you when something needs attention. Max 2 per day. No noise.

**Vault Memory** — reads your Obsidian vault. Your notes, projects, and people are the context layer — not the model's generic defaults.

**Telegram Native** — message it like a person. Commands or plain text. Always on.

---

## Install

```bash
git clone https://github.com/EuanSmith2/NZT-48
cd NZT-48
./install.sh
```

The installer detects what you have, fills in what's missing, asks 3 questions, and starts the bot. Takes 5 minutes the first time (model download). Under 60 seconds on repeat.

**You need:**
- macOS (Linux support coming)
- [Claude Code CLI](https://github.com/anthropics/claude-code) — logged in
- A Telegram account

That's it.

---

## Tiers

**Free** — everything above. Complete. Works out of the box.

**Pro DLC** — the expansion pack. Three premium agent personalities (Sales Beast, Deep Research, Hacker Mode), enhanced brief templates, lead scoring prompts, cold email generator. These are the prompts I actually use.

→ [Get Pro on Gumroad](https://gumroad.com/euansmith/nzt48pro) · Drop the `/premium` folder and restart.

---

## Roadmap

- [ ] Linux / WSL support
- [ ] Voice input (Whisper pipeline)
- [ ] Web dashboard
- [ ] Multi-vault support

---

<div align="center">

Built by [Euan Smith](https://github.com/EuanSmith2) · [GitHub Sponsors](https://github.com/sponsors/EuanSmith2) · MIT

*"It's not that I'm smarter. I just use more of my brain."*

</div>
