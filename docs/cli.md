# CLI Reference

## Telegram commands

### Daily use

| Command | What it does |
|---|---|
| `/brief` | Run the morning brief on demand (same output as the 07:30 auto-brief) |
| `/task <text>` | Add a task with optional due date — `due tomorrow`, `due friday`, `due 2026-07-10` |
| `/research <topic>` | Deep-dive on any topic; result filed to vault under `05-KNOWLEDGE/` |
| `/cram <topic>` | Quick summary mode — faster than research, shorter output |
| `/pipeline` | Show current business pipeline (requires `modules.business.enabled: true`) |
| `/status` | System status: uptime, last brief time, monitor state, token usage today |
| `/usage` | Token and cost breakdown by agent and by day |

### Input

| Command | What it does |
|---|---|
| Voice note | Transcribed locally, echoed back, then routed to the relevant agent |
| Photo | Described by the vision model; filed as untrusted — write is gated |
| PDF / document | Extracted, summarised, filed under `05-KNOWLEDGE/` as untrusted |
| Forwarded message | Treated as untrusted content regardless of source |
| Plain text | Classified by `router.py` and dispatched to the appropriate agent |

### Setup and admin

| Command | What it does |
|---|---|
| `/setup` | Onboarding wizard — generates or updates `config.yml` |
| `/new <name>` | Create a new note or project card in the vault |
| `/say <text>` | Read text aloud via ElevenLabs TTS (requires `voice.elevenlabs.api_key`) |
| `/help` | List available commands with one-line descriptions |

## Machine commands

Run from inside the repo with the venv active (`source .venv/bin/activate`).

### Bot

```bash
python bot.py                  # start the bot (also starts background monitors)
python bot.py --dry-run        # validate config and vault path, no Telegram connection
python bot.py --no-monitors    # start bot only, skip background monitors
```

### Brief

```bash
python brief.py                # run the morning brief now and send to Telegram
python brief.py --print        # run brief and print to stdout, do not send
```

### Usage

```bash
python claude_usage.py         # print token usage summary for today
python claude_usage.py --week  # usage for the past 7 days
python claude_usage.py --trim  # archive log entries older than 30 days
```

### State

```bash
sqlite3 state.db ".tables"                         # list all tables
sqlite3 state.db "SELECT * FROM kv LIMIT 20;"      # inspect key-value store
sqlite3 state.db "DELETE FROM kv WHERE key='x';"   # clear a key
```

### Logs

```bash
tail -f logs/nzt.log           # live bot log
tail -f logs/brief.log         # brief run history
grep "WARN\|ERROR" logs/nzt.log | tail -20
```

## Usage breakdown

`/usage` in Telegram (or `python claude_usage.py`) shows:

```
TODAY — 2026-07-06
  briefing       4,210 tok   sonnet
  research       9,840 tok   sonnet
  routing          380 tok   local
  ─────────────────────────────────
  total         14,430 tok   (subscription — €0 extra)
```

Every agent call is logged to `state.db` with timestamp, agent name, model, input tokens and output tokens.
