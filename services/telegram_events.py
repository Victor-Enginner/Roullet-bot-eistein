import os
from typing import Dict, Optional


EVENT_STICKER_ENV: Dict[str, str] = {
    "NEW_NUMBER": "TELEGRAM_STICKER_NEW_NUMBER",
    "SIGNAL": "TELEGRAM_STICKER_SIGNAL",
    "WIN_ENTRY": "TELEGRAM_STICKER_WIN_ENTRY",
    "WIN_PROTECTION": "TELEGRAM_STICKER_WIN_PROTECTION",
    "PROTECTION": "TELEGRAM_STICKER_PROTECTION",
    "LOSS": "TELEGRAM_STICKER_LOSS",
    "TURBULENCE": "TELEGRAM_STICKER_TURBULENCE",
    "NORMALIZED": "TELEGRAM_STICKER_NORMALIZED",
    "MESSY_TERMINALS": "TELEGRAM_STICKER_MESSY_TERMINALS",
    "HOT_STRATEGY": "TELEGRAM_STICKER_HOT_STRATEGY",
    "ANALYTICS": "TELEGRAM_STICKER_ANALYTICS",
    "PATTERN": "TELEGRAM_STICKER_PATTERN",
}


def get_sticker_id(event_key: str) -> Optional[str]:
    env_name = EVENT_STICKER_ENV.get(event_key)
    if not env_name:
        return None

    value = os.getenv(env_name, "").strip()
    return value or None


def is_sticker_enabled() -> bool:
    return os.getenv("TELEGRAM_SEND_STICKERS", "false").lower() == "true"
