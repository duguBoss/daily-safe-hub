from __future__ import annotations

import re
from html import escape

from bs4 import BeautifulSoup

from .config import HEADER_IMG
from .template import render_template


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


def _build_fallback_body(source_title: str) -> str:
    return (
        f"<section><h2>{escape(source_title)}</h2>"
        "<p>这是一篇面向实战场景的安全情报速读，帮助你快速掌握威胁动态与防守动作。</p>"
        "</section>"
    )


def _clean_body(body: str) -> str:
    body = re.sub(r"<a[^>]*>(.*?)</a>", r"\1", body, flags=re.I | re.S)
    body = re.sub(r"(原文地址|来源|source|reference)[:：]?\s*https?://\S+", "", body, flags=re.I)
    body = re.sub(r"https?://\S+", "", body)
    body = re.sub(r"(原文地址|文章来源|来源)[:：]?", "", body, flags=re.I)
    body = re.sub(r"<script[\s\S]*?</script>", "", body, flags=re.I)
    return body


def _ensure_min_content(body: str) -> str:
    text_len = len(BeautifulSoup(body, "html.parser").get_text(" ", strip=True))
    if text_len < 900:
        body += (
            "<h2 style='font-size:18px;font-weight:600;color:#0f172a;margin:28px 0 12px 0;border-bottom:1px solid #e2e8f0;padding-bottom:6px;'>🛠 防守侧行动指南</h2>"
            "<p style='margin:0 0 16px;color:#334155;font-size:16px;line-height:1.7;'>建议安全团队按以下优先级响应：<br><strong style='color:#0369a1;'>1. 盘点资产暴露面：</strong> 明确受直接影响的系统及外部入口，标记高危节点。<br><strong style='color:#0369a1;'>2. 增补检测规则：</strong> 根据TTPs在SIEM/NDR中布防告警，重点捕捉异常活动与越权尝试。<br><strong style='color:#0369a1;'>3. 加固与拦截：</strong> 更新防护设备策略并实施紧急补丁，设定阻断指标。</p>"
        )
    return body


def _append_missing_images(body: str, github_images: list[str]) -> str:
    if not github_images:
        return body

    soup = BeautifulSoup(body, "html.parser")
    paragraphs = soup.find_all("p")
    
    missing_images = [u for u in github_images if str(u) not in body]
    if not missing_images:
        return body

    if not paragraphs:
        for u in missing_images:
            body += f"<section style='margin-top:20px;'><img src='{escape(u)}' style='width:100%;height:auto;margin-bottom:12px;display:block;border-radius:6px;box-shadow:0 4px 12px rgba(0,0,0,0.05);'/></section>"
        return body

    num_p = len(paragraphs)
    num_img = len(missing_images)
    step = max(1, num_p // (num_img + 1))
    
    for i, img_url in enumerate(missing_images):
        idx = (i + 1) * step
        if idx >= num_p:
            idx = num_p - 1
            
        target_p = paragraphs[idx]
        img_tag = soup.new_tag("img", src=img_url, style="width:100%;height:auto;margin:20px 0;display:block;border-radius:6px;box-shadow:0 4px 12px rgba(0,0,0,0.05);")
        target_p.insert_after(img_tag)
        
    for empty_img in soup.find_all("img"):
        src = empty_img.get("src", "")
        if not src or "素材URL" in src or "素材图片URL" in src or empty_img.get("src") == "":
            empty_img.decompose()
            
    return str(soup)


def _append_summary_section(body: str, summary: str) -> str:
    body += (
        "<section style='margin-top:32px;padding:16px 20px;background-color:#f8fafc;border-radius:6px;border-left:4px solid #0369a1;'>"
        "<p style='margin:0;color:#0f172a;font-size:15px;line-height:1.7;font-weight:500;'><span style='color:#0369a1;font-weight:600;margin-right:8px;'>情报总结：</span>"
        f"{escape(summary)}</p>"
        "</section>"
    )
    return body


def _append_tags_section(body: str, text_tags: list[str]) -> str:
    if text_tags:
        tags_html = "".join([f"<span style='display:inline-block;margin:0 6px 6px 0;color:#64748b;font-size:14px;'>{escape(t)}</span>" for t in text_tags])
        body += (
            "<section style='margin-top:28px;border-top:1px dashed #cbd5e1;padding-top:16px;'>"
            f"<section>{tags_html}</section>"
            "</section>"
        )
    return body


def ensure_wxhtml(
    wxhtml: str,
    source_title: str,
    github_images: list[str],
    summary: str,
    text_tags: list[str],
) -> str:
    body = (wxhtml or "").strip()
    if not body:
        body = _build_fallback_body(source_title)

    body = _clean_body(body)
    body = _ensure_min_content(body)
    body = _append_missing_images(body, github_images)
    body = _append_summary_section(body, summary)
    body = _append_tags_section(body, text_tags)

    return render_template(
        header_img=HEADER_IMG,
        source_title=source_title,
        body=body,
    )