from __future__ import annotations

import json
import re
import time
from typing import Any

import requests

from .config import GEMINI_MAX_RETRIES, GEMINI_MODEL


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
        print(
            f"[daily-safe-hub] warn: Gemini status={resp.status_code}, retry in {delay}s "
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