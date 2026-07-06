# Install

## Requirements

- macOS (Linux / WSL support in progress)
- [Claude Code CLI](https://github.com/anthropics/claude-code) — installed and logged in
- Python 3.11+
- A Telegram account

## One-line install

```bash
git clone https://github.com/EuanSmith2/NZT-48 && cd NZT-48 && ./install.sh
```

The script does the following in order:

1. Checks Python 3.11+, Claude Code, and Ollama
2. Creates a `.venv` and installs `requirements.txt`
3. Pulls the local routing model (`nzt-lite` via Ollama)
4. Asks for your Telegram bot token and writes `.env`
5. Copies `config.yml.example` → `config.yml` (you edit this next)
6. Scaffolds the Obsidian vault at the path you choose
7. Registers two launchd units so the bot and brief timer survive reboots

On success, message your bot. The wizard reads your Telegram ID from that first message, finishes configuration, and confirms in chat.

## First-run wizard

After installation, `/setup` walks through identity, goals, brief time and module toggles. It writes `config.yml` when you confirm. You can re-run `/setup` at any time — it diffs against the current file and only changes what you answer.

## Headless install

```bash
./install.sh --skip-setup        # installs deps + launchd, skips wizard
./install.sh --non-interactive   # assumes all defaults, no prompts
```

## Manual steps (if the installer fails)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

ollama pull qwen2.5:3b
ollama create nzt-lite -f Modelfile

cp config.yml.example config.yml
# edit config.yml — minimum: user.name, vault.path, telegram.token
```

Then add your bot token to `.env`:

```
TELEGRAM_TOKEN=your:token
```

Start manually:

```bash
python bot.py
```

## VPS / SSH

The bot runs fine on a Linux VPS. Substitute `launchd` with `systemd`:

```bash
cp deploy/nzt48.service /etc/systemd/system/
systemctl enable --now nzt48
```

`systemd` unit templates are in `deploy/` once Linux support ships.
