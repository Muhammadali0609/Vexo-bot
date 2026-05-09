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
        "format": "bv*[ext=mp4][vcodec^=avc1]+ba[ext=m4a]/b[ext=mp4]",
        "merge_output_format": "mp4",
        "concurrent_fragment_downloads": 1,
        "quiet": True,
        "noplaylist": True,
        "progress_hooks": [progress_hook],
        "cookiefile": "cookies.txt",
        "no_warnings": True
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
        "format": "bv*[ext=mp4][vcodec^=avc1]+ba[ext=m4a]/b[ext=mp4]",
        "merge_output_format": "mp4",
        "concurrent_fragment_downloads": 1,
        "quiet": True,
        "noplaylist": True,
        "retries": 3,
        "fragment_retries": 3,
        "progress_hooks": [progress_hook],
        "cookiefile": "cookies.txt",
        "no_warnings": True
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
        "outtmpl": file_name,

        # 💥 SAFE LOW QUALITY STRATEGY
        # берём максимум 480p, если нет — что есть
        "format": "best[height<=480]/worst[ext=mp4]/best",

        # 💥 важно для стабильности TikTok/Instagram
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,

        # 💥 меньше нагрузка = быстрее и стабильнее
        "concurrent_fragment_downloads": 1,

        # 💥 защита от зависаний
        "retries": 3,
        "fragment_retries": 3,
    }

    def run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return file_name

    try:
        return await asyncio.to_thread(run)
    except Exception as e:
        print("LOW QUALITY FAIL:", e)
        return None

async def try_yt_dlp_with_format(url: str, fmt: str):
    file_name = f"downloads/{uuid.uuid4()}.mp4"
    os.makedirs("downloads", exist_ok=True)

    ydl_opts = {
        "outtmpl": file_name,
        "format": fmt,
        "merge_output_format": "mp4",
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
            # 💥 STEP 1: получаем инфо БЕЗ скачивания
            def get_info():
                import yt_dlp
                with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
                    return ydl.extract_info(url, download=False)

            info = await asyncio.to_thread(get_info)
            formats = info.get("formats", [])
            # 🎯 STEP 2: ищем лучший формат ≤720p
            selected_format = None
            selected_size = None

            for f in formats:
                if f.get("height") and f["height"] <= 720:
                    # размер (если есть)
                    size = f.get("filesize") or f.get("filesize_approx")
                    # выбираем первый подходящий
                    if selected_format is None:
                        selected_format = f["format_id"]
                        selected_size = size

            # fallback если ничего нет
            if not selected_format:
                selected_format = "best"
                selected_size = None

            # 💥 STEP 3: если уже видно что файл большой → сразу low mode
            if selected_size and selected_size > 50 * 1024 * 1024:
                print("TOO BIG (pre-check) → LOW QUALITY MODE")

                file_path = await try_yt_dlp_with_format(
                    url,
                    "best[height<=480]/worst/best"
                )
            else:
                file_path = await try_yt_dlp_with_format(url, selected_format)

            if file_path and os.path.exists(file_path):
                return file_path

        except Exception as e:
            print(f"PRIMARY FAIL attempt {attempt + 1}:", e)
            last_error = e

        await asyncio.sleep(1.5)

    # 🥈 fallback engine
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
