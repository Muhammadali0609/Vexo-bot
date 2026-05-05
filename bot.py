import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

from config import TOKEN
from downloader import download_tiktok

async def handle_message(update, context):
    text = update.message.text

    if "tiktok.com" not in text:
        await update.message.reply_text("Отправь TikTok ссылку 📎")
        return

    # 1. отправляем статус и сохраняем сообщение
    status_msg = await update.message.reply_text("Скачиваю видео... ⏳")

    try:
        file_path = download_tiktok(text)

        # 2. отправляем видео
        await update.message.reply_video(video=open(file_path, "rb"))

        # 3. удаляем статус сообщение
        await status_msg.delete()

        os.remove(file_path)

    except Exception as e:
        await status_msg.edit_text("Ошибка, попробуйте еще раз")


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Vexo Bot запущен...")
app.run_polling()