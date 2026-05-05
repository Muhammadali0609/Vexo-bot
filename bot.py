import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

from config import TOKEN
from downloader import download_tiktok


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "tiktok.com" not in text:
        await update.message.reply_text("Отправь TikTok ссылку 📎")
        return

    status_msg = await update.message.reply_text("Скачиваю видео... ⏳")

    try:
        # 🔥 ВАЖНО: уводим блокирующий код в отдельный поток
        file_path = await asyncio.to_thread(download_tiktok, text)

        with open(file_path, "rb") as video:
            await update.message.reply_video(video=video)

        await status_msg.delete()

        os.remove(file_path)

    except Exception as e:
        await status_msg.edit_text("Ошибка, попробуйте еще раз ❌")


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Vexo Bot запущен...")
app.run_polling()
