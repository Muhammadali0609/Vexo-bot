import os
import asyncio

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

from config import TOKEN
from downloader import download_tiktok

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
    text = update.message.text

    if "tiktok.com" not in text:
        await update.message.reply_text("📎 Отправь TikTok ссылку")
        return

    msg = await update.message.reply_text("⬇️ Подготовка загрузки...")

    # сюда будет приходить реальный прогресс
    state = {"percent": "0%"}

    def progress_callback(p, speed):
        state["percent"] = p
        state["speed"] = speed

    async def progress_updater():
        last = ""
        while True:
            if state["percent"] != last:
                last = state["percent"]
                await msg.edit_text(
                    f"⬇️ Скачивание...\n\n"
                    f"{render_bar(state['percent'])}\n"
                    f"⚡ {state['speed']}"
                )

            await asyncio.sleep(0.8)

    try:
        # запускаем обновление прогресса
        task = asyncio.create_task(progress_updater())

        # реальная загрузка (не блокирует event loop)
        file_path = await asyncio.to_thread(
            download_tiktok,
            text,
            progress_callback
        )

        task.cancel()

        await msg.edit_text("⬆️ Отправка видео...")

        with open(file_path, "rb") as video:
            await update.message.reply_video(video=video)

        await msg.delete()

        os.remove(file_path)

    except Exception:
        await msg.edit_text("❌ Ошибка загрузки")

    finally:
        if not task.done():
            task.cancel()


# 🔥 запуск бота
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Vexo Bot запущен 🚀")
app.run_polling()
