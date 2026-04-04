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
你是一位顶级的网络安全情报分析专家和资深科技媒体主编。你需要将提供的英文安全资讯，深度提炼并转化为极为专业、结构严谨、排版精美、具有极高阅读价值和决策参考意义的中文安全情报报告。

内容素材:
{article_blocks}

输出格式要求:
1) 输出纯JSON，包含且仅包含: title, summary, wxhtml
2) 所有正文必须使用严谨、专业的简体中文，避免机器翻译感。

标题要求 (title):
- 长度: 18-28个中文字符
- 必须包含: 具体的威胁组织/CVE编号/漏洞名称/或核心攻击技术
- 必须包含: 关键影响（例如：破坏规模、针对行业等）
- 风格: 如同顶级安全智库的深度研报标题，极具信息密度和专业权威感，但实事求是。
- 绝不使用"速报/要闻/汇总/盘点"等低沉淀感词汇。
- 绝不出现完整URL或"来源"字样。

摘要要求 (summary):
- 长度: 120-180个中文字符
- 内容: 以高管或CISO视角，用一两句话讲透“发生了什么、到底有多危险、需要采取什么关键行动”。这是信息的精华。

正文要求 (wxhtml):
- 长度: 1500-2500个中文字符
- 定位: 面向CISO、安全架构师、一线安全专家的深度剖析报告。
- 结构必须严格包含以下模块（按顺序）：
  1. 威胁态势研判: 概括该威胁背景、攻击组织特征、目标画像及本次攻击意图。
  2. 技术链路剖析: 深度解析攻击手法、漏洞利用过程、TTPs（需突出战术与技术细节）。
  3. 影响面与风险评估: 详细说明受影响的系统版本、组件及引发的次生风险。
  4. 缓解与防御预案: 极具实操性的短期应急措施和中长期加固指南。
  5. 运营洞察 (SOC/蓝军视角): 从威胁狩猎、日志研判、告警规则等实战角度给出专家建议。

正文极其严格的高级HTML排版规范 (请完全按照以下格式进行输出，这是微信公众号精美排版的必须条件):
- 模块结构：各个核心模块必须使用 `<section style="margin-bottom: 36px;"></section>` 包裹。
- 模块标题：统一使用以下优美的标题样式（不要改变style属性）：
  <section style="display:flex;align-items:center;margin-bottom:16px;">
    <span style="display:inline-block;width:4px;height:18px;background-color:#0052D9;border-radius:2px;margin-right:10px;"></span>
    <h2 style="margin:0;font-size:20px;color:#1C1F23;font-weight:700;letter-spacing:0.5px;">此处写模块名称</h2>
  </section>
- 段落文本：用 `<p style="margin:0 0 16px;font-size:16px;color:#4B5563;line-height:1.8;text-align:justify;word-wrap:break-word;">` 包裹。若是列表项，也请保持字体颜色和行高一致。
- 重点强调文字：重要的技术名词、特定的影响系统、核心数据等，必须使用 `<strong style="color:#0052D9;font-weight:600;">关键字</strong>` 加以高亮。
- IOC信息/代码段：对于IP/Hash/路径/命令词等，使用 `<code style="display:inline-block;background-color:#F2F5F8;color:#E34D59;padding:2px 6px;border-radius:4px;font-family:monospace;font-size:14px;word-break:break-all;">内容</code>`。
- 警示引用或核心思想（可选使用）：
  <section style="margin:20px 0;padding:16px 20px;background-color:#F8FAFC;border-left:4px solid #0052D9;border-radius:4px;">
    <p style="margin:0;font-size:15px;color:#334155;line-height:1.7;">引用内容</p>
  </section>
- 图片使用：必须且只使用素材中提供的 Images 数组中的图片。
  插入图片时必须严格采用如下格式（不含任何外部链接，且只用素材图片）：
  <section style="margin:24px 0;text-align:center;">
    <img src="素材提供的图片URL" style="max-width:100%;height:auto;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.06);" />
  </section>
- 绝对禁止的内容：任何 `<a>` 标签、`<script>`。绝对禁止以"综上所述"、“以上就是”等废话结尾，要在专业内容处戛然而止。

JSON输出格式:
{{
  "title": "...",
  "summary": "...",
  "wxhtml": "<section style='margin-bottom: 36px;'><section style='display:flex;...'>...</section><p style='...'>...</p></section>"
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