import aiohttp
import requests
import re
import json


# =========================
# 📸 INSTAGRAM PHOTO / CAROUSEL
# =========================
async def download_instagram_photo(url: str):
    headers = {

        "User-Agent": "Mozilla/5.0"

    }

    async with aiohttp.ClientSession(headers=headers) as session:

        async with session.get(url) as r:

            html = await r.text()

    # ищем изображения

    images = re.findall(r'"display_url":"(https:[^"]+)"', html)

    if not images:

        return None

    # decode \u0026

    images = [img.replace("\\u0026", "&") for img in images]

    # убираем дубли

    images = list(dict.fromkeys(images))

    return images


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