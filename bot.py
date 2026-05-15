import os
import asyncio
import re
import requests

from telegram import Update, InputMediaPhoto
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder,MessageHandler,CommandHandler,CallbackQueryHandler,ContextTypes,filters,)
from db import add_user, get_users_count, add_event, get_cached_video, save_cached_video, update_event_status, init_db, set_user_lang, get_user_lang, is_user_banned
from config import TOKEN, WEBHOOK_URL
from admin import adminm, admin_callback
from downloader_engine import download_manager, safe_remove, download_audio, get_video_metadata
from locales import t
from photo_downloader import download_instagram_photo, download_tiktok_photo, download_youtube_video, download_file

print("🔥 BOT STARTED")

semaphore = asyncio.Semaphore(2)
ACTIVE_TASKS = set()

# 🔥 создаём Telegram приложение
app = ApplicationBuilder().token(TOKEN).build()

def extract_url(text: str):
    urls = re.findall(r'https?://\S+', text)
    if urls:
        return urls[0]
    return None

def resolve_url(url):
    try:
        print("RESOLVING:", url)
        response = requests.get(
            url,
            allow_redirects=True,
            timeout=10,
            headers={
                "User-Agent": (
                    "Mozilla/5.0"
                )
            }
        )

        print("FINAL URL:", response.url)
        return response.url

    except Exception as e:
        print("RESOLVE URL ERROR:", e)
        return url

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
    
async def start(update, context):
    keyboard = [
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇺🇿 O‘zbek", callback_data="lang_uz")
        ]
    ]

    await update.message.reply_text(
        "🌍 Выберите язык / Tilni tanlang",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def language_handler(update, context):
    query = update.callback_query
    print("🔥 CALLBACK RECEIVED:", query.data)
    await query.answer()

    user_id = query.from_user.id

    lang = "ru"
    if query.data == "lang_uz":
        lang = "uz"

    set_user_lang(user_id, lang)

    from locales import t

    await query.edit_message_text(
        t(lang, "start")
    )
    await query.edit_message_reply_markup(None)

# 🔥 обработка сообщений
async def handle_message(update, context):
    register_user(update)
    text = update.message.text or ""
    url = extract_url(text)
    if not url:
        return
        
    print("URL BEFORE:", url)
    url = resolve_url(url)
    print("URL AFTER:", url)
    
    if not is_valid_link(url):
        return

    user_id = update.effective_user.id
    if is_user_banned(user_id):
        return
    lang = get_user_lang(user_id) or "ru"
    platform = detect_platform(url)
    # 📊 2. лог события
    event_id = add_event(user_id, url, platform, "pending")
    # 🚀 3. запускаем обработку
    asyncio.create_task(
        process_video(update, context, url, user_id, platform, event_id)
    )
    
async def process_video(update, context, url, user_id, platform, event_id):
    lang = get_user_lang(user_id) or "ru"
    task_id = id(update)
    ACTIVE_TASKS.add(task_id)
    msg = await update.message.reply_text(t(lang, "loading"))
    success = False

    try:
        # 🧠 1. CACHE CHECK
        cached = get_cached_video(url)

        if cached:
            video_file_id, audio_file_id = cached
            
            await update.message.reply_video(
                video=video_file_id,
                caption=t(lang, "caption")
            )

            if audio_file_id:
                await update.message.reply_audio(
                    audio=audio_file_id
                )
            update_event_status(event_id, "success")
            success = True
            return

        # 📸 PHOTO POSTS
        photo_result = None

        if platform == "instagram":
            photo_result = await download_instagram_photo(url)
        elif platform == "tiktok":
            photo_result = await download_tiktok_photo(url)
        if photo_result:
            if isinstance(photo_result, list):
                media = []
                for i, img in enumerate(photo_result):
                    if i == 0:
                        media.append(
                            InputMediaPhoto(
                                media=img,
                                caption=t(lang, "caption")
                            ) 
                        )
                    else:
                        media.append(
                            InputMediaPhoto(media=img)
                        )
                await update.message.reply_media_group(media)
            else:
                await update.message.reply_photo(
                    photo=photo_result,
                    caption=t(lang, "caption")
                )
            update_event_status(event_id, "success")
            success = True
            return

        if platform == "youtube":

            video_url = await download_youtube_video(url)
        
            if not video_url:
                await msg.edit_text(t(lang, "error"))
                return
        
            file_path = await download_file(video_url)
        
            sent_msg = await update.message.reply_video(
                video=file_path,
                caption=t(lang, "caption"),
                supports_streaming=True
            )
        
            video_file_id = sent_msg.video.file_id
        
            save_cached_video(
                url,
                video_file_id,
                None,
                platform
            )
        
            safe_remove(file_path)
        
            update_event_status(event_id, "success")
            success = True
            return
            
        # 🚀 2. DOWNLOAD VIDEO
        async with semaphore:
            file_path = await download_manager(url, platform)

        if not file_path:
            await msg.edit_text(t(lang, "error"))
            return

        # 📤 3. SEND VIDEO
        width, height = get_video_metadata(file_path)

        sent_msg = await update.message.reply_video(
            video=file_path,
            caption=t(lang, "caption"),
            width=width,
            height=height,
            supports_streaming=True
        )
        video_file_id = sent_msg.video.file_id
        
        audio_file_id = None

        is_youtube_shorts = (
            platform == "youtube"
            and "/shorts/" in url
        )
        
        audio_path = None
        
        if not is_youtube_shorts:
            audio_path = await download_audio(url)
        
        if audio_path and os.path.exists(audio_path):
            sent_audio = await update.message.reply_audio(
                audio=audio_path
            )

            audio_file_id = sent_audio.audio.file_id
            safe_remove(audio_path)

        save_cached_video(
            url,
            video_file_id,
            audio_file_id,
            platform
        )
        safe_remove(file_path)
        update_event_status(event_id, "success")
        success = True

    except Exception as e:
        print("PROCESS ERROR:", e)

        update_event_status(event_id, "error")
        
        try:
            await msg.edit_text(t(lang, "error"))
        except:
            await update.message.reply_text(t(lang, "error"))
    finally:
        ACTIVE_TASKS.discard(task_id)
        if success:
            try:
                await msg.delete()
            except Exception as e:
                print("DELETE ERROR:", e)
            
# 🔥 регистрируем handler
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CommandHandler("adminm", adminm))
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(language_handler, pattern="^lang_"))
app.add_handler(CallbackQueryHandler(admin_callback))

async def post_init(app):
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.bot.set_webhook(WEBHOOK_URL)

    print("🚀 webhook set")

def main():
    init_db()
    port = int(os.environ.get("PORT", 8080))
    app.post_init = post_init
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path="webhook",
        webhook_url=WEBHOOK_URL,
    )

if __name__ == "__main__":
    main()
