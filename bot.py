import os
import asyncio

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

from config import TOKEN
from downloader import download_tiktok  # используем как универсальный downloader

lock = asyncio.Lock()


def is_supported_url(text: str) -> bool:
    return any(domain in text for domain in [
        "tiktok.com",
        "youtube.com",
        "youtu.be",
        "instagram.com"
    ])


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if not text or not is_supported_url(text):
        return

    asyncio.create_task(process_video(update, text))


async def process_video(update: Update, text: str):
    async with lock:
        msg = await update.message.reply_text("⏳")

        try:
            # 🔥 скачивание в отдельном потоке
            file_path = await asyncio.to_thread(download_tiktok, text)

            # отправка видео
            with open(file_path, "rb") as video:
                await update.message.reply_video(video=video)

            # удалить "⏳"
            await msg.delete()

            # очистка файла
            if os.path.exists(file_path):
                os.remove(file_path)

        except Exception as e:
            print("ERROR:", e)
            try:
                await msg.edit_text("❌ не удалось скачать")
            except:
                pass


# =========================
# 🚀 запуск
# =========================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot started 🚀")

app.run_polling(drop_pending_updates=True)
