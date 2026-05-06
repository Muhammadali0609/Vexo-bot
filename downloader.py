import os
import yt_dlp

BASE_DIR = os.path.dirname(__file__)
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

os.makedirs(DOWNLOADS_DIR, exist_ok=True)


def download_tiktok(url: str) -> str:
    """
    Универсальный downloader для:
    - TikTok
    - YouTube
    - Instagram
    """

    ydl_opts = {
        # 📁 куда сохраняем
        "outtmpl": os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s"),

        # 🎬 лучший mp4
        "format": "best[ext=mp4]/best",

        # 🔕 без логов
        "quiet": True,
        "noplaylist": True,

        # 🌐 стабильность сети
        "retries": 10,
        "fragment_retries": 10,
        "socket_timeout": 40,
        "extractor_retries": 5,

        # 🔐 анти-блок (очень важно для TikTok/Instagram)
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        },

        # ⚙️ стабильность парсинга
        "nocheckcertificate": True,

        # 📉 убирает лишние зависания
        "concurrent_fragment_downloads": 2,
    }

    last_error = None

    # 🔁 несколько попыток (очень важно для TikTok/IG)
    for i in range(3):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                # получаем путь к файлу
                file_path = ydl.prepare_filename(info)

                return file_path

        except Exception as e:
            last_error = e
            print(f"[Downloader] retry {i + 1}: {e}")

    raise Exception(f"Download failed after retries: {last_error}")
