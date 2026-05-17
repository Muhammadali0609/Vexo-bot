import os
import asyncio
import re
import requests

from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder,MessageHandler,CommandHandler,CallbackQueryHandler,ContextTypes,filters,)
from db import add_user, get_users_count, add_event, get_cached_video, save_cached_video, update_event_status, init_db, set_user_lang, get_user_lang, is_user_banned
from config import TOKEN, WEBHOOK_URL
from admin import adminm, admin_callback
from downloader_engine import download_manager, safe_remove, download_audio, get_video_metadata
from locales import t
from photo_downloader import download_instagram_photo, download_tiktok_media

print("🔥 BOT STARTED")

semaphore = asyncio.Semaphore(2)
instagram_semaphore = asyncio.Semaphore(1)
ACTIVE_TASKS = set()

# 🔥 создаём Telegram приложение
app = ApplicationBuilder().token(TOKEN).build()

def extract_url(text: str):
    urls = re.findall(r'https?://\S+', text)
    if urls:
        return urls[0]
    return None


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

def is_instagram_story(url: str):
    return (
        "instagram.com/stories/" in url
        or "/stories/" in url
    )

def is_instagram_post(url: str):
    return (
        "instagram.com/p/" in url
        or "/p/" in url
    )

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
        
    if not is_valid_link(url):
        return

    user_id = update.effective_user.id
    if is_user_banned(user_id):
        return
    lang = get_user_lang(user_id) or "ru"
    msg = await update.message.reply_text(t(lang, "loading"))
    platform = detect_platform(url)
    # 📊 2. лог события
    event_id = add_event(user_id, url, platform, "pending")
    # 🚀 3. запускаем обработку
    asyncio.create_task(
        process_video(update, context, url, user_id, platform, event_id, msg)
    )
    
async def process_video(update, context, url, user_id, platform, event_id, msg):
    lang = get_user_lang(user_id) or "ru"
    task_id = id(update)
    ACTIVE_TASKS.add(task_id)
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
            async with instagram_semaphore:
                photo_result = await download_instagram_photo(url)
            print("PHOTO RESULT:", photo_result)
        elif platform == "tiktok":
            photo_result = await download_tiktok_media(url)
        if photo_result:
            is_local = photo_result.get("local", False)

            if photo_result.get("type") == "photos":
                photos = photo_result["data"]

                if len(photos) == 1:
                    photo = photos[0]

                    try:
                        if is_local and os.path.exists(photo):
                            with open(photo, "rb") as file:
                                await update.message.reply_photo(
                                    photo=file,
                                    caption=t(lang, "caption")
                                )
                        else:
                            await update.message.reply_photo(
                                photo=photo,
                                caption=t(lang, "caption")
                            )

                        update_event_status(event_id, "success")
                        success = True
                        return

                    finally:
                        if is_local:
                            safe_remove(photo)

                media = []
                opened_files = []

                try:
                    for i, img in enumerate(photos[:10]):
                        caption = t(lang, "caption") if i == 0 else None
                        media_value = img

                        if is_local and os.path.exists(img):
                            file = open(img, "rb")
                            opened_files.append(file)
                            media_value = file

                        media.append(
                            InputMediaPhoto(
                                media=media_value,
                                caption=caption
                            )
                        )

                    await update.message.reply_media_group(media)
                    update_event_status(event_id, "success")
                    success = True
                    return

                finally:
                    for file in opened_files:
                        file.close()

                    if is_local:
                        for img in photos:
                            safe_remove(img)

            elif photo_result.get("type") == "video":
                video_data = photo_result["data"]

                try:
                    if is_local and os.path.exists(video_data):
                        with open(video_data, "rb") as file:
                            sent_msg = await update.message.reply_video(
                                video=file,
                                caption=t(lang, "caption"),
                                supports_streaming=True
                            )
                    else:
                        sent_msg = await update.message.reply_video(
                            video=video_data,
                            caption=t(lang, "caption"),
                            supports_streaming=True
                        )

                    video_file_id = sent_msg.video.file_id
                    save_cached_video(url, video_file_id, None, platform)
                    update_event_status(event_id, "success")
                    success = True
                    return

                finally:
                    if is_local:
                        safe_remove(video_data)

            elif photo_result.get("type") == "media_group":
                media = []
                opened_files = []

                try:
                    for i, item in enumerate(photo_result["data"][:10]):
                        caption = t(lang, "caption") if i == 0 else None
                        media_value = item["url"]

                        if is_local and os.path.exists(media_value):
                            file = open(media_value, "rb")
                            opened_files.append(file)
                            media_value = file

                        if item["type"] == "video":
                            media.append(
                                InputMediaVideo(
                                    media=media_value,
                                    caption=caption
                                )
                            )
                        else:
                            media.append(
                                InputMediaPhoto(
                                    media=media_value,
                                    caption=caption
                                )
                            )

                    await update.message.reply_media_group(media)
                    update_event_status(event_id, "success")
                    success = True
                    return

                finally:
                    for file in opened_files:
                        file.close()

                    if is_local:
                        for item in photo_result["data"]:
                            safe_remove(item["url"])
        

        if platform == "instagram" and is_instagram_story(url):
            await msg.edit_text(t(lang, "story_unavailable"))
            update_event_status(event_id, "error")
            return

        if platform == "instagram" and is_instagram_post(url):
            await msg.edit_text(t(lang, "error"))
            update_event_status(event_id, "error")
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
        
        #audio_path = await download_audio(url)
        
        #if audio_path and os.path.exists(audio_path):
            #sent_audio = await update.message.reply_audio(
                #audio=audio_path
            #)

            #audio_file_id = sent_audio.audio.file_id
            #safe_remove(audio_path)

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
