import os
import re
import uuid
import socket
import asyncio
import base64
import tempfile
from instaloader import Instaloader, Post, Profile

from urllib.parse import urlparse
from aiohttp.resolver import ThreadedResolver

import aiohttp

DOWNLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
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

    for item in items:
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

    #clean_items = clean_items[:10]

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

    for story in loader.get_stories(userids=[profile.userid]):
        for item in story.get_items():
            if item.is_video:
                items.append({"type": "video", "url": item.video_url})
            else:
                items.append({"type": "photo", "url": item.url})

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
