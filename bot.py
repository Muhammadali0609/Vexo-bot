import os
import asyncio

from telegram import Update
from telegram.ext import (ApplicationBuilder,MessageHandler,CommandHandler,CallbackQueryHandler,ContextTypes,filters,)
from db import add_user, get_users_count, add_event, get_cached_video, save_cached_video, migrate_video_cache
from config import TOKEN, WEBHOOK_URL
from admin import adminm, admin_callback
from downloader_engine import download_manager, safe_remove

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
    # 🚫 1. проверка ссылки
    if not is_valid_link(text):
        return

    user_id = update.effective_user.id
    platform = detect_platform(text)
    # 📊 2. лог события
    add_event(user_id, text, platform, "pending")
    # 🚀 3. запускаем обработку
    asyncio.create_task(
        process_video(update, context, text, user_id, platform)
    )
    
async def process_video(update, context, url, user_id, platform):
    msg = await update.message.reply_text("⏳")

    try:
        # 🧠 1. CACHE CHECK (file_id)
        file_id = get_cached_video(url)
        if file_id:
            await update.message.reply_video(video=file_id)
            await msg.delete()
            return
        # 🚀 2. DOWNLOAD (only first time)
        file_path = await download_manager(url, platform)
        if not file_path:
            await msg.edit_text("⚠️ Video not available")
            return
        # 📤 3. SEND TO TELEGRAM
        with open(file_path, "rb") as video:
            sent_msg = await update.message.reply_video(video=video)
        # 💾 4. SAVE file_id
        file_id = sent_msg.video.file_id
        save_cached_video(url, file_id, platform)
        await msg.delete()

    except Exception as e:
        print("PROCESS ERROR:", e)
        await msg.edit_text("❌ Error while processing video")
            
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
    migrate_video_cache()
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