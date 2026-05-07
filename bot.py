import os
import asyncio

from telegram import Update
from telegram.ext import (ApplicationBuilder,MessageHandler,CommandHandler,CallbackQueryHandler,ContextTypes,filters,)

from config import TOKEN, WEBHOOK_URL
from downloader import download_video

from admin import adminm, admin_callback

# 🔥 лимит параллельных загрузок
semaphore = asyncio.Semaphore(2)

# 🔥 создаём Telegram приложение
app = ApplicationBuilder().token(TOKEN).build()

# 🔥 обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    # 1. игнорируем команды (ВАЖНО)
    if text.startswith("/"):
        return
    # 2. список поддерживаемых платформ
    platforms = ("tiktok.com", "instagram.com", "youtube.com", "youtu.be")
    # 3. проверяем есть ли ссылка
    if not any(domain in text for domain in platforms):
        return
    # 4. запускаем загрузку
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
app.add_handler(CommandHandler("adminm", adminm))
app.add_handler(CallbackQueryHandler(admin_callback))

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