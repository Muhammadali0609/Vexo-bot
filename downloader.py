import os
import yt_dlp

BASE_DIR = os.path.dirname(__file__)
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

os.makedirs(DOWNLOADS_DIR, exist_ok=True)


def download_tiktok(url: str) -> str:
    """
    Скачивает видео и возвращает путь к файлу.
    Максимально стабильная версия без прогресс-колбэков.
    """

    ydl_opts = {
        "outtmpl": os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s"),
        "format": "best[ext=mp4]/best",
        "quiet": True,

        # 🔥 стабильность сети
        "retries": 10,
        "fragment_retries": 10,
        "socket_timeout": 40,
        "extractor_retries": 5,

        # 🔥 TikTok/анти-блок
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        },

        # 🔥 чуть стабильнее разбор
        "nocheckcertificate": True,
    }

    last_error = None

    for i in range(3):  # 3 попытки достаточно
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                return file_path

        except Exception as e:
            last_error = e
            print(f"[Downloader] retry {i + 1}: {e}")

    raise Exception(f"Download failed: {last_error}")
