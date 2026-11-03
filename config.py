import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    telegram_token: str
    admin_ids: set[int]
    webhook_secret: str
    database_path: str
    render_external_url: str
    mydgn_user: str
    mydgn_secret_key: str


def load_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")
    raw_ids = os.getenv("ADMIN_IDS", "").strip()
    admin_ids = {int(x.strip()) for x in raw_ids.split(",") if x.strip()}
    if not admin_ids:
        raise RuntimeError("ADMIN_IDS must contain at least one numeric Telegram user ID")
    secret = os.getenv("WEBHOOK_SECRET", "").strip()
    if len(secret) < 16:
        raise RuntimeError("WEBHOOK_SECRET must be at least 16 characters")
    base_url = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    if not base_url:
        raise RuntimeError("RENDER_EXTERNAL_URL is missing; deploy as a Render Web Service")
    mydgn_user = os.getenv("MYDGN_USER", "").strip()
    mydgn_secret_key = os.getenv("MYDGN_SECRET_KEY", "").strip()
    if not mydgn_user or not mydgn_secret_key:
        raise RuntimeError("MYDGN_USER and MYDGN_SECRET_KEY must both be set")
    return Settings(
        telegram_token=token,
        admin_ids=admin_ids,
        webhook_secret=secret,
        database_path=os.getenv("DATABASE_PATH", "/tmp/bot.sqlite3"),
        render_external_url=base_url,
        mydgn_user=mydgn_user,
        mydgn_secret_key=mydgn_secret_key,
    )
