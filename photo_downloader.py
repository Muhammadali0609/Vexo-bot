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
        print("TIKTOK PHOTO URL:", url)
        headers = {
            "User-Agent": (
                "Mozilla/5.0"
            )
        }
        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )
        html = response.text
        
        # 🔥 ищем JSON с SIGI_STATE
        start = html.find(
            '<script id="SIGI_STATE" type="application/json">'
        )
        if start == -1:
            print("SIGI_STATE NOT FOUND")
            return None

        start = html.find(">", start) + 1
        end = html.find("</script>", start)
        json_text = html[start:end]
        data = json.loads(json_text)

        # 🔥 ищем любой post item
        item_module = data.get("ItemModule", {})
        if not item_module:
            print("ITEM MODULE EMPTY")
            return None

        first_key = next(iter(item_module))
        post = item_module[first_key]
        images = []
        image_post = post.get("imagePost", {})
        for img in image_post.get("images", []):
            image_url = (
                img.get("imageURL", {})
                .get("urlList", [])
            )

            if image_url:
                images.append(image_url[0])

        print("TIKTOK IMAGES:", images)
        return images if images else None

    except Exception as e:
        print("TIKTOK PHOTO ERROR:", e)
        return None