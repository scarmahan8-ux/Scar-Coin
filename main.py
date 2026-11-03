import asyncio
import hashlib
import logging
import os
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import load_settings
from db import Database
from mydgn_api import MyDGNClient, MyDGNError

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("mydgn-admin-bot")
settings = load_settings()
db = Database(settings.database_path)
mydgn = MyDGNClient(settings.mydgn_user, settings.mydgn_secret_key)


def is_admin(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id in settings.admin_ids)


async def deny(update: Update):
    if update.effective_message:
        await update.effective_message.reply_text("این ربات خصوصی است و فقط مدیر مجاز به استفاده است.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    await update.effective_message.reply_text(
        "پنل مدیریتی فعال است.\n\n"
        "/help راهنما\n"
        "/checkorders دریافت یک سفارش کنسول از myDGN\n"
        "/orders آخرین سفارش‌ها و یادداشت‌ها\n"
        "/summary خلاصه وضعیت\n"
        "/myid نمایش شناسه تلگرام\n\n"
        "پلتفرم: فقط کنسول | نوع: Basic | بازه قیمت: ۰ تا ۴۰۰۰\n"
        "خرید بازیکن باید دستی انجام شود؛ این ربات داخل بازی خرید نمی‌کند."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    await update.effective_message.reply_text(f"شناسه تلگرام شما: {update.effective_user.id}")


async def checkorders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    msg = await update.effective_message.reply_text("در حال بررسی سفارش کنسول در myDGN...")
    try:
        order = await asyncio.to_thread(mydgn.get_transfer)
    except MyDGNError as exc:
        await msg.edit_text(str(exc))
        return
    except Exception:
        log.exception("Unexpected error while checking myDGN")
        await msg.edit_text("خطای غیرمنتظره هنگام ارتباط با myDGN رخ داد. گزارش خطا در Render قابل بررسی است.")
        return

    txid = int(order.get("transactionID", 0) or 0)
    if not txid:
        await msg.edit_text("پاسخ myDGN شناسه تراکنش نداشت؛ سفارش ثبت نشد. لطفاً پشتیبانی myDGN را بررسی کنید.")
        return
    is_new = db.save_order(txid, order)
    if not is_new:
        await msg.edit_text(f"این سفارش قبلاً دریافت شده است. شماره تراکنش: {txid}\nبرای جلوگیری از ثبت تکراری، دوباره نمایش داده نشد.")
        return

    name = str(order.get("playerName", "نامشخص"))
    search_name = str(order.get("search_name", name))
    lock_expires = int(order.get("lockExpires", 0) or 0)
    remaining = max(0, lock_expires - int(time.time())) if lock_expires else 0
    mins, secs = divmod(remaining, 60)
    text = (
        "🟢 سفارش جدید کنسول دریافت شد\n\n"
        f"بازیکن: {name}\n"
        f"نام جست‌وجو: {search_name}\n"
        f"ریتینگ: {order.get('rating', '—')}\n"
        f"قیمت شروع: {order.get('startPrice', '—')}\n"
        f"قیمت خرید: {order.get('coinAmount', '—')}\n"
        f"شناسه تراکنش: {txid}\n"
        f"Trade ID: {order.get('tradeID', '—')}\n"
        f"زمان باقی‌مانده تا مهلت اعلام وضعیت: حدود {mins} دقیقه و {secs} ثانیه\n\n"
        "اکنون خرید را به‌صورت دستی انجام بده. این ربات خرید داخل بازی را انجام نمی‌دهد.\n"
        "پس از خرید یا انصراف، برای ثبت وضعیت در myDGN باید مرحله بعدی را انجام دهیم."
    )
    await msg.edit_text(text)


async def addnote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    raw = " ".join(context.args)
    if len(context.args) < 2 or context.args[0].lower() != "console":
        return await update.effective_message.reply_text("فرمت صحیح: /addnote console عنوان | توضیحات")
    payload = raw[len(context.args[0]):].strip()
    parts = payload.split("|", 1)
    title = parts[0].strip()
    details = parts[1].strip() if len(parts) > 1 else ""
    if not title:
        return await update.effective_message.reply_text("عنوان نمی‌تواند خالی باشد.")
    note_id = db.add_note("console", title, details)
    await update.effective_message.reply_text(f"ثبت شد. شماره یادداشت: #{note_id}")


async def orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    order_rows = db.list_orders()
    note_rows = db.list_notes()
    if not order_rows and not note_rows:
        return await update.effective_message.reply_text("هنوز سفارشی یا یادداشتی ثبت نشده است.")
    lines = ["آخرین سفارش‌های myDGN:"]
    for r in order_rows:
        lines.append(f"#{r['transaction_id']} | CONSOLE | {r['player_name']} | {r['coin_amount']} coins | {r['created_at']}")
    if note_rows:
        lines.append("\nیادداشت‌ها:")
        for r in note_rows:
            lines.append(f"#{r['id']} | {r['title']} | {r['state']}")
    await update.effective_message.reply_text("\n".join(lines)[:4000])


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    rows = db.summary()
    orders_count = db.order_count()
    lines = [f"تعداد سفارش‌های دریافت‌شده از myDGN: {orders_count}"]
    if rows:
        lines.append("یادداشت‌ها:")
        for r in rows:
            lines.append(f"{r['platform'].upper()} / {r['state']}: {r['n']}")
    await update.effective_message.reply_text("\n".join(lines))


def main():
    app = Application.builder().token(settings.telegram_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("addnote", addnote))
    app.add_handler(CommandHandler("checkorders", checkorders))
    app.add_handler(CommandHandler("orders", orders))
    app.add_handler(CommandHandler("summary", summary))

    port = int(os.environ.get("PORT", "10000"))
    webhook_url = f"{settings.render_external_url}/telegram"
    log.info("Starting Telegram webhook server on port %s", port)
    app.run_webhook(
        listen="0.0.0.0", port=port, url_path="telegram", webhook_url=webhook_url,
        secret_token=settings.webhook_secret, drop_pending_updates=False,
    )


if __name__ == "__main__":
    main()
