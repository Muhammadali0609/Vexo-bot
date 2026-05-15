import aiohttp
import requests
import re
import json
from bs4 import BeautifulSoup

# =========================
# 📸 INSTAGRAM PHOTO / CAROUSEL
# =========================
async def download_instagram_photo(url: str):
    url = url.replace(
        "instagram.com",
        "ddinstagram.com"
    )
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers
            ) as response:
                html = await response.text()
        image_urls = re.findall(
            r'https://[^"]+\.jpg',
            html
        )
        if not image_urls:
            return None
            
        return list(set(image_urls))

    except Exception as e:
        print("INSTAGRAM ERROR:", e)
        return None

# =========================
# 🎵 TIKTOK PHOTO (oEmbed fallback)
# =========================
async def download_tiktok_photo(url: str):
    print("TIKTOK PHOTO URL:", url)
    try:
        response = requests.post(
            "https://tikwm.com/api/",
            data={
                "url": url
            },
            timeout=20
        )
        data = response.json()
        images = data.get("data", {}).get("images")
        if not images:
            print("NO IMAGES")
            return None
        return images
    except Exception as e:
        print("TIKTOK PHOTO ERROR:", e)
        return None

