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
            "<section style='margin-top:32px;'>"
            "<h3 style='display:inline-block;margin:0 0 16px;font-size:18px;color:#1C1F23;font-weight:bold;padding-bottom:6px;border-bottom:2px solid #0052D9;letter-spacing:1px;'>防守方执行清单</h3>"
            "<p style='margin:0 0 16px;color:#4B5563;font-size:16px;line-height:1.8;text-align:justify;'>建议从三个层面立即落地：<br><strong style='color:#0052D9;font-weight:600;'>第一，资产层面</strong>先确认受影响系统版本、暴露面和外网入口，把高风险节点拉出清单；<br><strong style='color:#0052D9;font-weight:600;'>第二，检测层面</strong>增加针对该攻击链的日志规则与告警聚合，优先关注异常登录、提权与横向移动行为；<br><strong style='color:#0052D9;font-weight:600;'>第三，响应层面</strong>同步修复优先级，明确24小时内可完成项。</p>"
            "<p style='margin:0;color:#4B5563;font-size:16px;line-height:1.8;text-align:justify;'>若你在企业内负责安全运营，建议将本文分为<strong>“高层简报版”</strong>与<strong>“执行任务版”</strong>。简报版强调业务风险与处置进度；任务版明确责任人、系统、时间窗与验收标准，全面提升团队协同效率并降低沟通成本。</p>"
            "</section>"
        )
    return body


def _append_missing_images(body: str, github_images: list[str]) -> str:
    missing_images = [u for u in github_images if u not in body]
    for u in missing_images:
        body += (
            "<section style='margin:28px 0;text-align:center;'>"
            f"<img src='{escape(u)}' style='max-width:100%;height:auto;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.06);'/>"
            "</section>"
        )
    return body


def _append_summary_section(body: str, summary: str) -> str:
    body += (
        "<section style='margin-top:32px;padding:24px;background-color:#F8FAFC;border-left:4px solid #0052D9;border-radius:0 8px 8px 0;box-shadow:0 2px 8px rgba(0,0,0,0.02);'>"
        "<h3 style='margin:0 0 12px;font-size:18px;color:#0052D9;font-weight:bold;letter-spacing:0.5px;'>情报总结</h3>"
        f"<p style='margin:0;color:#334155;font-size:15px;line-height:1.8;text-align:justify;'>{escape(summary)}</p>"
        "</section>"
    )
    return body


def _append_tags_section(body: str, text_tags: list[str]) -> str:
    if text_tags:
        tags_html = "".join([f"<span style='display:inline-block;margin:0 8px 8px 0;padding:4px 14px;background-color:#F1F5F9;color:#64748B;font-size:13px;border-radius:100px;letter-spacing:0.5px;'>{escape(t)}</span>" for t in text_tags])
        body += (
            "<section style='margin-top:36px;'>"
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