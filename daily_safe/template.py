from __future__ import annotations

from html import escape
from typing import List, Tuple


def _minify_html(html: str) -> str:
    lines = html.strip().split('\n')
    return ''.join(line.strip() for line in lines if line.strip())


PAGE_TEMPLATE = _minify_html('''
<section style="max-width: 100%; margin: 0 auto; box-sizing: border-box; padding: 0; font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif; background-color: #ffffff; font-size: 15px; color: #333;">
    {header}
    {body}
    {footer}
</section>
''')


HEADER_TEMPLATE = _minify_html('''
<section style="width: 100%; margin-bottom: 20px;">
    <img src="{header_img}" style="width: 100%; display: block; border-radius: 0;" alt="Header"/>
</section>
''')


ALERT_BANNER_TEMPLATE = _minify_html('''
<section style="background: linear-gradient(135deg, #1e3a5f 0%, #0f1f33 100%); padding: 20px 16px; border-radius: 12px; margin-bottom: 16px; border-left: 4px solid #ef4444;">
    <section style="color: #ef4444; font-size: 11px; font-weight: bold; letter-spacing: 2px; margin-bottom: 6px; font-family: Arial, sans-serif;">
        CYBERSECURITY INTELLIGENCE
    </section>
    <h1 style="color: #ffffff; font-size: 20px; font-weight: bold; line-height: 1.4; margin: 0;">{title}</h1>
</section>
''')


THREAT_SECTION_TEMPLATE = _minify_html('''
<section style="margin-bottom: 24px;">
    <section style="display: flex; align-items: center; margin-bottom: 12px;">
        <span style="background-color: #dc2626; width: 4px; height: 18px; display: inline-block; margin-right: 8px;"></span>
        <span style="font-size: 15px; font-weight: bold; color: #dc2626; letter-spacing: 1px;">{section_title}</span>
    </section>
    <section style="font-size: 14px; color: #475569; line-height: 1.9; text-align: justify; word-wrap: break-word;">
        {content}
    </section>
</section>
''')


TECH_SECTION_TEMPLATE = _minify_html('''
<section style="margin-bottom: 24px;">
    <section style="display: flex; align-items: center; margin-bottom: 12px;">
        <span style="background-color: #2563eb; width: 4px; height: 18px; display: inline-block; margin-right: 8px;"></span>
        <span style="font-size: 15px; font-weight: bold; color: #2563eb; letter-spacing: 1px;">{section_title}</span>
    </section>
    <section style="font-size: 14px; color: #475569; line-height: 1.9; text-align: justify; word-wrap: break-word;">
        {content}
    </section>
</section>
''')


IMPACT_SECTION_TEMPLATE = _minify_html('''
<section style="margin-bottom: 24px;">
    <section style="display: flex; align-items: center; margin-bottom: 12px;">
        <span style="background-color: #d97706; width: 4px; height: 18px; display: inline-block; margin-right: 8px;"></span>
        <span style="font-size: 15px; font-weight: bold; color: #d97706; letter-spacing: 1px;">{section_title}</span>
    </section>
    <section style="font-size: 14px; color: #475569; line-height: 1.9; text-align: justify; word-wrap: break-word;">
        {content}
    </section>
</section>
''')


DEFENSE_SECTION_TEMPLATE = _minify_html('''
<section style="margin-bottom: 24px; background-color: #f0fdf4; border: 1px solid #86efac; border-radius: 10px; padding: 16px;">
    <section style="display: flex; align-items: center; margin-bottom: 12px;">
        <span style="background-color: #16a34a; width: 4px; height: 18px; display: inline-block; margin-right: 8px;"></span>
        <span style="font-size: 15px; font-weight: bold; color: #16a34a; letter-spacing: 1px;">{section_title}</span>
    </section>
    <section style="font-size: 14px; color: #475569; line-height: 1.9;">
        {content}
    </section>
</section>
''')


SOC_SECTION_TEMPLATE = _minify_html('''
<section style="margin-bottom: 24px; background-color: #fef3c7; border: 1px solid #fcd34d; border-radius: 10px; padding: 16px;">
    <section style="display: flex; align-items: center; margin-bottom: 12px;">
        <span style="background-color: #d97706; width: 4px; height: 18px; display: inline-block; margin-right: 8px;"></span>
        <span style="font-size: 15px; font-weight: bold; color: #d97706; letter-spacing: 1px;">{section_title}</span>
    </section>
    <section style="font-size: 14px; color: #475569; line-height: 1.9;">
        {content}
    </section>
</section>
''')


SUMMARY_SECTION_TEMPLATE = _minify_html('''
<section style="margin-bottom: 20px; padding: 16px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;">
    <section style="display: flex; align-items: center; margin-bottom: 10px;">
        <span style="background-color: #0f172a; width: 4px; height: 18px; display: inline-block; margin-right: 8px;"></span>
        <span style="font-size: 15px; font-weight: bold; color: #0f172a; letter-spacing: 1px;">{section_title}</span>
    </section>
    <section style="font-size: 14px; color: #475569; line-height: 1.8;">
        {content}
    </section>
</section>
''')


DIVIDER_TEMPLATE = '<section style="width: 85%; height: 1px; border-top: 1px dashed #cbd5e1; margin: 0 auto 20px auto;"></section>'


PARAGRAPH_TEMPLATE = '<p style="margin: 0 0 14px 0;">{text}</p>'
PARAGRAPH_LAST_TEMPLATE = '<p style="margin: 0;">{text}</p>'


def render_paragraph(text: str, is_last: bool = False) -> str:
    if is_last:
        return PARAGRAPH_LAST_TEMPLATE.format(text=escape(text))
    return PARAGRAPH_TEMPLATE.format(text=escape(text))


def render_header(header_img: str) -> str:
    return HEADER_TEMPLATE.format(header_img=escape(header_img))


def render_alert_banner(title: str) -> str:
    return ALERT_BANNER_TEMPLATE.format(title=escape(title))


def render_section(section_type: str, section_title: str, paragraphs: List[str]) -> str:
    content = '\n'.join(paragraphs)

    if section_type == 'threat':
        template = THREAT_SECTION_TEMPLATE
    elif section_type == 'tech':
        template = TECH_SECTION_TEMPLATE
    elif section_type == 'impact':
        template = IMPACT_SECTION_TEMPLATE
    elif section_type == 'defense':
        template = DEFENSE_SECTION_TEMPLATE
    elif section_type == 'soc':
        template = SOC_SECTION_TEMPLATE
    else:
        template = SUMMARY_SECTION_TEMPLATE

    return template.format(section_title=escape(section_title), content=content)


def render_template(header_img: str, source_title: str, body: str) -> str:
    return PAGE_TEMPLATE.format(
        header=render_header(header_img),
        body=render_alert_banner(source_title) + body,
        footer='',
    )