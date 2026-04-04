from __future__ import annotations

import json
import mimetypes
import os
import re
import shutil
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .config import (
    ASSETS_DIR,
    DATA_DIR,
    GEMINI_MAX_RETRIES,
    GEMINI_MODEL,
    OUTPUT_DIR,
    POST_JSON,
    RSS_URL,
    SEEN_FILE,
    USER_AGENT,
)
from .models import ArticleDetail, GeminiResult, NewsItem


def log(msg: str) -> None:
    print(f"[daily-safe-hub] {msg}", flush=True)


def normalize_url(url: Any) -> str | None:
    if not isinstance(url, str):
        return None
    u = url.strip()
    if not u:
        return None
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        return "https://thehackernews.com" + u
    if not (u.startswith("http://") or u.startswith("https://")):
        return None
    return u


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    return " ".join(soup.get_text("\n", strip=True).split())


def request_text(session: requests.Session, method: str, url: str, **kwargs: Any) -> str:
    headers = kwargs.pop("headers", {})
    merged_headers = {"User-Agent": USER_AGENT, **headers}
    resp = session.request(method, url, headers=merged_headers, timeout=30, **kwargs)
    resp.raise_for_status()
    return resp.text


def parse_rss_items(xml_text: str) -> list[NewsItem]:
    root = ET.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
    channel = root.find("channel")
    if channel is None:
        raise RuntimeError("RSS channel not found.")

    def read_text(node: ET.Element, tag: str) -> str:
        found = node.find(tag)
        return (found.text or "").strip() if found is not None else ""

    items: list[NewsItem] = []
    for it in channel.findall("item"):
        title = read_text(it, "title")
        link = read_text(it, "link")
        description_html = read_text(it, "description")
        pub_date = read_text(it, "pubDate")
        enclosure = it.find("enclosure")
        enclosure_url = enclosure.attrib.get("url", "").strip() if enclosure is not None else ""
        n_link = normalize_url(link)
        if not title or not n_link:
            continue
        items.append(
            NewsItem(
                title=title,
                link=n_link,
                description_html=description_html,
                pub_date=pub_date,
                enclosure_url=normalize_url(enclosure_url),
            )
        )
    return items


def fetch_candidates(session: requests.Session) -> list[NewsItem]:
    xml_text = request_text(session, "GET", RSS_URL)
    items = parse_rss_items(xml_text)
    if not items:
        raise RuntimeError("No news item found in RSS feed.")
    return items


def choose_item(items: list[NewsItem], seen_urls: set[str]) -> NewsItem:
    for item in items:
        if item.link not in seen_urls:
            return item
    raise RuntimeError("No unseen news item available in current RSS window.")


def extract_article_image_urls(article_soup: BeautifulSoup) -> list[str]:
    urls: list[str] = []
    article = (
        article_soup.select_one("div.articlebody")
        or article_soup.select_one("div#articlebody")
        or article_soup.select_one("div.post-body")
        or article_soup.select_one("article")
    )

    if article is None:
        article = article_soup

    for img in article.select("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-original")
        u = normalize_url(src)
        if not u:
            continue
        lu = u.lower()
        if lu.startswith("data:"):
            continue
        if any(x in lu for x in ["logo", "avatar", "icon", "sprite", "ads"]):
            continue
        urls.append(u)

    for meta in article_soup.select("meta[property='og:image'],meta[name='twitter:image']"):
        u = normalize_url(meta.get("content"))
        if u:
            urls.append(u)

    return list(dict.fromkeys(urls))


def extract_article_text(article_soup: BeautifulSoup, fallback_description: str) -> str:
    article = (
        article_soup.select_one("div.articlebody")
        or article_soup.select_one("div#articlebody")
        or article_soup.select_one("div.post-body")
        or article_soup.select_one("article")
    )

    text_parts: list[str] = []
    desc_text = html_to_text(fallback_description)
    if desc_text:
        text_parts.append(desc_text)

    if article is not None:
        for p in article.select("p,li,h2,h3"):
            t = " ".join(p.get_text(" ", strip=True).split())
            if t:
                text_parts.append(t)
    else:
        for p in article_soup.select("p"):
            t = " ".join(p.get_text(" ", strip=True).split())
            if t:
                text_parts.append(t)

    return "\n".join(list(dict.fromkeys(text_parts)))[:25000]


def get_item_details(session: requests.Session, item: NewsItem) -> ArticleDetail:
    html = request_text(session, "GET", item.link)
    soup = BeautifulSoup(html, "html.parser")

    title = item.title.strip()
    source_url = item.link
    content_text = extract_article_text(soup, item.description_html)

    image_urls: list[str] = []
    if item.enclosure_url:
        image_urls.append(item.enclosure_url)
    image_urls.extend(extract_article_image_urls(soup))
    image_urls = list(dict.fromkeys(image_urls))

    return ArticleDetail(
        title=title,
        source_url=source_url,
        pub_date=item.pub_date,
        content_text=content_text,
        image_urls=image_urls,
    )


def guess_extension(url: str, content_type: str | None) -> str:
    parsed = urlparse(url)
    ext = Path(parsed.path).suffix.lower()
    if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg"}:
        return ext
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            if guessed == ".jpe":
                return ".jpg"
            return guessed
    return ".jpg"


def to_github_raw_url(rel_path: Path) -> str:
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    branch = os.getenv("GITHUB_REF_NAME", "").strip() or "main"
    path = rel_path.as_posix().lstrip("/")
    if repo:
        return f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
    return path


def download_images(session: requests.Session, image_urls: list[str], limit: int = 16) -> list[str]:
    saved: list[str] = []
    for idx, url in enumerate(image_urls[:limit], start=1):
        try:
            resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=40, stream=True)
            if resp.status_code != 200:
                log(f"warn: skip image status={resp.status_code} url={url}")
                continue
            ext = guess_extension(url, resp.headers.get("content-type"))
            file = ASSETS_DIR / f"cover_{idx:02d}{ext}"
            with file.open("wb") as fw:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        fw.write(chunk)
            saved.append(to_github_raw_url(file.relative_to(Path(__file__).resolve().parents[1])))
        except Exception as exc:
            log(f"warn: image download failed: {url} ({exc})")
    return saved