from __future__ import annotations

import os

from daily_safe.fetching import (
    choose_item,
    clean_generated_outputs,
    download_images,
    fetch_candidates,
    get_item_details,
    log,
)
from daily_safe.persistence import load_seen_urls, save_post_data, save_seen_urls
from daily_safe.ai_writer import call_gemini
from daily_safe.rendering import build_text_tags, ensure_wxhtml


def main() -> int:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY environment variable.")

    clean_generated_outputs()
    seen_urls = load_seen_urls()
    log(f"loaded seen urls: {len(seen_urls)}")

    import requests
    session = requests.Session()
    items = fetch_candidates(session)
    log(f"rss items fetched: {len(items)}")

    selected = choose_item(items, seen_urls)
    log(f"selected: {selected.title} | {selected.link}")

    detail = get_item_details(session, selected)
    log(f"source images found: {len(detail.image_urls)}")

    github_images = download_images(session, detail.image_urls, limit=16)
    if not github_images:
        raise RuntimeError("No image downloaded from selected article.")
    log(f"images downloaded: {len(github_images)}")

    gemini_result = call_gemini(
        session=session,
        api_key=api_key,
        source_title=detail.title,
        pub_date=detail.pub_date,
        content_text=detail.content_text,
        github_image_urls=github_images,
    )

    title = str(gemini_result.get("title", "")).strip() or f"{detail.title} | 安全速报"
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
    save_post_data(title=title, covers=covers, wxhtml=wxhtml, summary=summary)
    log(f"written: output/post.json")

    seen_urls.add(detail.source_url)
    save_seen_urls(seen_urls)
    log(f"seen urls updated: {len(seen_urls)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log(f"error: {exc}")
        raise