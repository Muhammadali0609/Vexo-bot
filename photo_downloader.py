import json
import os
import re
import uuid
import socket
import asyncio
import base64
import tempfile
from instaloader import Instaloader, Post, Profile

from html import unescape
from urllib.parse import urlparse
from aiohttp.resolver import ThreadedResolver

import aiohttp
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

DOWNLOAD_HEADERS = {
    "User-Agent": HEADERS["User-Agent"],
    "Accept": "*/*",
    "Referer": "https://www.instagram.com/",
}

PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
VIDEO_EXTENSIONS = (".mp4", ".mov")
MAX_FILE_SIZE = 49 * 1024 * 1024


def make_connector():
    return aiohttp.TCPConnector(
        resolver=ThreadedResolver(),
        family=socket.AF_INET,
        ttl_dns_cache=300
    )

def is_reel_url(url):
    return "/reel/" in url or "/reels/" in url or "/tv/" in url
def is_story_url(url):
    return "/stories/" in url
def is_post_url(url):
    return "/p/" in url

def clean_url(value):
    if not value:
        return None

    value = unescape(str(value))
    value = value.replace("\\/", "/").replace("\\u0026", "&")
    value = value.strip().strip("\"'")

    if value.startswith("//"):
        value = "https:" + value

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

    items.append({"type": media_type, "url": url})


def collect_media_from_text(text):
    items = []
    if not text:
        return items

    text = unescape(str(text))
    text = text.replace("\\/", "/").replace("\\u0026", "&")

    for url in re.findall(r"https?://[^\s\"'<>]+", text):
        url = url.split("\\")[0].rstrip(".,);]")
        add_media(items, url)

    return items


def collect_media_from_html(html):
    items = []
    if not html:
        return items

    soup = BeautifulSoup(html, "html.parser")

    for prop in ("og:video", "og:video:secure_url", "twitter:player:stream"):
        tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
        if tag:
            add_media(items, tag.get("content"), "video")

    for tag in soup.find_all(["video", "source"]):
        add_media(items, tag.get("src"), "video")

    if items:
        return items

    for tag in soup.find_all("a"):
        href = tag.get("href") or tag.get("data-href")
        text = tag.get_text(" ", strip=True).lower()
        classes = " ".join(tag.get("class", [])).lower()

        if "download" in text or "download" in classes:
            add_media(items, href)

    if items:
        return items

    for prop in ("og:image", "og:image:secure_url", "twitter:image"):
        tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
        if tag:
            add_media(items, tag.get("content"), "photo")

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


def filter_items_for_source(source_url, items):
    if is_reel_url(source_url):
        videos = [item for item in items if item["type"] == "video"]
        return videos

    return items


def extension_for(url, media_type):
    path = urlparse(str(url)).path.lower()
    ext = os.path.splitext(path)[1]

    if media_type == "video" and ext in VIDEO_EXTENSIONS:
        return ext

    if media_type == "photo" and ext in PHOTO_EXTENSIONS:
        return ext

    return ".mp4" if media_type == "video" else ".jpg"


async def download_media_file(session, item):
    url = item["url"]
    media_type = item["type"]

    try:
        async with session.get(
            url,
            headers=DOWNLOAD_HEADERS,
            timeout=aiohttp.ClientTimeout(total=60),
            allow_redirects=True
        ) as response:
            if response.status != 200:
                print("MEDIA DOWNLOAD STATUS:", response.status, url)
                return None

            content_type = response.headers.get("Content-Type", "").lower()

            if "text/html" in content_type:
                print("MEDIA DOWNLOAD HTML INSTEAD OF MEDIA:", url)
                return None

            if "video" in content_type:
                media_type = "video"
            elif "image" in content_type:
                media_type = "photo"

            os.makedirs("downloads", exist_ok=True)
            file_path = f"downloads/{uuid.uuid4()}{extension_for(response.url, media_type)}"

            total = 0
            with open(file_path, "wb") as file:
                async for chunk in response.content.iter_chunked(64 * 1024):
                    if not chunk:
                        continue

                    total += len(chunk)

                    if total > MAX_FILE_SIZE:
                        file.close()
                        os.remove(file_path)
                        print("MEDIA TOO LARGE:", url)
                        return None

                    file.write(chunk)

            if total < 1024:
                os.remove(file_path)
                print("MEDIA TOO SMALL:", url)
                return None

            return {"type": media_type, "url": file_path}

    except Exception as e:
        print("MEDIA DOWNLOAD ERROR:", e)
        return None


