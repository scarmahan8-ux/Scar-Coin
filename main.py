import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import load_settings
from db import Database

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("mydgn-admin-bot")
settings = load_settings()
db = Database(settings.database_path)


def is_admin(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id in settings.admin_ids)


async def deny(update: Update):
    if update.effective_message:
        await update.effective_message.reply_text("این ربات خصوصی است و فقط مدیر مجاز به استفاده است.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    await update.effective_message.reply_text(
        "پنل مدیریتی آزمایشی فعال است.\n\n"
        "/help راهنما\n"
        "/addnote console عنوان | توضیحات\n"
        "/addnote pc عنوان | توضیحات\n"
        "/orders آخرین یادداشت‌ها\n"
        "/summary خلاصه وضعیت\n"
        "/myid نمایش شناسه تلگرام\n\n"
        "توجه: هنوز به API سایت myDGN متصل نیست."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    await update.effective_message.reply_text(f"شناسه تلگرام شما: {update.effective_user.id}")


async def addnote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    raw = " ".join(context.args)
    if len(context.args) < 2 or context.args[0].lower() not in {"pc", "console"}:
        return await update.effective_message.reply_text(
            "فرمت صحیح:\n/addnote console عنوان | توضیحات\n/addnote pc عنوان | توضیحات"
        )
    platform = context.args[0].lower()
    payload = raw[len(context.args[0]):].strip()
    parts = payload.split("|", 1)
    title = parts[0].strip()
    details = parts[1].strip() if len(parts) > 1 else ""
    if not title:
        return await update.effective_message.reply_text("عنوان نمی‌تواند خالی باشد.")
    note_id = db.add_note(platform, title, details)
    await update.effective_message.reply_text(f"ثبت شد. شماره یادداشت: #{note_id}")


async def orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    rows = db.list_notes()
    if not rows:
        return await update.effective_message.reply_text("هنوز موردی ثبت نشده است.")
    lines = ["آخرین موارد ثبت‌شده:"]
    for r in rows:
        lines.append(f"#{r['id']} | {r['platform'].upper()} | {r['title']} | {r['state']}")
        if r["details"]:
            lines.append(f"  {r['details'][:180]}")
    await update.effective_message.reply_text("\n".join(lines))


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    rows = db.summary()
    if not rows:
        return await update.effective_message.reply_text("داده‌ای برای گزارش وجود ندارد.")
    lines = ["خلاصه ثبت‌ها:"]
    for r in rows:
        lines.append(f"{r['platform'].upper()} / {r['state']}: {r['n']}")
    await update.effective_message.reply_text("\n".join(lines))


def main():
    app = Application.builder().token(settings.telegram_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("addnote", addnote))
    app.add_handler(CommandHandler("orders", orders))
    app.add_handler(CommandHandler("summary", summary))

    port = int(os.environ.get("PORT", "10000"))
    webhook_url = f"{settings.render_external_url}/telegram"
    log.info("Starting Telegram webhook server on port %s", port)
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path="telegram",
        webhook_url=webhook_url,
        secret_token=settings.webhook_secret,
        drop_pending_updates=False,
    )


if __name__ == "__main__":
    main()
