import os
import asyncio

from telegram import Update
from telegram.ext import (ApplicationBuilder,MessageHandler,CommandHandler,CallbackQueryHandler,ContextTypes,filters,)
from db import add_user, get_users_count, add_event, get_cached_video, save_cached_video, update_event_status
from config import TOKEN, WEBHOOK_URL
from admin import adminm, admin_callback
from downloader_engine import download_manager, safe_remove, download_audio

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
    await process_video(update, context, text, user_id, platform)
    
async def process_video(update, context, url, user_id, platform):
    msg = await update.message.reply_text("⏳")
    caption = "✅ @Vexoapp_bot"

    try:
        # 🧠 1. CACHE CHECK
        cached = get_cached_video(url)

        if cached:
            video_file_id, audio_file_id = cached

            await update.message.reply_video(
                video=video_file_id,
                caption=caption
            )

            if audio_file_id:
                await update.message.reply_audio(
                    audio=audio_file_id
                )

            await msg.delete()
            return

        # 🚀 2. DOWNLOAD VIDEO
        file_path = await download_manager(url)

        if not file_path:
            try:
                await msg.edit_text("⚠️ Видео недоступно, попробуйте снова")
            except:
                await update.message.reply_text("⚠️ Видео недоступно, попробуйте снова")
            return

        # 📤 3. SEND VIDEO
        sent_msg = await update.message.reply_video(
            video=file_path,
            caption=caption
        )

        video_file_id = sent_msg.video.file_id

        # 🎵 4. DOWNLOAD AUDIO
        audio_file_id = None

        audio_path = await download_audio(url)

        if audio_path and os.path.exists(audio_path):

            sent_audio = await update.message.reply_audio(
                audio=audio_path
            )

            audio_file_id = sent_audio.audio.file_id

            safe_remove(audio_path)

        # 💾 5. SAVE CACHE
        save_cached_video(
            url,
            video_file_id,
            audio_file_id,
            platform
        )

        # 🧹 6. DELETE VIDEO FILE
        safe_remove(file_path)
        
        update_event_status(
            user_id,
            url,
            "success"
        )
        
        await msg.delete()

    except Exception as e:
        print("PROCESS ERROR:", e)

        update_event_status(
            user_id,
            url,
            "error"
        )
        
        try:
            await msg.edit_text("⚠️ Видео недоступно, попробуйте снова")
        except:
            await update.message.reply_text("⚠️ Видео недоступно, попробуйте снова")
    finally:
        try:
            await msg.delete()
        except Exception as e:
            print("DELETE ERROR:", e)
            
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
