import asyncio
import os
import uuid
import yt_dlp
from db import get_cached_video, save_cached_video

# =========================
# 🔥 PRIMARY YT-DLP
# =========================
def progress_hook(d):
    if d['status'] == 'finished':
        print("DONE:", d['filename'])

async def try_yt_dlp(url: str):
    file_name = f"downloads/{uuid.uuid4()}.%(ext)s"

    os.makedirs("downloads", exist_ok=True)

    ydl_opts = {
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "format": "best",
        "concurrent_fragment_downloads": 1,
        "quiet": True,
        "noplaylist": True,
        "progress_hooks": [progress_hook],
    }

    def run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
        return file_path

    await asyncio.to_thread(run)

    # 🔥 найти реальный файл
    files = os.listdir("downloads")
    if not files:
        return None

    latest = max(
        [os.path.join("downloads", f) for f in files],
        key=os.path.getctime
    )

    return latest


# =========================
# 🔁 RETRY (slightly different config)
# =========================
async def try_yt_dlp_alt(url: str):
    file_name = f"downloads/{uuid.uuid4()}_alt.mp4"

    os.makedirs("downloads", exist_ok=True)

    ydl_opts = {
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "concurrent_fragment_downloads": 1,
        "quiet": True,
        "noplaylist": True,
        "retries": 3,
        "fragment_retries": 3,
        "progress_hooks": [progress_hook]
    }

    def run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
        return file_path

    return await asyncio.to_thread(run)

async def try_low_quality(url: str):
    file_name = f"downloads/{uuid.uuid4()}.mp4"

    os.makedirs("downloads", exist_ok=True)

    ydl_opts = {
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "format": "best[height<=720]",
        "quiet": True,
        "noplaylist": True,
    }

    def run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return file_name

    return await asyncio.to_thread(run)

async def download_audio(url: str):
    file_name = f"downloads/{uuid.uuid4()}.mp3"

    os.makedirs("downloads", exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": file_name,
        "quiet": True,
        "noplaylist": True,
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
    last_error = None

    for attempt in range(3):
        try:
            print(f"TRY {attempt + 1}/3")
            file_path = await try_yt_dlp(url)
            if file_path and os.path.exists(file_path):
                size_mb = get_file_size_mb(file_path)
                print(f"FILE SIZE: {size_mb:.2f}MB")

                # 💥 если слишком большой → сразу 720p fallback
                if size_mb > 50:
                    print("TOO BIG → SWITCH 720P")
                    safe_remove(file_path)
                    low_file = await try_low_quality(url)
                    return low_file if low_file and os.path.exists(low_file) else None

                return file_path

        except Exception as e:
            print(f"PRIMARY FAIL attempt {attempt + 1}:", e)
            last_error = e

        # ⏳ retry delay (важная часть)
        await asyncio.sleep(1.5)

    # 🥈 fallback engine после 3 неудач
    try:
        print("TRY ALT ENGINE")
        return await try_yt_dlp_alt(url)

    except Exception as e:
        print("ALT FAIL:", e)
        last_error = e

    print("ALL FAILED:", last_error)
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
        
def get_file_size_mb(file_path):
    size = os.path.getsize(file_path)
    return size / (1024 * 1024)
