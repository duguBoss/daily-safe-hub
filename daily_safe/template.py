from __future__ import annotations

from html import escape


def _minify_html(html: str) -> str:
    lines = html.strip().split('\n')
    return ''.join(line.strip() for line in lines if line.strip())


PAGE_TEMPLATE = _minify_html('''
<section style='font-size:16px;line-height:1.78;color:#111827;'>
    <section style='margin:0 0 14px;'>
        <img src='{header_img}' style='width:100%;height:auto;display:block;border-radius:12px;'/>
    </section>
    <section style='padding:14px;border-radius:12px;background:#0b1220;color:#e5e7eb;border:1px solid #1f2937;margin-bottom:14px;'>
        <p style='margin:0 0 6px;font-size:13px;color:#fca5a5;'>DAILY SAFE BRIEF</p>
        <h2 style='margin:0 0 8px;font-size:22px;line-height:1.4;'>{source_title}</h2>
    </section>
    <section style='padding:14px;border-radius:12px;background:#ffffff;border:1px solid #e5e7eb;'>
        {body}
    </section>
</section>
''')


def render_template(header_img: str, source_title: str, body: str) -> str:
    return PAGE_TEMPLATE.format(
        header_img=escape(header_img),
        source_title=escape(source_title),
        body=body,
    )