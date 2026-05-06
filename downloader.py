import os
import yt_dlp
import time

BASE_DIR = os.path.dirname(__file__)
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

os.makedirs(DOWNLOADS_DIR, exist_ok=True)


def download_tiktok(url: str, progress_callback=None):

    def hook(d):
        if d['status'] == 'downloading':
            if progress_callback:
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 1)
                speed = d.get("speed", 0)
    
                progress_callback(downloaded, total, speed)

    last_error = None

    ydl_opts = {
        "outtmpl": os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s"),
        "format": "best[ext=mp4]/best",
        "quiet": True,
        "progress_hooks": [hook],
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        },

        # 🔥 ключ к стабильности
        "retries": 10,
        "fragment_retries": 10,
        "socket_timeout": 40,
        "concurrent_fragment_downloads": 3,
        "tls_verify": False,
        "extractor_retries": 5,
        "sleep_interval": 1,
        "max_sleep_interval": 5,
    }

    for i in range(5):  # больше попыток
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        except Exception as e:
            last_error = e

            print(f"[Vexo] Retry {i+1}: {e}")

            # 🔥 важный момент — пауза растёт
            time.sleep(1.5 * (i + 1))

    raise Exception(f"Failed after retries: {last_error}")
