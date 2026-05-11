import asyncio
import os
import uuid
import yt_dlp

# =========================
# 🔥 HOOK (лог скачивания)
# =========================
def progress_hook(d):
    if d['status'] == 'finished':
        print("DONE:", d['filename'])


# =========================
# 🧠 PRIMARY DOWNLOAD
# =========================
async def try_yt_dlp(url: str):
    os.makedirs("downloads", exist_ok=True)

    file_name = f"downloads/{uuid.uuid4()}.mp4"

    ydl_opts = {
        "outtmpl": file_name,

        # 🔥 СТАБИЛЬНЫЙ ФОРМАТ (ВАЖНО)
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",

        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,

        "retries": 3,

        "cookiefile": "cookies.txt",
        "progress_hooks": [progress_hook],
    }

    def run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return file_name

    return await asyncio.to_thread(run)


# =========================
# 🔁 ALT DOWNLOAD (backup)
# =========================
async def try_yt_dlp_alt(url: str):
    os.makedirs("downloads", exist_ok=True)

    file_name = f"downloads/{uuid.uuid4()}_alt.mp4"

    ydl_opts = {
        "outtmpl": file_name,

        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",

        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,

        "retries": 3,

        "cookiefile": "cookies.txt",
        "progress_hooks": [progress_hook],
    }

    def run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return file_name

    return await asyncio.to_thread(run)


# =========================
# 🚀 MAIN ENGINE (SIMPLE + CLEAN)
# =========================
async def download_manager(url: str):
    last_error = None

    for attempt in range(3):
        try:
            print(f"TRY PRIMARY {attempt + 1}/3")
            file_path = await try_yt_dlp(url)

            if file_path and os.path.exists(file_path):
                return file_path

        except Exception as e:
            print("PRIMARY FAIL:", e)
            last_error = e

        await asyncio.sleep(1.5)

    # 🔁 fallback
    try:
        print("TRY ALT ENGINE")
        file_path = await try_yt_dlp_alt(url)

        if file_path and os.path.exists(file_path):
            return file_path

    except Exception as e:
        print("ALT FAIL:", e)
        last_error = e

    print("ALL FAILED:", last_error)
    return None

async def download_audio(url: str):
    os.makedirs("downloads", exist_ok=True)

    file_name = f"downloads/{uuid.uuid4()}.mp3"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": file_name,

        "quiet": True,
        "noplaylist": True,

        "cookiefile": "cookies.txt",
    }

    def run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return file_name

    return await asyncio.to_thread(run)

# =========================
# 🧹 CLEANUP
# =========================
def safe_remove(file_path: str):
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print("CLEANUP ERROR:", e)
