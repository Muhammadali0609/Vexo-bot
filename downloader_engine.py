import asyncio
import os
import uuid
import yt_dlp
import subprocess
import json

# =========================
# 🔥 HOOK (лог скачивания)
# =========================
def progress_hook(d):
    if d['status'] == 'finished':
        print("DONE:", d['filename'])

def get_ydl_opts(platform, file_name):
    
    base = {
        "outtmpl": file_name,

        "merge_output_format": "mp4",

        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,

        "retries": 3,

        "progress_hooks": [progress_hook],
    }

    # =========================
    # 🎵 YOUTUBE
    # =========================
    if platform == "youtube":
        base.update({
            "format": "bv*[height<=720]+ba/b",
            "retries": 10,
            "fragment_retries": 10,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android"]
                }
            },
            "cookiefile": "cookies/youtube.txt"
        })

    # =========================
    # 🎵 TIKTOK
    # =========================
    elif platform == "tiktok":
        base.update({
            "format": "best",
            "postprocessor_args": [
                "-movflags", "+faststart",
            ],
            "recodevideo": "mp4",
        })

    # =========================
    # 🎵 INSTAGRAM
    # =========================
    elif platform == "instagram":
        base.update({
            "format": "best",
            "recodevideo": "mp4",
        })

    # =========================
    # 🔥 DEFAULT
    # =========================
    else:
        base.update({
            "format": "best"
        })

    return base

# =========================
# 🧠 PRIMARY DOWNLOAD
# =========================
async def try_yt_dlp(url: str, platform: str):
    os.makedirs("downloads", exist_ok=True)

    file_name = f"downloads/{uuid.uuid4()}.mp4"

    ydl_opts = get_ydl_opts(platform, file_name)

    def run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return file_name

    return await asyncio.to_thread(run)

# =========================
# 🔁 ALT DOWNLOAD (backup)
# =========================
async def try_yt_dlp_alt(url: str, platform: str):
    os.makedirs("downloads", exist_ok=True)

    file_name = f"downloads/{uuid.uuid4()}_alt.mp4"

    ydl_opts = get_ydl_opts(platform, file_name)

    def run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return file_name

    return await asyncio.to_thread(run)

def get_video_metadata(file_path):
    try:
        result = subprocess.check_output([
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            file_path
        ])

        data = json.loads(result)

        video_stream = next(
            s for s in data["streams"]
            if s["codec_type"] == "video"
        )
        width = video_stream.get("width")
        height = video_stream.get("height")

        return width, height

    except Exception as e:
        print("FFPROBE ERROR:", e)
        return None, None

# =========================
# 🚀 MAIN ENGINE (SIMPLE + CLEAN)
# =========================
async def download_manager(url: str, platform: str):
    last_error = None

    for attempt in range(3):
        try:
            print(f"TRY PRIMARY {attempt + 1}/3")
            file_path = await try_yt_dlp(url, platform)

            if file_path and os.path.exists(file_path):
                return file_path

        except Exception as e:
            print("PRIMARY FAIL:", e)
            last_error = e

        await asyncio.sleep(1.5)

    # 🔁 fallback
    try:
        print("TRY ALT ENGINE")
        file_path = await try_yt_dlp(url, platform)

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
