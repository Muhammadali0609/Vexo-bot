import aiohttp
import requests
import re
import json


# =========================
# 📸 INSTAGRAM PHOTO / CAROUSEL
# =========================
RAPID_API_KEY = "adca32e6dbmshe66aeffbf1157c9p19139fjsndd0b2a3c5c1b"
async def download_instagram_photo(url: str):
    endpoint = "https://instagram-downloader-api.p.rapidapi.com/download"
    headers = {
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": "instagram-downloader-api.p.rapidapi.com"
    }
    params = {
        "url": url
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(endpoint, headers=headers, params=params) as r:
            data = await r.json()
    if not data or "media" not in data:
        return None
    return data["media"]

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