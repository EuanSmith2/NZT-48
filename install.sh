#!/usr/bin/env bash
# NZT-48 installer
# Built by Euan Smith (github.com/EuanSmith2) · MIT
set -euo pipefail

NZT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$NZT_DIR/.env"
CFG_FILE="$NZT_DIR/config.yml"
PLIST_SRC="$NZT_DIR/com.nzt48.plist.template"
PLIST_DST="$HOME/Library/LaunchAgents/com.nzt48.plist"
VENV="$NZT_DIR/.venv"

G='\033[0;32m'; Y='\033[0;33m'; D='\033[0;90m'; R='\033[0;31m'; N='\033[0m'

ok()   { printf "  ${G}✓${N}  %s\n" "$*"; }
skip() { printf "  ${D}↷${N}  ${D}%s${N}\n" "$*"; }
need() { printf "  ${Y}↓${N}  %s\n" "$*"; }
ask()  { printf "  ${Y}?${N}  %s" "$*"; }
die()  { printf "  ${R}✗${N}  %s\n" "$*"; exit 1; }
sep()  { printf "${D}─────────────────────────────────────${N}\n"; }

printf "\n${G}NZT-48${N}${D} v1.0.0 · installer${N}\n"
printf "${D}Built by Euan Smith · github.com/EuanSmith2 · MIT${N}\n\n"
sep

# ── detect ────────────────────────────────────────────────────────────────────

check_python() {
  command -v python3 &>/dev/null || die "python3 not found — install from python.org"
  ok "python3 $(python3 --version | cut -d' ' -f2)"
}

check_claude() {
  if command -v claude &>/dev/null; then
    ok "claude-code $(claude --version 2>/dev/null | head -1 || echo '(installed)')"
  else
    need "claude-code not found"
    printf "\n    npm install -g @anthropic-ai/claude-code && claude login\n\n"
    ask "Press enter once claude is installed and logged in → "
    read -r
    command -v claude &>/dev/null || die "claude still not found"
    ok "claude-code installed"
  fi
}

check_ollama() {
  if command -v ollama &>/dev/null; then
    ok "ollama $(ollama --version 2>/dev/null | head -1 || echo '(installed)')"
  else
    need "ollama not found — installing"
    curl -fsSL https://ollama.ai/install.sh | sh &>/dev/null
    ok "ollama installed"
  fi
}

detect_vault() {
  VAULT_PATH=""
  for candidate in \
    "$HOME/Documents/Notes" \
    "$HOME/Documents/Obsidian" \
    "$HOME/Obsidian" \
    "$HOME/Documents"
  do
    if [ -d "$candidate" ]; then
      VAULT_PATH="$candidate"
      ok "vault  $candidate"
      return
    fi
  done
  ICLOUD_OB="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents"
  if [ -d "$ICLOUD_OB" ]; then
    VAULT_PATH="$(ls -d "$ICLOUD_OB"/*/ 2>/dev/null | head -1 | sed 's|/$||')"
    [ -n "$VAULT_PATH" ] && ok "vault  $VAULT_PATH" && return
  fi
  VAULT_PATH="$HOME/Documents/Notes"
  skip "vault not detected — defaulting to $VAULT_PATH (edit config.yml to change)"
}

get_telegram_token() {
  EXISTING_TOKEN="$(grep -s '^TELEGRAM_TOKEN=' "$ENV_FILE" | cut -d= -f2 || true)"
  if [ -n "$EXISTING_TOKEN" ]; then
    skip "TELEGRAM_TOKEN  already set"
    TELEGRAM_TOKEN="$EXISTING_TOKEN"
    return
  fi
  need "TELEGRAM_TOKEN missing"
  printf "\n    Telegram → @BotFather → /newbot → copy the token\n\n"
  ask "Token → "
  read -r TELEGRAM_TOKEN
  [ -z "$TELEGRAM_TOKEN" ] && die "token required"
}

get_telegram_uid() {
  EXISTING_UID="$(grep -s '^TELEGRAM_USER_ID=[0-9]' "$ENV_FILE" | cut -d= -f2 || true)"
  if [ -n "$EXISTING_UID" ]; then
    skip "TELEGRAM_USER_ID  already set"
    TELEGRAM_UID="$EXISTING_UID"
    return
  fi
  need "TELEGRAM_USER_ID missing"
  printf "\n    Telegram → @userinfobot → Start → copy your numeric ID\n\n"
  ask "Your user ID → "
  read -r TELEGRAM_UID
  [ -z "$TELEGRAM_UID" ] && die "user ID required"
}

