import os
import asyncio

from telegram import Update
from telegram.ext import (ApplicationBuilder,MessageHandler,CommandHandler,CallbackQueryHandler,ContextTypes,filters,)
from db import add_user, get_users_count, add_event
from config import TOKEN, WEBHOOK_URL
from downloader import download_video
from admin import adminm, admin_callback

# 🔥 лимит параллельных загрузок
semaphore = asyncio.Semaphore(2)

# 🔥 создаём Telegram приложение
app = ApplicationBuilder().token(TOKEN).build()

def register_user(update):
    user = update.effective_user

    user_id = user.id
    username = user.username
    first_name = user.first_name

    add_user(user_id, username, first_name)
    
def is_valid_link(text: str):
    if not text:
        return False

    return any(domain in text for domain in [
        "tiktok.com",
        "youtube.com",
        "youtu.be",
        "instagram.com"
    ])
    
def detect_platform(text: str):
    if "tiktok.com" in text:
        return "tiktok"
    if "youtube.com" in text or "youtu.be" in text:
        return "youtube"
    if "instagram.com" in text:
        return "instagram"
    return "unknown"
    
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update)
    await update.message.reply_text(
        "👋 Welcome to Vexo\n\n"
        "📥 Send TikTok / YouTube / Instagram link"
    )
# 🔥 обработка сообщений
async def handle_message(update, context):
    register_user(update)
    text = update.message.text or ""
    if not is_valid_link(text):
        return
    
    if not any(x in text for x in ["tiktok.com", "youtube.com", "youtu.be", "instagram.com"]):
        return

    user_id = update.effective_user.id
    platform = detect_platform(text)

    # 🔥 создаём запись события (pending)
    add_event(user_id, text, platform, "pending")

    asyncio.create_task(process_video(update, context, text, user_id, platform))
    
async def process_video(update, context, text, user_id, platform):
    async with semaphore:
        msg = await update.message.reply_text("⏳")
        try:
            file_path = await asyncio.to_thread(download_video, text)
            if not file_path:
                raise Exception("Empty file path")

            with open(file_path, "rb") as video:
                await update.message.reply_video(video=video)

            await msg.delete()
            os.remove(file_path)
            add_event(user_id, text, platform, "success")

        except Exception as e:
            print("DOWNLOAD ERROR:", repr(e))
            await msg.edit_text("❌ Ошибка загрузки")
            add_event(user_id, text, platform, "error")
            
# 🔥 регистрируем handler
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CommandHandler("adminm", adminm))
app.add_handler(CallbackQueryHandler(admin_callback))
app.add_handler(CommandHandler("start", start))

async def post_init(app):
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.bot.set_webhook(WEBHOOK_URL)

    print("🚀 webhook set")

def main():
    port = int(os.environ.get("PORT", 10000))
    app.post_init = post_init
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path="webhook",
        webhook_url=WEBHOOK_URL,
    )

if __name__ == "__main__":
    main()