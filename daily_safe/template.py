from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_FILE = ROOT / "daily_safe" / "template.html"


def get_template() -> str:
    return TEMPLATE_FILE.read_text(encoding="utf-8")


def render_template(header_img: str, source_title: str, body: str) -> str:
    template = get_template()
    return (
        template
        .replace("{{HEADER_IMG}}", header_img)
        .replace("{{SOURCE_TITLE}}", source_title)
        .replace("{{BODY}}", body)
    )