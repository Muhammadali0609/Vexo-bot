import os
import yt_dlp
import time

BASE_DIR = os.path.dirname(__file__)
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

os.makedirs(DOWNLOADS_DIR, exist_ok=True)


def download_tiktok(url: str, progress_callback=None):

    def hook(d):
        if d['status'] == 'downloading':

            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate')

            # % по байтам (самый стабильный способ)
            percent = "0%"
            if total:
                percent = f"{int(downloaded / total * 100)}%"

            speed = d.get('speed')
            if speed:
                speed = f"{speed / 1024 / 1024:.2f} MB/s"
            else:
                speed = "0.00 MB/s"

            if progress_callback:
                progress_callback(percent, speed)

    ydl_opts = {
        "outtmpl": os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s"),
        "format": "best",
        "quiet": True,
        "progress_hooks": [hook],
        "nocheckcertificate": True,
        "http_headers": {"User-Agent": "Mozilla/5.0"},
        "retries": 5,
        "fragment_retries": 5,
        "socket_timeout": 20,
    }

    last_error = None

    for i in range(3):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                return file_path

        except Exception as e:
            last_error = e
            print(f"[Vexo] Попытка {i+1} не удалась: {e}")
            time.sleep(1.5)

    raise Exception(f"Не удалось скачать видео: {last_error}")
