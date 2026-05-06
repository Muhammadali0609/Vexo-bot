import os
import re
import asyncio
import time
import contextlib

from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

from config import TOKEN
from config import WEBHOOK_URL
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

    task = asyncio.create_task(process_video(update, context, text))

    def log_task_result(t):
        try:
            t.result()
        except Exception as e:
            print("TASK ERROR:", e)
    
    task.add_done_callback(log_task_result)
    
async def process_video(update, context, text):
    await asyncio.sleep(0.3)
    async with semaphore:  # 🔥 ограничение
        msg = await update.message.reply_text("⬇️ Скачивание...")

        state = {
            "downloaded": 0,
            "total": 1,
            "speed": 0,
            "last_update": time.time()
        }

        def progress_callback(downloaded, total, speed):
            state["downloaded"] = downloaded
            state["total"] = total or 1
            state["speed"] = speed or 0
            state["last_update"] = time.time()

        async def updater():
            last_text = ""
            try:
                while True:
                    now = time.time()
    
                    delta = now - state["last_update"]
    
                    estimated = state["downloaded"] + state["speed"] * delta
                    total = state["total"]
            
                    percent = min(estimated / total * 100, 100)
    
                    filled = int(percent // 10)
                    bar = "█" * filled + "░" * (10 - filled)
            
                    # скорость
                    speed_mb = state["speed"] / 1024 / 1024
                    
                    text = (
                        f"⬇️ Скачивание...\n\n"
                        f"{bar} {percent:.1f}%\n"
                        f"⚡ {speed_mb:.2f} MB/s"
                    )
    
                    if text != last_text:
                        try:
                            await msg.edit_text(text)
                            last_text = text
                        except:
                            pass
            
                    await asyncio.sleep(0.3)
            except asyncio.CancelledError:
                return
            except Exception as e:
                print("UPDATER ERROR:", e)     
                
        task = asyncio.create_task(updater())

        try:
            file_path = await asyncio.to_thread(
                download_tiktok,
                text,
                progress_callback
            )

            task.cancel()
            with contextlib.suppress(Exception):
                await task
                
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

async def webhook_handler(request):
    data = await request.json()
    update = Update.de_json(data, app.bot)
    await app.process_update(update)
    return web.Response()

async def main():
    await app.initialize()
    await app.bot.set_webhook(WEBHOOK_URL)

    server = web.Application()
    server.router.add_post("/webhook", webhook_handler)

    runner = web.AppRunner(server)
    await runner.setup()

    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print("Bot started")

    await asyncio.Event().wait()
    
if __name__ == "__main__":
    asyncio.run(main())
