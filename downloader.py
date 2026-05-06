import os
import time
import yt_dlp

BASE_DIR = os.path.dirname(__file__)
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

os.makedirs(DOWNLOADS_DIR, exist_ok=True)


# 🔥 базовые настройки (общие для всех)
BASE_OPTS = {
    "outtmpl": os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s"),
    "quiet": True,
    "noplaylist": True,

    # стабильность
    "retries": 5,
    "fragment_retries": 5,
    "socket_timeout": 30,

    # меньше ошибок SSL
    "nocheckcertificate": True,
}


# 🔥 TikTok
TIKTOK_OPTS = {
    **BASE_OPTS,
    "format": "best[ext=mp4]/best",
    "http_headers": {
        "User-Agent": "Mozilla/5.0"
    },
}


# 🔥 Instagram
INSTAGRAM_OPTS = {
    **BASE_OPTS,
    "format": "best",
    "http_headers": {
        "User-Agent": "Mozilla/5.0"
    },
    # можно добавить cookies позже
}


# 🔥 YouTube
YOUTUBE_OPTS = {
    **BASE_OPTS,
    "format": "bestvideo+bestaudio/best",
    "merge_output_format": "mp4",
}


# 🔥 определяем платформу
def get_opts(url: str):
    url = url.lower()

    if "tiktok.com" in url:
        return TIKTOK_OPTS

    elif "instagram.com" in url:
        return INSTAGRAM_OPTS

    elif "youtube.com" in url or "youtu.be" in url:
        return YOUTUBE_OPTS

    else:
        return BASE_OPTS


# 🔥 главная функция
def download_video(url: str):
    opts = get_opts(url)

    last_error = None

    for i in range(3):  # 3 попытки
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        except Exception as e:
            last_error = e
            print(f"[Downloader] Retry {i+1}: {e}")

            # небольшая задержка
            time.sleep(1.5 * (i + 1))

    raise Exception(f"Download failed: {last_error}")