import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    telegram_token: str
    admin_ids: set[int]
    database_path: str

def load_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or token == "put_your_telegram_bot_token_here":
        raise RuntimeError("TELEGRAM_BOT_TOKEN را در فایل .env تنظیم کنید.")
    raw_ids = os.getenv("ADMIN_IDS", "").strip()
    admin_ids = {int(x.strip()) for x in raw_ids.split(",") if x.strip()}
    if not admin_ids:
        raise RuntimeError("حداقل یک شناسه عددی تلگرام در ADMIN_IDS وارد کنید.")
    return Settings(
        telegram_token=token,
        admin_ids=admin_ids,
        database_path=os.getenv("DATABASE_PATH", "data/bot.sqlite3"),
    )
