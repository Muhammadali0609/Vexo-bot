import aiohttp
import requests
import re
import json


# =========================
# 📸 INSTAGRAM PHOTO / CAROUSEL
# =========================
async def download_instagram_photo(url: str):
    try:
        # превращаем в JSON endpoint
        if "instagram.com" not in url:
            return None

        if "/reel/" in url or "/video/" in url:
            return None  # не фото

        clean_url = url.split("?")[0]
        json_url = clean_url + "?__a=1&__d=dis"

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(json_url) as r:
                data = await r.json(content_type=None)

        # 🧠 IMAGE extraction
        media = data.get("items", [{}])[0]

        if "image_versions2" in media:
            url_img = media["image_versions2"]["candidates"][0]["url"]
            return url_img

        # carousel
        if "carousel_media" in media:
            images = []
            for item in media["carousel_media"]:
                img = item["image_versions2"]["candidates"][0]["url"]
                images.append(img)
            return images

        return None

    except Exception as e:
        print("INSTAGRAM PHOTO ERROR:", e)
        return None


# =========================
# 🎵 TIKTOK PHOTO (oEmbed fallback)
# =========================
async def download_tiktok_photo(url: str):
    print("TIKTOK PHOTO URL:", url)
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"
            )
        }
        response = requests.get(url, headers=headers)
        html = response.text
        match = re.search(
            r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>',
            html
        )
        if not match:
            print("TIKTOK PHOTO FAILED")
            return None
        data = json.loads(match.group(1))
        photo_list = (
            data["__DEFAULT_SCOPE__"]
            ["webapp.video-detail"]
            ["itemInfo"]
            ["itemStruct"]
            ["imagePost"]
            ["images"]
        )
        images = []
        for item in photo_list:
            images.append(
                item["imageURL"]["urlList"][0]
            )
        return images

    except Exception as e:
        print("TIKTOK PHOTO ERROR:", e)
        return None