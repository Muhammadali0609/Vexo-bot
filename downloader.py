import os
import yt_dlp

BASE_DIR = os.path.dirname(__file__)
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


def download_tiktok(url: str, progress_callback=None):

    def hook(d):
        if d['status'] == 'downloading':
            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
            speed = d.get("speed") or 0

            if progress_callback:
                progress_callback(downloaded, total, speed)

    ydl_opts = {
        "outtmpl": os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s"),
        "format": "best[ext=mp4]/best",
        "quiet": True,

        "progress_hooks": [hook],

        "http_headers": {
            "User-Agent": "Mozilla/5.0"
        },

        # 🔥 стабильность (без перегруза)
        "retries": 5,
        "fragment_retries": 5,
        "socket_timeout": 30,
        "extractor_retries": 3,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)
