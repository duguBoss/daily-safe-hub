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
            "<section style='margin-top:14px;'>"
            "<h3 style='margin:0 0 8px;font-size:20px;color:#0f172a;'>防守方执行清单</h3>"
            "<p>建议从三个层面立即落地：第一，资产层面先确认受影响系统版本、暴露面和外网入口，"
            "把高风险节点拉出清单；第二，检测层面增加针对该攻击链的日志规则与告警聚合，"
            "优先关注异常登录、提权与横向移动行为；第三，响应层面同步修复优先级，明确24小时内可完成项。"
            "</p>"
            "<p>若你在企业内负责安全运营，可以把本文拆成"高层汇报版 + 执行任务版"两份："
            "汇报版强调业务影响与处置进展，任务版明确人、系统、时间和验收标准。这样既能提升团队协作效率，"
            "也能减少事件处理过程中的信息断层和重复沟通成本。</p>"
            "</section>"
        )
    return body


def _append_missing_images(body: str, github_images: list[str]) -> str:
    missing_images = [u for u in github_images if u not in body]
    for u in missing_images:
        body += (
            "<figure style='margin:16px 0;padding:8px;border:1px solid #fca5a5;border-radius:10px;'>"
            f"<img src='{escape(u)}' style='width:100%;height:auto;border-radius:6px;'/>"
            "</figure>"
        )
    return body


def _append_summary_section(body: str, summary: str) -> str:
    body += (
        "<section style='margin-top:18px;padding:14px;background:#fff7ed;border:1px solid #fdba74;border-radius:10px;'>"
        "<h3 style='margin:0 0 8px;font-size:18px;color:#7c2d12;'>总结</h3>"
        f"<p style='margin:0;color:#7c2d12;'>{escape(summary)}</p>"
        "</section>"
    )
    return body


def _append_tags_section(body: str, text_tags: list[str]) -> str:
    if text_tags:
        tags_text = " ".join(text_tags)
        body += (
            "<section style='margin-top:10px;padding:12px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;'>"
            "<p style='margin:0;font-size:14px;color:#334155;'>"
            f"标签：{escape(tags_text)}"
            "</p>"
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