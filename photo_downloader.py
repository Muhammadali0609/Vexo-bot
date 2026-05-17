import aiohttp
import requests
import re
import json
from bs4 import BeautifulSoup
from html import unescape

# =========================
# 📸 INSTAGRAM PHOTO / CAROUSEL
# =========================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}


PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
VIDEO_EXTENSIONS = (".mp4", ".mov")


def clean_url(value):
    if not value:
        return None

    value = str(value)
    value = unescape(value)
    value = value.replace("\\/", "/").replace("\\u0026", "&")
    value = value.strip().strip("\"'")

    if not value.startswith("http"):
        return None

    return value


def detect_media_type(url):
    lower = url.lower()

    if any(ext in lower for ext in VIDEO_EXTENSIONS):
        return "video"

    if any(ext in lower for ext in PHOTO_EXTENSIONS):
        return "photo"

    if "fbcdn.net" in lower or "cdninstagram.com" in lower:
        if "video" in lower:
            return "video"
        return "photo"

    return None


def add_media(items, url, forced_type=None):
    url = clean_url(url)
    if not url:
        return

    media_type = forced_type or detect_media_type(url)
    if not media_type:
        return

    if any(item["url"] == url for item in items):
        return

    items.append({
        "type": media_type,
        "url": url
    })


def collect_media_from_text(text):
    items = []

    if not text:
        return items

    text = unescape(str(text))
    text = text.replace("\\/", "/").replace("\\u0026", "&")

    urls = re.findall(r"https?://[^\s\"'<>]+", text)

    for url in urls:
        url = url.split("\\")[0]
        url = url.rstrip(".,);]")
        add_media(items, url)

    return items


def collect_media_from_html(html):
    items = []

    if not html:
        return items

    soup = BeautifulSoup(html, "html.parser")

    # Сначала берем ссылки с download-кнопок, чтобы не схватить preview/thumbnail.
    for tag in soup.find_all("a"):
        href = tag.get("href") or tag.get("data-href")
        text = tag.get_text(" ", strip=True).lower()
        classes = " ".join(tag.get("class", [])).lower()

        if "download" in text or "download" in classes:
            add_media(items, href)

    if items:
        return items

    for tag in soup.find_all(["video", "source"]):
        add_media(items, tag.get("src"), "video")

    if items:
        return items

    for tag in soup.find_all("img"):
        src = tag.get("src") or tag.get("data-src")
        add_media(items, src, "photo")

    if items:
        return items

    return collect_media_from_text(html)


def payload_strings(payload):
    result = []

    if isinstance(payload, str):
        result.append(payload)

    elif isinstance(payload, dict):
        for value in payload.values():
            result.extend(payload_strings(value))

    elif isinstance(payload, list):
        for value in payload:
            result.extend(payload_strings(value))

    return result


def parse_service_payload(payload):
    items = []

    for text in payload_strings(payload):
        if "<" in text and ">" in text:
            for item in collect_media_from_html(text):
                add_media(items, item["url"], item["type"])

        for item in collect_media_from_text(text):
            add_media(items, item["url"], item["type"])

    return items


def build_result(items):
    clean_items = []

    for item in items:
        if item["url"] and item["type"] in ("photo", "video"):
            if not any(existing["url"] == item["url"] for existing in clean_items):
                clean_items.append(item)

    clean_items = clean_items[:10]

    if not clean_items:
        return None

    if len(clean_items) == 1:
        item = clean_items[0]
        if item["type"] == "video":
            return {
                "type": "video",
                "data": item["url"]
            }

        return {
            "type": "photos",
            "data": [item["url"]]
        }

    if all(item["type"] == "photo" for item in clean_items):
        return {
            "type": "photos",
            "data": [item["url"] for item in clean_items]
        }

    return {
        "type": "media_group",
        "data": clean_items
    }


async def post_form(session, endpoint, data, referer):
    headers = {
        **HEADERS,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": referer.rstrip("/"),
        "Referer": referer,
    }

    async with session.post(
        endpoint,
        data=data,
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=30),
        allow_redirects=True
    ) as response:
        text = await response.text()

        try:
            payload = json.loads(text)
        except Exception:
            payload = text

        return response.status, payload


async def try_saveig(session, url):
    endpoints = [
        ("https://v3.saveig.app/api/ajaxSearch", "https://saveig.app/"),
        ("https://v3.saveig.app/api/ajaxSearch", "https://saveig.net/"),
    ]

    for endpoint, referer in endpoints:
        try:
            status, payload = await post_form(
                session,
                endpoint,
                {"q": url, "t": "media", "lang": "en"},
                referer
            )

            print("SAVEIG STATUS:", status)

            if status == 200:
                items = parse_service_payload(payload)
                if items:
                    print("SAVEIG ITEMS:", items)
                    return items

        except Exception as e:
            print("SAVEIG ERROR:", e)

    return []


async def try_snapinsta(session, url):
    endpoints = [
        ("https://snapinsta.app/action2.php", "https://snapinsta.app/"),
        ("https://snapinsta.app/action.php", "https://snapinsta.app/"),
    ]

    for endpoint, referer in endpoints:
        try:
            status, payload = await post_form(
                session,
                endpoint,
                {"url": url},
                referer
            )

            print("SNAPINSTA STATUS:", status)

            if status == 200:
                items = parse_service_payload(payload)
                if items:
                    print("SNAPINSTA ITEMS:", items)
                    return items

        except Exception as e:
            print("SNAPINSTA ERROR:", e)

    return []


async def try_public_page(session, url):
    try:
        async with session.get(
            url,
            headers=HEADERS,
            timeout=aiohttp.ClientTimeout(total=20),
            allow_redirects=True
        ) as response:
            html = await response.text()

        items = collect_media_from_html(html)
        if items:
            print("INSTAGRAM PAGE ITEMS:", items)
            return items

    except Exception as e:
        print("INSTAGRAM PAGE ERROR:", e)

    return []


async def download_instagram_photo(url: str):
    async with aiohttp.ClientSession() as session:
        for downloader in (try_saveig, try_snapinsta, try_public_page):
            items = await downloader(session, url)
            result = build_result(items)

            if result:
                print("INSTAGRAM RESULT:", result)
                return result

    print("INSTAGRAM RESULT: None")
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
