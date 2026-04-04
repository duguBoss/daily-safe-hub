from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class NewsItem:
    title: str
    link: str
    description_html: str
    pub_date: str
    enclosure_url: str | None


@dataclass
class ArticleDetail:
    title: str
    source_url: str
    pub_date: str
    content_text: str
    image_urls: list[str]


@dataclass
class GeminiResult:
    title: str
    summary: str
    wxhtml: str