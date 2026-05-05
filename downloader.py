import os
import time
import yt_dlp

BASE_DIR = os.path.dirname(__file__)
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

os.makedirs(DOWNLOADS_DIR, exist_ok=True)


def download_tiktok(url: str):
    ydl_opts = {
        "outtmpl": os.path.join(DOWNLOADS_DIR, "%(title)s.%(ext)s"),
        "format": "mp4",
        "quiet": True,
        "nocheckcertificate": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0"
        }
    }

    last_error = None

    for i in range(3):  # 3 попытки
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                return file_path

        except Exception as e:
            last_error = e
            print(f"Попытка {i+1} не удалась: {e}")
            time.sleep(2)

    raise Exception(f"Не удалось скачать видео: {last_error}")