async def materialize_items(session, items):
    local_items = []

    for item in items[:10]:
        local_item = await download_media_file(session, item)
        if local_item:
            local_items.append(local_item)

    return local_items


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
            return {"type": "video", "data": item["url"], "local": True}

        return {"type": "photos", "data": [item["url"]], "local": True}

    if all(item["type"] == "photo" for item in clean_items):
        return {
            "type": "photos",
            "data": [item["url"] for item in clean_items],
            "local": True,
        }

    return {
        "type": "media_group",
        "data": clean_items,
        "local": True,
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

async def try_igdownloader(session, url):
    endpoints = [
        ("https://v3.igdownloader.app/api/ajaxSearch", "https://igdownloader.app/en"),
    ]

    for endpoint, referer in endpoints:
        try:
            status, payload = await post_form(
                session,
                endpoint,
                {
                    "recaptchaToken": "",
                    "q": url,
                    "t": "media",
                    "lang": "en"
                },
                referer
            )

            print("IGDOWNLOADER STATUS:", status)

            if status == 200:
                items = parse_service_payload(payload)
                if items:
                    print("IGDOWNLOADER ITEMS:", items)
                    return items

        except Exception as e:
            print("IGDOWNLOADER ERROR:", e)

    return []


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
                {
                    "recaptchaToken": "",
                    "q": url,
                    "t": "media",
                    "lang": "en"
                },
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
                {
                    "url": url,
                    "action": "post",
                    "lang": "en"
                },
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
    if is_story_url(url) or is_post_url(url):
        print("INSTAGRAM PAGE SKIPPED: public page gives only preview image")
        return []

    try:
        async with session.get(
            url,
            headers=HEADERS,
            timeout=aiohttp.ClientTimeout(total=20),
            allow_redirects=True
        ) as response:
            html = await response.text()

        items = collect_media_from_html(html)
        items = [item for item in items if item["type"] == "video"]

        if items:
            print("INSTAGRAM PAGE VIDEO ITEMS:", items)
            return items

    except Exception as e:
        print("INSTAGRAM PAGE ERROR:", e)

    return []
    
INSTAGRAM_LOADER = None

def extract_instagram_shortcode(url):
    match = re.search(r"instagram\.com/(?:p|reel|reels|tv)/([^/?#]+)", url)
    return match.group(1) if match else None


def extract_story_parts(url):
    match = re.search(r"instagram\.com/stories/([^/?#]+)/([^/?#]+)", url)
    if not match:
        return None, None

    return match.group(1), match.group(2)


def get_instagram_loader():
    global INSTAGRAM_LOADER

    if INSTAGRAM_LOADER:
        return INSTAGRAM_LOADER

    loader = Instaloader(quiet=True)
    username = os.getenv("IG_USERNAME")
    session_b64 = os.getenv("IG_SESSION_B64")

    if username and session_b64:
        session_path = os.path.join(tempfile.gettempdir(), "instagram.session")
        with open(session_path, "wb") as file:
            file.write(base64.b64decode(session_b64))

        loader.load_session_from_file(username, session_path)
        print("INSTALOADER SESSION LOADED")

    INSTAGRAM_LOADER = loader
    return loader


def instaloader_post_items(url):
    shortcode = extract_instagram_shortcode(url)
    if not shortcode:
        return []

    loader = get_instagram_loader()
    post = Post.from_shortcode(loader.context, shortcode)

    items = []

    if post.typename == "GraphSidecar":
        for node in post.get_sidecar_nodes():
            if node.is_video:
                items.append({"type": "video", "url": node.video_url})
            else:
                items.append({"type": "photo", "url": node.display_url})

        return items

    if post.is_video:
        return [{"type": "video", "url": post.video_url}]

    return [{"type": "photo", "url": post.url}]


def instaloader_story_items(url):
    username, story_id = extract_story_parts(url)
    if not username:
        return []

    loader = get_instagram_loader()
    profile = Profile.from_username(loader.context, username)

    items = []
    start_collecting = False

    for story in loader.get_stories(userids=[profile.userid]):
        for item in story.get_items():
            if story_id and str(item.mediaid) == str(story_id):
                start_collecting = True

            if not story_id or start_collecting:
                if item.is_video:
                    items.append({"type": "video", "url": item.video_url})
                else:
                    items.append({"type": "photo", "url": item.url})

            if len(items) >= 10:
                return items

    return items

async def try_instaloader(url):
    try:
        if is_story_url(url):
            return await asyncio.to_thread(instaloader_story_items, url)

        return await asyncio.to_thread(instaloader_post_items, url)

    except Exception as e:
        print("INSTALOADER ERROR:", e)
        return []


async def download_instagram_photo(url: str):
    items = await try_instaloader(url)
    items = filter_items_for_source(url, items)

    if not items:
        print("INSTAGRAM RESULT: None")
        return None

    connector = make_connector()

    async with aiohttp.ClientSession(connector=connector) as session:
        local_items = await materialize_items(session, items)
        result = build_result(local_items)

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
