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
你是一位专业的网络安全情报编辑，负责将英文安全资讯转化为高质量的中文微信公众号文章。

内容素材:
{article_blocks}

输出格式要求:
1) 输出纯JSON，包含且仅包含: title, summary, wxhtml
2) 所有正文必须使用简体中文

标题要求 (title):
- 长度: 18-28个中文字符
- 必须包含: 具体的威胁组织名称/CVE编号/漏洞名称/攻击技术名称之一
- 必须包含: 具体的影响范围或数字
- 风格: 像成熟的中文科技自媒体标题，具体、有信息量、引发好奇，但实事求是
- 禁止: 使用"速报/要闻/汇总/盘点/合集"等低信息量词汇
- 禁止: 标题中出现完整URL或"来源"字样

摘要要求 (summary):
- 长度: 100-180个中文字符
- 内容: 简洁概括核心威胁、影响规模、关键行动建议

正文要求 (wxhtml):
- 长度: 1200-2000个中文字符
- 结构必须包含以下模块（按顺序）:
  1. 威胁态势概览: 用1-2段说明这是什么威胁、来自哪个组织、目标是谁
  2. 技术细节分析: 详细说明攻击手法、漏洞利用方式、技术实现细节
  3. 影响范围评估: 具体列出受影响的版本/系统/行业
  4. 防御建议清单: 提供3-5条可落地的具体防御措施
  5. SOC行动指南: 针对安全运营团队的优先级建议
  6. 总结: 用简洁的段落收尾，不要包含任何来源链接

正文格式规范:
- 使用 <section> 标签组织各模块
- 使用 <h2> 标签作为模块标题，带颜色标记(如: color:#d97706)
- 使用 <p> 标签包裹段落，line-height设为1.8
- 重要技术术语使用 <strong> 加粗
- 禁止: 任何 <a> 标签、脚本标签
- 禁止: 出现原文URL、来源标注
- 图片使用: <img src="图片URL" style="width:100%;border-radius:8px;margin:16px 0;" />

JSON格式:
{{
  "title": "...",
  "summary": "...",
  "wxhtml": "<section>...</section>"
}}
""".strip()

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