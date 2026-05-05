import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

from config import TOKEN
from downloader import download_tiktok

def progress_bar(percent: int):
    filled = "█" * (percent // 10)
    empty = "░" * (10 - percent // 10)
    return f"{filled}{empty} {percent}%"
    
async def animate_loading(msg, stop_flag):
    percent = 0

    while not stop_flag["done"]:
        percent += 10
        if percent > 90:
            percent = 10

        await msg.edit_text(f"⬇️ Загрузка...\n{progress_bar(percent)}")

        await asyncio.sleep(0.8)

async def handle_message(update, context):
    text = update.message.text

    if "tiktok.com" not in text:
        await update.message.reply_text("Отправь TikTok ссылку 📎")
        return

    msg = await update.message.reply_text("⬇️ Подготовка...")

    stop_flag = {"done": False}

    # запускаем анимацию
    task = asyncio.create_task(animate_loading(msg, stop_flag))

    try:
        file_path = await asyncio.to_thread(download_tiktok, text)

        stop_flag["done"] = True
        await task

        await msg.edit_text("⬆️ Отправка видео...")

        with open(file_path, "rb") as video:
            await update.message.reply_video(video=video)

        await msg.delete()

    except Exception:
        stop_flag["done"] = True
        await msg.edit_text("❌ Ошибка загрузки")


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Vexo Bot запущен...")
app.run_polling()
