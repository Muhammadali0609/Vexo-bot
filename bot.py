import os
import asyncio

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

from config import TOKEN, WEBHOOK_URL
from downloader import download_video


# 🔥 лимит параллельных загрузок
semaphore = asyncio.Semaphore(2)

# 🔥 создаём Telegram приложение
app = ApplicationBuilder().token(TOKEN).build()

# 🔥 обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if not text:
        return

    if not any(x in text for x in ["tiktok.com", "instagram.com", "youtube.com", "youtu.be"]):
        return

    asyncio.create_task(process_video(update, context, text))


# 🔥 скачивание
async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    async with semaphore:
        msg = await update.message.reply_text("⏳")

        try:
            file_path = await asyncio.to_thread(download_video, url)

            with open(file_path, "rb") as video:
                await update.message.reply_video(video=video)

            await msg.delete()
            os.remove(file_path)

        except Exception as e:
            print("DOWNLOAD ERROR:", e)
            await msg.edit_text("❌ Ошибка загрузки")


# 🔥 регистрируем handler
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


async def main():
    await app.initialize()
    
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.bot.set_webhook(WEBHOOK_URL)
    print("🚀 Bot started")

    await app.updater.start_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path="webhook",
        webhook_url=WEBHOOK_URL
    )

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())