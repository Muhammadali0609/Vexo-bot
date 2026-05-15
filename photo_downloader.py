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
        return result if result else None

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

