"""NZT-48 entrypoint — the bot lives in transports/telegram.py now.
This shim keeps `python bot.py`, the launchd plist, and every
`from bot import dispatch, send` (voice.py, doc_intake.py) working."""
from transports.telegram import (dispatch, generalist_reply, handle_envelope,  # noqa: F401
                                 local_reply, main, send)

if __name__ == "__main__":
    main()
