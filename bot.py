import os
import re
import asyncio

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

from config import TOKEN
from downloader import download_tiktok

semaphore = asyncio.Semaphore(2)

def render_bar(percent: str):
    try:
        p = int(percent.replace("%", "").strip())
    except:
        p = 0

    filled = "█" * (p // 10)
    empty = "░" * (10 - (p // 10))

    return f"{filled}{empty} {p}%"

async def handle_message(update, context):
    text = update.message.text

    if "tiktok.com" not in text:
        return

    asyncio.create_task(process_video(update, context, text))
    
async def process_video(update, context, text):

    async with semaphore:  # 🔥 ограничение
        msg = await update.message.reply_text("⬇️ Скачивание...")

        state = {"percent": "0%", "speed": "0.00 MB/s"}

        def progress_callback(p, speed):
            if p:
                state["percent"] = p
            if speed:
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

        except Exception as e:
            task.cancel()
            await msg.edit_text("❌ Ошибка")
            print("ERROR:", e)
            
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Vexo Bot запущен 🚀")
app.run_polling()
