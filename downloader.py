import os
import yt_dlp

BASE_DIR = os.path.dirname(__file__)
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

os.makedirs(DOWNLOADS_DIR, exist_ok=True)


COMMON_OPTS = {
    "outtmpl": os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s"),
    "quiet": True,
    "noplaylist": True,
    "retries": 3,
    "fragment_retries": 3,
    "socket_timeout": 20,
}


def download_video(url: str):
    if "tiktok.com" in url:
        return download_tiktok(url)

    if "instagram.com" in url:
        return download_instagram(url)

    if "youtube.com" in url or "youtu.be" in url:
        return download_youtube(url)

    raise Exception("Unsupported platform")


# ======================
# TIKTOK
# ======================
def download_tiktok(url):
    ydl_opts = {
        **COMMON_OPTS,
        "format": "best",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


# ======================
# INSTAGRAM
# ======================
def download_instagram(url):
    ydl_opts = {
        **COMMON_OPTS,
        "format": "mp4/best",
        "http_headers": {
            "User-Agent": "Mozilla/5.0"
        },
        "sleep_interval": 1,
        "extractor_retries": 5,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


# ======================
# YOUTUBE
# ======================
def download_youtube(url):
    ydl_opts = {
        **COMMON_OPTS,
        "format": "best",
        "merge_output_format": "mp4",
        "cookiefile": "cookies.txt",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)