# ── install ───────────────────────────────────────────────────────────────────

install_deps() {
  printf "\n"; sep
  python3 -m venv "$VENV" &>/dev/null
  "$VENV/bin/pip" install -q -r "$NZT_DIR/requirements.txt"
  ok "python deps"
}

pull_model() {
  if ollama list 2>/dev/null | grep -q "nzt-lite"; then
    skip "nzt-lite  already pulled"
  else
    need "nzt-lite  pulling (~2GB, one-time)"
    ollama create nzt-lite -f "$NZT_DIR/Modelfile" &>/dev/null
    ok "nzt-lite ready"
  fi
}

write_env() {
  if [ -f "$ENV_FILE" ] && grep -q '^TELEGRAM_TOKEN=.\+' "$ENV_FILE" 2>/dev/null; then
    skip ".env  exists"
  else
    cat > "$ENV_FILE" <<EOF
TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
TELEGRAM_USER_ID=${TELEGRAM_UID:-0}
BRAVE_API_KEY=
ANTHROPIC_API_KEY=
EOF
    ok ".env written"
  fi
}

write_plist() {
  if [ -f "$PLIST_DST" ]; then
    skip "launchd plist  already installed"
  else
    sed "s|{{NZT_DIR}}|$NZT_DIR|g; s|{{VENV}}|$VENV|g; s|{{HOME}}|$HOME|g" \
      "$PLIST_SRC" > "$PLIST_DST"
    ok "launchd plist  $PLIST_DST"
  fi
}

# ── onboarding ────────────────────────────────────────────────────────────────

onboarding() {
  if [ -f "$CFG_FILE" ]; then
    skip "config.yml  exists — skipping onboarding"
    return
  fi

  printf "\n"; sep; printf "\n"
  printf "  ${G}NZT-48${N}  What do you do?\n\n"
  printf "    [1]  Freelancer / sales\n"
  printf "    [2]  Developer\n"
  printf "    [3]  Student\n"
  printf "    [4]  Other\n\n"
  ask "→ "
  read -r PROFILE_CHOICE
  case "$PROFILE_CHOICE" in
    1) PROFILE="freelancer" ;;
    2) PROFILE="developer" ;;
    3) PROFILE="student"    ;;
    *) PROFILE="other"      ;;
  esac

  ask "Your name → "
  read -r USER_NAME
  [ -z "$USER_NAME" ] && USER_NAME="User"

  ask "Brief time [09:00] → "
  read -r BRIEF_TIME
  [ -z "$BRIEF_TIME" ] && BRIEF_TIME="09:00"

  cat > "$CFG_FILE" <<EOF
user:
  name: "${USER_NAME}"
  vault: "${VAULT_PATH}"
  brief_time: "${BRIEF_TIME}"
  profile: "${PROFILE}"

monitoring:
  enabled: true
  interval_minutes: 30
  window_start: "08:00"
  window_end: "20:30"
  max_per_day: 2
EOF
  ok "config.yml written"
}

# ── smoke test + launch ───────────────────────────────────────────────────────

smoke_test() {
  printf "\n"; sep; printf "\n"
  "$VENV/bin/python" -c "import bot" 2>/dev/null \
    && ok "smoke test passed" \
    || die "import failed — check $NZT_DIR/logs/bot.log"
}

scaffold_vault() {
  "$VENV/bin/python" scaffold.py && ok "vault scaffold ensured"
}

start_bot() {
  launchctl load "$PLIST_DST" 2>/dev/null || true
  ok "bot started  (com.nzt48)"
}

count_install() {
  # anonymous install counter (README badge). One bare HTTP hit, no data.
  # Opt out: NZT_NO_TELEMETRY=1 ./install.sh
  if [ -z "${NZT_NO_TELEMETRY:-}" ]; then
    curl -s -m 5 "https://api.counterapi.dev/v1/nzt48-installs/installs/up" >/dev/null 2>&1 || true
    ok "counted (anonymous ping — NZT_NO_TELEMETRY=1 to skip)"
  else
    skip "telemetry skipped"
  fi
}

# ── run ───────────────────────────────────────────────────────────────────────

check_python
check_claude
check_ollama
detect_vault
get_telegram_token
get_telegram_uid
install_deps
pull_model
write_env
write_plist
onboarding
smoke_test
scaffold_vault
start_bot
count_install

printf "\n${G}NZT-48 is live.${N}\n"
printf "${D}Built by Euan Smith · github.com/EuanSmith2 · MIT${N}\n\n"
