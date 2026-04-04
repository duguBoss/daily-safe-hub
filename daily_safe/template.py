from __future__ import annotations

from html import escape


def _minify_html(html: str) -> str:
    lines = html.strip().split('\n')
    return ''.join(line.strip() for line in lines if line.strip())


PAGE_TEMPLATE = _minify_html('''
<section style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif; font-size: 16px; color: #333; line-height: 1.7; background-color: #fff; text-align: justify; word-wrap: break-word;">
    {header}
    <section>
        {body}
    </section>
</section>
''')

HEADER_TEMPLATE = _minify_html('''
<section style="width: 100%; margin-bottom: 24px;">
    <img src="{header_img}" style="width: 100%; display: block;" alt="Header"/>
</section>
''')

ALERT_BANNER_TEMPLATE = _minify_html('''
<section style="margin-bottom: 28px;">
    <h1 style="color: #1a1a1a; font-size: 22px; font-weight: 600; line-height: 1.5; margin: 0 0 12px 0;">{title}</h1>
    <section style="display: inline-block; padding: 2px 8px; background-color: #f87171; color: #ffffff; font-size: 12px; font-weight: 500; border-radius: 2px; letter-spacing: 0.5px;">深度威胁情报</section>
</section>
''')

def render_header(header_img: str) -> str:
    return HEADER_TEMPLATE.format(header_img=escape(header_img))


def render_alert_banner(title: str) -> str:
    return ALERT_BANNER_TEMPLATE.format(title=escape(title))


def render_template(header_img: str, source_title: str, body: str) -> str:
    return PAGE_TEMPLATE.format(
        header=render_header(header_img),
        body=render_alert_banner(source_title) + body,
    )