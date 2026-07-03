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

This repo just slipped Claude the NZT-48 pill and now your AI intern is absolutely ZOOTED.

NZT-48 is the personal AI OS that runs 24/7 like that one over-caffeinated, Adderall-fueled intern who never sleeps, never forgets, and actually gets shit done. (Built by Euan Smith)

It wakes up before you, briefs you every morning like a standing desk standup, watches your whole pipeline, writes your emails, and hits you on Telegram like a real human.

You can straight up message this thing from anywhere, phone, Mac, iOS, whatever, and it just does the thing you ask, no pushback or waffle. Native with your Calendar, Alarms, Mail, reminders, the whole human workflow. No weird chatbot lag. It feels like texting your smartest (and most unhinged) employee. (think The Social Network + Mr.Robot on speed-dail)

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


Daily Brief at 09:00 — Priorities, deadlines, pipeline updates, relevant news. Reads like a 60-second hype reel. You’re caught up before your coffee’s even hot.

Smart Router — Figures out what needs what. Quick stuff runs on local Gemma. Heavy lifting goes to Claude Code headless. Everything gets queued like a pro. Nothing falls through the cracks.

7 Agents — Research gremlin, Business dude, Learning mode, Memory vault, Pre-call prep, Briefing beast, Task destroyer. Each one prompt-tuned and locked in.

5 Monitors — Silent background watchers. They only ping you when it actually matters (max 2 nudges a day, no spam).

Vault Memory — Eats your entire Obsidian vault. Your real notes, projects, and people become the context. No more generic corporate AI slop. (or getting dumber from long convos)

Telegram Native — Text it like a person. Commands or normal chat. Always on, always ready.

Terminal Dashboard — Riced btop/neofetch-style TUI. Live bot status, pipeline, message feed, alerts, CPU/RAM bars, clock. Opens automatically when you launch a terminal. Q to quit, R to refresh, B to restart the bot.

Zero € per message at scale. Runs on your machine. Adapts to you after a dead-simple 3-question setup. (becuase fck subscription based services)

---

## Install

```bash
git clone https://github.com/EuanSmith2/NZT-48
cd NZT-48
./install.sh
```

The installer detects what you have, fills in what's missing, asks 3 questions, and starts the bot. Takes 5 minutes the first time (model download). Under 60 seconds on repeat.

**You need:**
- macOS (Linux / WSL support in progress)
- [Claude Code CLI](https://github.com/anthropics/claude-code) — logged in
- A Telegram account

> **Heads up:** `install.sh` fetches and runs a script from the internet (standard for most CLI tools, same as Homebrew). Review it first if that's your thing: `curl -fsSL https://raw.githubusercontent.com/EuanSmith2/NZT-48/master/install.sh | less`

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
- [x] Web dashboard
- [ ] Multi-vault support
- [ ] Multi-user Telegram (one bot, multiple people)

---

<div align="center">

Built by [Euan Smith](https://euansmith.net) · [GitHub Sponsors](https://github.com/sponsors/EuanSmith2) · MIT · [business.euan@hotmail.com](mailto:business.euan@hotmail.com)

*"It's not that I'm smarter. I just use more of my brain."*

**Clone it. Install it. Give your AI the pill and watch it start cooking.**
</div>
