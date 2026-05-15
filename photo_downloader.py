import aiohttp
import requests
import re
import json
from bs4 import BeautifulSoup

# =========================
# 📸 INSTAGRAM PHOTO / CAROUSEL
# =========================
async def download_instagram_photo(url: str):
    fixed_url = re.sub(
        r"(www\.)?instagram\.com",
        "ddinstagram.com",
        url
    )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                fixed_url,
                headers=headers,
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                html = await response.text()

        soup = BeautifulSoup(html, "html.parser")

        videos = []
        photos = []

        for tag in soup.find_all("meta"):
            content = tag.get("content")
            if not content:
                continue

            if ".mp4" in content:
                videos.append(content)

            if any(ext in content for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                photos.append(content)

        matches = re.findall(r'https:\\/\\/[^"]+', html) + re.findall(r'https://[^"\']+', html)

        for item in matches:
            item = item.replace("\\u0026", "&").replace("\\/", "/")

            if ".mp4" in item:
                videos.append(item)

            if any(ext in item for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                photos.append(item)

        videos = list(dict.fromkeys(videos))
        photos = list(dict.fromkeys(photos))

        print("INSTAGRAM VIDEOS:", videos)
        print("INSTAGRAM IMAGES:", photos)

        if videos:
            return {
                "type": "video",
                "data": videos[0]
            }

        if photos:
            return {
                "type": "photos",
                "data": photos[:10]
            }

        return None

    except Exception as e:
        print("INSTAGRAM ERROR:", e)
        return None

# =========================
# 🎵 TIKTOK PHOTO (oEmbed fallback)
# =========================
async def download_tiktok_media(url: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://tikwm.com/api/",
                data={"url": url},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                data = await response.json()
        print("TIKTOK:", data)
        media_data = data.get("data", {})

        # PHOTO POST
        images = media_data.get("images")
        if images:
            return {
                "type": "photos",
                "data": images
            }
            
        # VIDEO
        video_url = media_data.get("play")
        if video_url:
            return {
                "type": "video",
                "data": video_url
            }
        return None

    except Exception as e:
        print("TIKTOK ERROR:", e)
        return None
