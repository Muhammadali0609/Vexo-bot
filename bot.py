import os
import asyncio
import time
import contextlib
import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

from config import TOKEN
from downloader import download_tiktok

# ---------------- SETTINGS ----------------

semaphore = asyncio.Semaphore(2)

logging.basicConfig(level=logging.INFO)


# ---------------- HANDLER ----------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text

        if "tiktok.com" not in text:
            return

        asyncio.create_task(process_video(update, text))

    except Exception as e:
        print("HANDLER ERROR:", e)


# ---------------- PROCESS ----------------

async def process_video(update: Update, text: str):
    async with semaphore:
        msg = await update.message.reply_text("⬇️ Скачивание...")

        state = {
            "downloaded": 0,
            "total": 1,
            "speed": 0,
            "last_time": time.time()
        }

        def progress(downloaded, total, speed):
            state["downloaded"] = downloaded
            state["total"] = total or 1
            state["speed"] = speed or 0
            state["last_time"] = time.time()

        async def updater():
            last_text = ""

            try:
                while True:
                    now = time.time()
                    delta = now - state["last_time"]

                    estimated = state["downloaded"] + state["speed"] * delta
                    total = state["total"]

                    percent = min(int(estimated / total * 100), 100)

                    filled = percent // 10
                    bar = "█" * filled + "░" * (10 - filled)

                    speed_mb = state["speed"] / 1024 / 1024 if state["speed"] else 0

                    text = (
                        f"⬇️ Скачивание...\n\n"
                        f"{bar} {percent}%\n"
                        f"⚡ {speed_mb:.2f} MB/s"
                    )

                    if text != last_text:
                        try:
                            await msg.edit_text(text)
                            last_text = text
                        except:
                            pass

                    await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                return
            except Exception as e:
                print("UPDATER ERROR:", e)

        task = asyncio.create_task(updater())

        try:
            file_path = await asyncio.to_thread(
                download_tiktok,
                text,
                progress
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
            print("PROCESS ERROR:", e)

            try:
                await msg.edit_text("❌ Ошибка загрузки")
            except:
                pass


# ---------------- BOT INIT ----------------

def run():
    while True:
        try:
            app = ApplicationBuilder().token(TOKEN).build()

            app.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
            )

            print("🚀 Bot started")

            app.run_polling(
                drop_pending_updates=True,
                timeout=30,
                poll_interval=1
            )

        except Exception as e:
            print("💥 BOT CRASHED:", e)
            time.sleep(5)


# ---------------- START ----------------

if __name__ == "__main__":
    run()
