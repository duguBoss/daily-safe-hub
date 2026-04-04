from __future__ import annotations

import json
import re
import time
from typing import Any

import requests

from .config import GEMINI_MAX_RETRIES, GEMINI_MODEL


def _build_article_blocks(source_title: str, pub_date: str, content_text: str, image_urls: list[str]) -> str:
    blocks = [
        f"## Source Article",
        f"Title: {source_title}",
        f"Published: {pub_date}",
        f"Images: {json.dumps(image_urls, ensure_ascii=False)}",
        f"Content:",
        content_text[:15000],
    ]
    return "\n\n".join(blocks)


FORBIDDEN_TITLE_TERMS = (
    "速报",
    "要闻",
    "汇总",
    "盘点",
    "合集",
    "简报",
    "日更",
)


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

    article_blocks = _build_article_blocks(source_title, pub_date, content_text, github_image_urls)

    prompt = f"""
你是一位顶级的网络安全情报分析专家和资深科技媒体主编。你需要将提供的英文安全资讯，提炼并转化为专业、可读性极强、排版高级且留白合理的中文安全情报文章。

内容素材:
{article_blocks}

输出格式要求:
1) 输出纯JSON，包含且仅包含: title, summary, wxhtml
2) 所有正文必须使用严谨、专业的简体中文。

标题要求 (title):
- 长度: 18-28个中文字符
- 必须包含具体的威胁组织、漏洞名称或关键影响
- 风格: 极具信息密度和专业权威感，但实事求是。绝不使用"速报/要闻/汇总"等词汇。

摘要要求 (summary):
- 长度: 80-150个中文字符
- 内容: 用一两句话讲透核心安全事件。

正文要求 (wxhtml):
- 长度: 1500-2500个中文字符
- 定位: 面向CISO、安全架构师、一线专家的深度分析。
- 结构与行文：不要生硬堆砌模块。文章要有自然的呼吸感，按照“背景概览 -> 攻击解码 -> 风险定级 -> 防御建议 -> 运营洞察”的逻辑顺畅行文，以讲故事和深度分析的口吻推进。

正文极其严格的高级HTML排版规范 (请完全按照以下格式进行输出，专门适配微信公众号全宽无边距的高级阅读体验):
- 模块标题：使用简洁富有质感的标题（不要改变style，不要增加额外的div包裹）：
  <h2 style="font-size: 18px; font-weight: 600; color: #0f172a; margin: 28px 0 12px 0; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px;">
    模块名称
  </h2>
- 段落文本：用 `<p style="margin: 0 0 16px; font-size: 16px; color: #334155; line-height: 1.7;">`。列表项也使用该样式。
- 重点强调：核心攻击手法、CVE编号、IOC等，用 `<strong style="color: #0369a1; font-weight: 600;">关键字</strong>` 加以高亮。
- 代码片段：`<code style="display:inline-block;background-color:#f1f5f9;color:#e11d48;padding:2px 6px;border-radius:4px;font-family:monospace;font-size:14px;word-break:break-all;">内容</code>`
- 引用强调：
  <section style="margin:20px 0;padding:16px;background-color:#f8fafc;border-left:3px solid #0369a1;">
    <p style="margin:0;font-size:15px;color:#475569;line-height:1.7;">引用或专家点评内容</p>
  </section>
- 图片使用：必须且只使用素材中提供的图片，根据内容在合适的位置插入。
  <img src="素材图片URL" style="width:100%;height:auto;margin-bottom:16px;display:block;" />
- 禁止：任何 `<a>` 标签、引用的外部链接。

JSON输出格式:
{{
  "title": "...",
  "summary": "...",
  "wxhtml": "<h2>...</h2><p>...</p><img><p>...</p>"
}}
"""

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.65, "responseMimeType": "application/json"},
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