import asyncio
import os
import uuid
import yt_dlp
from db import get_cached_video, save_cached_video

# =========================
# 🔥 PRIMARY YT-DLP
# =========================
async def try_yt_dlp(url: str):
    file_name = f"downloads/{uuid.uuid4()}.mp4"

    os.makedirs("downloads", exist_ok=True)

    ydl_opts = {
        "outtmpl": file_name,
        "format": "mp4/best",
        "quiet": True,
        "noplaylist": True,
    }

    def run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return file_name

    return await asyncio.to_thread(run)


# =========================
# 🔁 RETRY (slightly different config)
# =========================
async def try_yt_dlp_alt(url: str):
    file_name = f"downloads/{uuid.uuid4()}_alt.mp4"

    os.makedirs("downloads", exist_ok=True)

    ydl_opts = {
        "outtmpl": file_name,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "noplaylist": True,
        "retries": 3,
        "fragment_retries": 3,
    }

    def run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return file_name

    return await asyncio.to_thread(run)


# =========================
# 🧠 MAIN ENGINE (FALLBACK CHAIN)
# =========================
async def download_manager(url: str):
    try:
        file_path = await try_yt_dlp(url)
        if file_path and os.path.exists(file_path):
            return file_path
    except Exception as e:
        print("PRIMARY FAIL:", e)

    try:
        file_path = await try_yt_dlp_alt(url)
        if file_path and os.path.exists(file_path):
            return file_path
    except Exception as e:
        print("ALT FAIL:", e)

    return None

# =========================
# 🧹 CLEANUP HELPER (optional later use)
# =========================
def safe_remove(file_path: str):
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print("CLEANUP ERROR:", e)