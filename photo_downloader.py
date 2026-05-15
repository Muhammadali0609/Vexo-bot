import aiohttp
import requests
import re
import json
from bs4 import BeautifulSoup

# =========================
# 📸 INSTAGRAM PHOTO / CAROUSEL
# =========================
async def download_instagram_photo(url: str):
    url = re.sub(
        r"(www\.)?instagram\.com",
        "ddinstagram.com",
        url
    )
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                allow_redirects=True
            ) as response:
                html = await response.text()
        matches = re.findall(
            r'https:\\/\\/[^"]+',
            html
        )
        result = []

        for item in matches:
            item = item.replace("\\u0026", "&")
            item = item.replace("\\/", "/")
            if any(ext in item for ext in [
                ".jpg",
                ".jpeg",
                ".png",
                ".webp"
            ]):
                result.append(item)
        result = list(set(result))
        print("INSTAGRAM IMAGES:", result)
        if result:
            return {
                "type": "photos",
                "data": result
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
