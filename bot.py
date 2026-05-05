import os
import re
import asyncio

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

from config import TOKEN
from downloader import download_tiktok

is_downloading = False

def extract_video_id(url):
    match = re.search(r'/video/(\d+)', url)
    if match:
        return match.group(1)
    return url

def render_bar(percent: str):
    try:
        p = int(percent.replace("%", "").strip())
    except:
        p = 0

    filled = "█" * (p // 10)
    empty = "░" * (10 - (p // 10))

    return f"{filled}{empty} {p}%"

# 🔥 прогресс будет обновлять это сообщение
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_downloading
    text = update.message.text

    if "tiktok.com" not in text:
        return
    if is_downloading:
        return

    is_downloading = True
    
    msg = await update.message.reply_text("⬇️ Скачивание...")

    state = {"percent": "0%", "speed": "0.00 MB/s"}

    def progress_callback(p, speed):
        state["percent"] = p
        state["speed"] = speed

    async def updater():
        while True:
            try:
                await msg.edit_text(
                    f"⬇️ Скачивание...\n\n"
                    f"{render_bar(state['percent'])}\n"
                    f"⚡ {state['speed']}"
                )
            except:
                pass

            await asyncio.sleep(1)

    task = asyncio.create_task(updater())

    try:
        file_path = await asyncio.to_thread(
            download_tiktok,
            text,
            progress_callback
        )

        task.cancel()

        with open(file_path, "rb") as video:
            await update.message.reply_video(video=video)

        await msg.delete()
        os.remove(file_path)

    except Exception:
        task.cancel()
        await msg.edit_text("❌ Ошибка загрузки")
        
    finally:
        is_downloading = False
        if not task.done():
            task.cancel()


# 🔥 запуск бота
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Vexo Bot запущен 🚀")
app.run_polling()
