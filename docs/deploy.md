# Deploy

## macOS (launchd)

The installer registers two launchd user units:

| Unit | File | What it runs |
|---|---|---|
| Bot | `com.nzt48.plist` | `python bot.py` — the Telegram long-poll loop |
| Brief | `com.nzt48.brief.plist` | `python brief.py` — fires once daily at your configured time |

Both are user-scoped (`~/Library/LaunchAgents/`) so they start on login without root.

**Common operations:**

```bash
# status
launchctl list | grep nzt48

# restart bot
launchctl kickstart -k gui/$(id -u)/com.nzt48

# restart brief timer
launchctl kickstart -k gui/$(id -u)/com.nzt48.brief

# stop everything
launchctl unload ~/Library/LaunchAgents/com.nzt48.plist
launchctl unload ~/Library/LaunchAgents/com.nzt48.brief.plist

# reload after config change
launchctl unload ~/Library/LaunchAgents/com.nzt48.plist
launchctl load  ~/Library/LaunchAgents/com.nzt48.plist
```

## Logs

```bash
tail -f logs/nzt.log           # live bot output
tail -f logs/brief.log         # brief run history
tail -f logs/monitors.log      # background monitor output
```

Log rotation is not automatic — run `python claude_usage.py --trim` to archive old entries, or add a weekly cron:

```bash
(crontab -l; echo "0 3 * * 0 python /path/to/NZT-48/claude_usage.py --trim") | crontab -
```

## Updates

```bash
git pull
source .venv/bin/activate
pip install -r requirements.txt --upgrade
launchctl kickstart -k gui/$(id -u)/com.nzt48
```

There is no auto-update — pull manually, review the diff, then restart.

## Changing brief time

Edit `config.yml`:

```yaml
brief:
  time: "07:30"
```

Then reload the brief plist:

```bash
launchctl unload ~/Library/LaunchAgents/com.nzt48.brief.plist
launchctl load  ~/Library/LaunchAgents/com.nzt48.brief.plist
```

## Monitoring check

The five background monitors run inside `bot.py` as asyncio tasks on the same process. They fire every `monitoring.interval_minutes` minutes within the `window` hours. If the bot process dies, all monitors stop with it — the launchd unit will restart the process automatically.

Monitor state (last-fired timestamps, suppressed nudges) lives in `state.db`. Delete the relevant rows to reset:

```bash
sqlite3 state.db "DELETE FROM kv WHERE key LIKE 'monitor_%';"
```

## VPS / Linux

Linux support is in progress. The principle is identical — replace launchd with systemd user units. Template:

```ini
[Unit]
Description=NZT-48 Telegram bot
After=network.target

[Service]
WorkingDirectory=/home/user/NZT-48
ExecStart=/home/user/NZT-48/.venv/bin/python bot.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

Install as `~/.config/systemd/user/nzt48.service`, then:

```bash
systemctl --user enable --now nzt48
```
