from __future__ import annotations

from html import escape


def _minify_html(html: str) -> str:
    lines = html.strip().split('\n')
    return ''.join(line.strip() for line in lines if line.strip())


PAGE_TEMPLATE = _minify_html('''
<section style="max-width: 677px; margin: 0 auto; box-sizing: border-box; padding: 16px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji'; background-color: #f7f9fc; font-size: 16px; color: #333333; line-height: 1.8;">
    <section style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.04); padding-bottom: 32px;">
        {header}
        <section style="padding: 0 24px;">
            {body}
        </section>
    </section>
</section>
''')

HEADER_TEMPLATE = _minify_html('''
<section style="width: 100%; margin-bottom: 24px; position: relative;">
    <img src="{header_img}" style="width: 100%; display: block; border-radius: 0;" alt="Header"/>
</section>
''')

ALERT_BANNER_TEMPLATE = _minify_html('''
<section style="margin-bottom: 32px;">
    <section style="display: flex; align-items: center; margin-bottom: 12px;">
        <span style="display: inline-block; padding: 4px 10px; background-color: #ffeef0; color: #E34D59; font-size: 13px; font-weight: 600; border-radius: 4px; letter-spacing: 1px;">全球威胁情报</span>
    </section>
    <h1 style="color: #1C1F23; font-size: 24px; font-weight: bold; line-height: 1.5; margin: 0; padding-bottom: 16px; border-bottom: 1px solid #E5E7EB;">{title}</h1>
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