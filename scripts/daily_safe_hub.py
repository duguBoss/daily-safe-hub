#!/usr/bin/env python3
import json
import mimetypes
import os
import re
import shutil
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
ASSETS_DIR = ROOT / "assets" / "today"
POST_JSON = OUTPUT_DIR / "post.json"
SEEN_FILE = DATA_DIR / "seen_urls.json"

RSS_URL = "https://feeds.feedburner.com/TheHackersNews"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "5"))
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)


@dataclass
class NewsItem:
    title: str
    link: str
    description_html: str
    pub_date: str
    enclosure_url: str | None


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


def load_seen_urls() -> set[str]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SEEN_FILE.exists():
        return set()
    try:
        data = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {str(x).strip() for x in data if str(x).strip()}
    except Exception as exc:
        log(f"warn: failed to parse seen urls file: {exc}")
    return set()


def save_seen_urls(urls: set[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(
        json.dumps(sorted(urls), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def clean_generated_outputs() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    if ASSETS_DIR.exists():
        shutil.rmtree(ASSETS_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def request_text(
    session: requests.Session, method: str, url: str, **kwargs: Any
) -> str:
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


def get_item_details(session: requests.Session, item: NewsItem) -> dict[str, Any]:
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

    return {
        "title": title,
        "source_url": source_url,
        "pub_date": item.pub_date,
        "content_text": content_text,
        "image_urls": image_urls,
    }


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


def download_images(
    session: requests.Session, image_urls: list[str], limit: int = 16
) -> list[str]:
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
            saved.append(to_github_raw_url(file.relative_to(ROOT)))
        except Exception as exc:
            log(f"warn: image download failed: {url} ({exc})")
    return saved


def call_gemini(
    session: requests.Session,
    api_key: str,
    source_title: str,
    pub_date: str,
    content_text: str,
    github_image_urls: list[str],
) -> dict[str, Any]:
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={api_key}"
    )
    prompt = f"""
You are a cybersecurity intelligence editor.
Transform this security news article into a high-quality WeChat post in Simplified Chinese.

Output JSON only, with exactly:
- title
- summary
- wxhtml

Rules:
1) title: 20-30 Chinese characters, high CTR but factual, no clickbait lies.
2) summary: 120-200 Chinese characters.
3) wxhtml: WeChat-friendly HTML body fragment only, no markdown, no script.
4) Keep content detailed and practical, target around 1200+ Chinese characters.
5) Include sections like: threat snapshot, technical details, impact analysis, defense checklist, SOC actions.
6) Use as many provided GitHub image URLs as possible with <img>.
7) Do NOT display any source URL, reference link, or "来源" section in the final content.
8) End the article with a concise "总结" section instead of source links.
9) No extra fields and no explanation outside JSON.

News title: {source_title}
Published: {pub_date}
Image URLs: {json.dumps(github_image_urls, ensure_ascii=False)}
Article extracted text: {content_text[:18000]}
""".strip()

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "responseMimeType": "application/json"},
    }

    data: dict[str, Any] | None = None
    for attempt in range(1, GEMINI_MAX_RETRIES + 1):
        resp = session.post(
            endpoint,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=120,
        )
        if resp.status_code < 400:
            data = resp.json()
            break
        should_retry = resp.status_code == 429 or 500 <= resp.status_code <= 599
        if not should_retry or attempt == GEMINI_MAX_RETRIES:
            resp.raise_for_status()
        retry_after = resp.headers.get("Retry-After", "").strip()
        delay = min(60, int(retry_after)) if retry_after.isdigit() else min(60, 2 ** attempt)
        log(
            f"warn: Gemini status={resp.status_code}, retry in {delay}s "
            f"(attempt {attempt}/{GEMINI_MAX_RETRIES})"
        )
        time.sleep(delay)

    if data is None:
        raise RuntimeError("Gemini request failed after retries.")

    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise RuntimeError("Gemini returned empty content.")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise RuntimeError("Gemini response is not valid JSON.")
        return json.loads(match.group(0))


def ensure_wxhtml(
    wxhtml: str,
    source_title: str,
    github_images: list[str],
    summary: str,
    text_tags: list[str],
) -> str:
    body = (wxhtml or "").strip()
    if not body:
        body = (
            f"<section><h2>{escape(source_title)}</h2>"
            "<p>这是一篇面向实战场景的安全情报速读，帮助你快速掌握威胁动态与防守动作。</p>"
            "</section>"
        )

    # Remove links and possible source/reference blocks for cleaner presentation.
    body = re.sub(r"<a[^>]*>(.*?)</a>", r"\1", body, flags=re.I | re.S)
    body = re.sub(r"(原文地址|来源|source|reference)[:：]?\s*https?://\S+", "", body, flags=re.I)
    body = re.sub(r"https?://\S+", "", body)
    body = re.sub(r"(原文地址|文章来源|来源)[:：]?", "", body, flags=re.I)
    body = re.sub(r"<script[\s\S]*?</script>", "", body, flags=re.I)

    text_len = len(BeautifulSoup(body, "html.parser").get_text(" ", strip=True))
    if text_len < 900:
        body += (
            "<section style='margin-top:14px;'>"
            "<h3 style='margin:0 0 8px;font-size:20px;color:#0f172a;'>防守方执行清单</h3>"
            "<p>建议从三个层面立即落地：第一，资产层面先确认受影响系统版本、暴露面和外网入口，"
            "把高风险节点拉出清单；第二，检测层面增加针对该攻击链的日志规则与告警聚合，"
            "优先关注异常登录、提权与横向移动行为；第三，响应层面同步修复优先级，明确24小时内可完成项。"
            "</p>"
            "<p>若你在企业内负责安全运营，可以把本文拆成“高层汇报版 + 执行任务版”两份："
            "汇报版强调业务影响与处置进展，任务版明确人、系统、时间和验收标准。这样既能提升团队协作效率，"
            "也能减少事件处理过程中的信息断层和重复沟通成本。</p>"
            "</section>"
        )

    missing_images = [u for u in github_images if u not in body]
    for u in missing_images:
        body += (
            "<figure style='margin:16px 0;padding:8px;border:1px solid #fca5a5;border-radius:10px;'>"
            f"<img src='{escape(u)}' style='width:100%;height:auto;border-radius:6px;'/>"
            "</figure>"
        )

    body += (
        "<section style='margin-top:18px;padding:14px;background:#fff7ed;border:1px solid #fdba74;border-radius:10px;'>"
        "<h3 style='margin:0 0 8px;font-size:18px;color:#7c2d12;'>总结</h3>"
        f"<p style='margin:0;color:#7c2d12;'>{escape(summary)}</p>"
        "</section>"
    )
    if text_tags:
        tags_text = " ".join(text_tags)
        body += (
            "<section style='margin-top:10px;padding:12px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;'>"
            "<p style='margin:0;font-size:14px;color:#334155;'>"
            f"标签：{escape(tags_text)}"
            "</p>"
            "</section>"
        )

    return (
        "<section style='font-size:16px;line-height:1.78;color:#111827;'>"
        "<section style='padding:14px;border-radius:12px;background:#0b1220;color:#e5e7eb;"
        "border:1px solid #1f2937;margin-bottom:14px;'>"
        "<p style='margin:0 0 6px;font-size:13px;color:#fca5a5;'>DAILY SAFE BRIEF</p>"
        f"<h2 style='margin:0 0 8px;font-size:22px;line-height:1.4;'>{escape(source_title)}</h2>"
        "</section>"
        "<section style='padding:14px;border-radius:12px;background:#ffffff;border:1px solid #e5e7eb;'>"
        f"{body}"
        "</section>"
        "</section>"
    )


def build_text_tags(title: str) -> list[str]:
    tags = ["#网络安全", "#威胁情报", "#漏洞预警", "#安全运营"]
    lower_title = title.lower()
    mapping = [
        ("ransom", "#勒索软件"),
        ("phish", "#钓鱼攻击"),
        ("ddos", "#DDoS"),
        ("botnet", "#僵尸网络"),
        ("zero-day", "#零日漏洞"),
        ("linux", "#Linux安全"),
        ("windows", "#Windows安全"),
        ("cloud", "#云安全"),
        ("iot", "#IoT安全"),
    ]
    for kw, tag in mapping:
        if kw in lower_title and tag not in tags:
            tags.append(tag)
    return tags[:8]


def main() -> int:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY environment variable.")

    clean_generated_outputs()
    seen_urls = load_seen_urls()
    log(f"loaded seen urls: {len(seen_urls)}")

    session = requests.Session()
    items = fetch_candidates(session)
    log(f"rss items fetched: {len(items)}")

    selected = choose_item(items, seen_urls)
    log(f"selected: {selected.title} | {selected.link}")

    detail = get_item_details(session, selected)
    log(f"source images found: {len(detail['image_urls'])}")

    github_images = download_images(session, detail["image_urls"], limit=16)
    if not github_images:
        raise RuntimeError("No image downloaded from selected article.")
    log(f"images downloaded: {len(github_images)}")

    gemini_result = call_gemini(
        session=session,
        api_key=api_key,
        source_title=detail["title"],
        pub_date=detail["pub_date"],
        content_text=detail["content_text"],
        github_image_urls=github_images,
    )

    title = str(gemini_result.get("title", "")).strip() or f"{detail['title']} | 安全速报"
    summary = str(gemini_result.get("summary", "")).strip() or (
        "今日安全快报：提炼威胁动态、影响评估与防守清单，便于安全团队快速执行。"
    )
    wxhtml_raw = str(gemini_result.get("wxhtml", "")).strip()
    text_tags = build_text_tags(title)
    wxhtml = ensure_wxhtml(
        wxhtml=wxhtml_raw,
        source_title=title,
        github_images=github_images,
        summary=summary,
        text_tags=text_tags,
    )

    covers = list(dict.fromkeys(github_images))
    post_data = {"title": title, "covers": covers, "wxhtml": wxhtml, "summary": summary}
    POST_JSON.write_text(json.dumps(post_data, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"written: {POST_JSON}")

    seen_urls.add(detail["source_url"])
    save_seen_urls(seen_urls)
    log(f"seen urls updated: {len(seen_urls)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log(f"error: {exc}")
        raise
