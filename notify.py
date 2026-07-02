"""Send Telegram messages outside the bot loop (monitors, brief cron)."""
import requests

from config import TELEGRAM_TOKEN, TELEGRAM_USER_ID


def send(text: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_USER_ID:
        print("[notify] telegram not configured:\n" + text)
        return False
    try:
        for i in range(0, len(text), 3900):
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_USER_ID, "text": text[i:i + 3900]},
                timeout=15,
            ).raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"[notify] failed: {e}")
        return False
