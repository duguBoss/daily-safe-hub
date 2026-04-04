from __future__ import annotations

import json
import shutil
from pathlib import Path

from .config import ASSETS_DIR, DATA_DIR, OUTPUT_DIR, POST_JSON, SEEN_FILE


def clean_generated_outputs() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    if ASSETS_DIR.exists():
        shutil.rmtree(ASSETS_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def load_seen_urls() -> set[str]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SEEN_FILE.exists():
        return set()
    try:
        data = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {str(x).strip() for x in data if str(x).strip()}
    except Exception as exc:
        print(f"[daily-safe-hub] warn: failed to parse seen urls file: {exc}")
    return set()


def save_seen_urls(urls: set[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(
        json.dumps(sorted(urls), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def save_post_data(title: str, covers: list[str], wxhtml: str, summary: str) -> None:
    post_data = {
        "title": title,
        "covers": covers,
        "wxhtml": wxhtml,
        "summary": summary,
    }
    POST_JSON.write_text(json.dumps(post_data, ensure_ascii=False, indent=2), encoding="utf-8")