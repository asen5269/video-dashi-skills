from __future__ import annotations

import html
import json
import os
import re
from typing import Any
from urllib.parse import urlparse

import requests


MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"
)


def clean_text(value: Any) -> str:
    return html.unescape(str(value or "")).replace("\xa0", " ").strip()


def extract_url(text: str) -> str:
    match = re.search(r"https?://[^\s，,。）)]+", text)
    return match.group(0).strip() if match else text.strip()


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))


def new_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": MOBILE_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://www.douyin.com/",
        }
    )
    if os.getenv("HTTP_PROXY"):
        session.proxies["http"] = os.environ["HTTP_PROXY"]
    if os.getenv("HTTPS_PROXY"):
        session.proxies["https"] = os.environ["HTTPS_PROXY"]
    return session


def og_value(source: str, prop: str) -> str:
    patterns = [
        rf'<meta[^>]+property=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(prop)}["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, source, re.I)
        if match:
            return clean_text(match.group(1))
    return ""


def og_images(source: str) -> list[str]:
    return unique(
        re.findall(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            source,
            re.I,
        )
    )


def extract_aweme_id(session: requests.Session, url: str) -> str:
    patterns = [r"/video/(\d+)", r"/note/(\d+)", r"modal_id=(\d+)", r"/(\d{15,})"]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    response = session.get(url, timeout=20, allow_redirects=True)
    response.raise_for_status()
    for candidate in (str(response.url), response.headers.get("Location", "")):
        for pattern in patterns:
            match = re.search(pattern, candidate)
            if match:
                return match.group(1)
    raise ValueError(f"Cannot extract Douyin aweme id: {url}")


def router_detail(source: str) -> dict[str, Any] | None:
    match = re.search(r"window\._ROUTER_DATA\s*=\s*(.*?);?\s*</script>", source, re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    for value in (data.get("loaderData") or {}).values():
        if not isinstance(value, dict):
            continue
        info = value.get("videoInfoRes")
        items = (info or {}).get("item_list") if isinstance(info, dict) else []
        if items and isinstance(items[0], dict):
            return items[0]
    return None


def resolve_redirect(session: requests.Session, url: str) -> str:
    try:
        response = session.get(url, timeout=15, allow_redirects=False)
        location = response.headers.get("Location") or response.headers.get("location") or ""
        if location.startswith("http"):
            return location
    except requests.RequestException:
        pass
    return url


def extract_detail(detail: dict[str, Any], session: requests.Session) -> dict[str, Any]:
    title = clean_text(detail.get("desc") or detail.get("title") or "")
    content = ""
    if "\n" in title:
        title, content = [part.strip() for part in title.split("\n", 1)]

    images: list[str] = []
    for image in detail.get("images") or []:
        if not isinstance(image, dict):
            continue
        urls = (
            image.get("url_list")
            or (image.get("display_image") or {}).get("url_list")
            or image.get("origin_url_list")
            or (image.get("download_addr") or {}).get("url_list")
            or []
        )
        if urls:
            images.append(str(urls[0]))

    videos: list[str] = []
    video = detail.get("video")
    is_image_post = bool(images) or detail.get("aweme_type") in {2, 68, 150}
    if isinstance(video, dict) and not is_image_post:
        play_urls = ((video.get("play_addr") or {}).get("url_list") or [])
        if play_urls:
            clean = str(play_urls[0]).replace("/playwm/", "/play/").replace("playwm", "play")
            videos.append(resolve_redirect(session, clean))
        if not videos:
            bitrates = [item for item in (video.get("bit_rate") or []) if isinstance(item, dict)]
            bitrates.sort(key=lambda item: int(item.get("bit_rate") or 0), reverse=True)
            for item in bitrates:
                urls = ((item.get("play_addr") or {}).get("url_list") or [])
                if urls:
                    videos.append(resolve_redirect(session, str(urls[0])))
                    break
        if not images:
            covers = ((video.get("origin_cover") or video.get("cover") or {}).get("url_list") or [])
            if covers:
                images.append(str(covers[0]))

    return {"title": title, "content": content, "images": unique(images), "videos": unique(videos)}


def parse_with_ytdlp(url: str, warning: str) -> dict[str, Any]:
    try:
        import certifi
        from yt_dlp import YoutubeDL
    except ImportError as exc:
        raise RuntimeError(f"{warning}; install yt-dlp and certifi for fallback parsing") from exc

    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "format": "best[ext=mp4]/best",
        "http_headers": {"User-Agent": MOBILE_UA},
    }
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    if proxy:
        options["proxy"] = proxy
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict):
        raise RuntimeError(f"{warning}; yt-dlp returned no metadata")

    videos = [str(info["url"])] if info.get("url") else []
    images = [str(info["thumbnail"])] if info.get("thumbnail") else []
    return {
        "platform": "douyin",
        "note_id": str(info.get("id") or "") or None,
        "title": clean_text(info.get("title")),
        "content": clean_text(info.get("description")),
        "url": str(info.get("webpage_url") or url),
        "images": unique(images),
        "videos": unique(videos),
        "warnings": [warning, "Used bundled yt-dlp fallback."],
    }


def parse_douyin(text: str) -> dict[str, Any]:
    url = extract_url(text)
    host = urlparse(url).netloc.lower()
    if "douyin.com" not in host and "iesdouyin.com" not in host:
        raise ValueError("Input is not a Douyin URL or share text")

    session = new_session()
    try:
        aweme_id = extract_aweme_id(session, url)
        source = ""
        detail = None
        for share_url in (
            f"https://www.iesdouyin.com/share/video/{aweme_id}/",
            f"https://www.iesdouyin.com/share/note/{aweme_id}/",
        ):
            response = session.get(share_url, timeout=25, allow_redirects=True)
            response.raise_for_status()
            source = response.text
            detail = router_detail(source)
            if detail:
                break

        if not detail:
            warning = "Douyin page data unavailable; tried Open Graph metadata."
            fallback = {
                "platform": "douyin",
                "note_id": aweme_id,
                "title": og_value(source, "og:title"),
                "content": og_value(source, "og:description"),
                "url": f"https://www.douyin.com/video/{aweme_id}",
                "images": og_images(source),
                "videos": [],
                "warnings": [warning],
            }
            if fallback["images"]:
                return fallback
            return parse_with_ytdlp(url, warning)

        extracted = extract_detail(detail, session)
        return {
            "platform": "douyin",
            "note_id": aweme_id,
            "title": extracted["title"],
            "content": extracted["content"],
            "url": f"https://www.douyin.com/{'note' if extracted['images'] and not extracted['videos'] else 'video'}/{aweme_id}",
            "images": extracted["images"],
            "videos": extracted["videos"],
            "warnings": [],
        }
    except Exception as exc:
        return parse_with_ytdlp(url, f"Built-in Douyin parser failed: {exc}")
