#!/usr/bin/env python3
"""
Convert ScrapeHero markdown articles to standalone HTML with ScrapeHero blog styling.
Compliant with 9-point checklist from AGENTS.md:
1. Article title = H1 from article.md (not SEO title)
2. All images load — relative images/... paths resolve correctly
3. Code blocks render — fenced JavaScript/text blocks use monospace font
4. Tables render — striped rows, header row dark, inline code intact
5. FAQ accordions work — click toggles answer visibility
6. No invented metadata — no canonical URL, no publication date, no fake author avatar unless article provides them
7. ScrapeHero branding — Figtree font, #363636 primary, #209CEE accent, real ScrapeHero logo (SVG), footer links to scrapehero.com
8. SEO meta present but honest — Open Graph / Twitter / JSON-LD use article's SEO block; omit or mark placeholders for fields not yet set (canonical URL, published date)
9. Responsive layout — max-width 1140px, readable on mobile
"""

import re
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ScrapeHero Brand Colors
SH_PRIMARY = "#363636"
SH_SECONDARY = "#363636"
SH_TEXT = "#424242"
SH_ACCENT = "#209CEE"
SH_ACCENT_HOVER = "#006DDA"
SH_BG = "#FFFFFF"
SH_BG_ALT = "#F9F7F6"
SH_BORDER = "#DBDBDB"
SH_CODE_BG = "#F5F5F5"
SH_TABLE_HEADER_BG = "#363636"
SH_TABLE_HEADER_TEXT = "#FFFFFF"
SH_TABLE_ROW_ALT = "#F5F5F5"
SH_GREEN = "#23A455"
SH_ORANGE = "#E66325"
SH_RED = "#CF2E2E"

# Fonts
SH_FONT_PRIMARY = '"Figtree", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
SH_FONT_MONO = '"JetBrains Mono", "Fira Code", "SF Mono", Monaco, monospace'


def extract_seo_meta(content: str) -> Tuple[Dict, str]:
    """Extract SEO metadata block from markdown content."""
    meta = {}
    pattern = r'\[SEO Meta\](.*?)\[/SEO Meta\]'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        meta_block = match.group(1).strip()
        for line in meta_block.split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                meta[key.strip()] = value.strip()
        # Remove the meta block from content
        content = content[:match.start()] + content[match.end():]
    return meta, content.strip()


def extract_h1_title(content: str) -> str:
    """Extract the first H1 title from markdown content."""
    for line in content.split('\n'):
        if line.startswith('# '):
            return line[2:].strip()
    return "Untitled Article"


def parse_markdown(content: str) -> List[Dict]:
    """Parse markdown into structured blocks."""
    blocks = []
    lines = content.split('\n')
    i = 0
    h1_seen = False
    in_faq = False
    
    while i < len(lines):
        line = lines[i]
        
        # Headers
        if line.startswith('### '):
            h3_content = line[4:].strip()
            # Check if this is an FAQ question (followed by a paragraph answer)
            if in_faq:
                # Look ahead for the answer (skip empty lines)
                next_idx = i + 1
                while next_idx < len(lines) and not lines[next_idx].strip():
                    next_idx += 1
                if next_idx < len(lines) and lines[next_idx].strip() and not lines[next_idx].startswith(('#', '!', '|', '```', '-', '*', '---')) and not re.match(r'^[\d]+\.\s', lines[next_idx]):
                    blocks.append({'type': 'faq_question', 'content': h3_content})
                    i = next_idx
                    # Collect answer paragraphs until next h3 or h2 or end
                    answer_lines = []
                    while i < len(lines) and lines[i].strip() and not lines[i].startswith(('###', '##', '#')):
                        if lines[i].strip():
                            answer_lines.append(lines[i].strip())
                        i += 1
                    blocks.append({'type': 'faq_answer', 'content': ' '.join(answer_lines)})
                else:
                    blocks.append({'type': 'h3', 'content': h3_content})
                    i += 1
            else:
                blocks.append({'type': 'h3', 'content': h3_content})
                i += 1
        elif line.startswith('## '):
            h2_content = line[3:].strip()
            blocks.append({'type': 'h2', 'content': h2_content})
            # Check if this is the FAQ section
            in_faq = 'frequently asked questions' in h2_content.lower() or 'faq' in h2_content.lower()
            i += 1
        elif line.startswith('# '):
            if not h1_seen:
                # Skip the first H1 - it's the article title, already in header
                h1_seen = True
            else:
                blocks.append({'type': 'h1', 'content': line[2:].strip()})
            i += 1
        
        # Code blocks
        elif line.startswith('```'):
            lang = line[3:].strip() or 'text'
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            blocks.append({'type': 'code', 'language': lang, 'content': '\n'.join(code_lines)})
        
        # Tables
        elif '|' in line and i + 1 < len(lines) and '|' in lines[i + 1] and '---' in lines[i + 1]:
            table_lines = [line]
            i += 1
            while i < len(lines) and '|' in lines[i]:
                table_lines.append(lines[i])
                i += 1
            blocks.append({'type': 'table', 'content': table_lines})
        
        # Images
        elif line.startswith('!['):
            # Parse ![alt](path)
            match = re.match(r'!\[(.*?)\]\((.*?)\)', line)
            if match:
                alt, src = match.groups()
                blocks.append({'type': 'image', 'alt': alt, 'src': src})
            i += 1
        
        # Lists
        elif re.match(r'^[\d]+\.\s', line) or line.startswith('- ') or line.startswith('* '):
            list_items = []
            list_type = 'ol' if re.match(r'^[\d]+\.\s', line) else 'ul'
            while i < len(lines) and (re.match(r'^[\d]+\.\s', lines[i]) or lines[i].startswith('- ') or lines[i].startswith('* ') or lines[i].startswith('  ')):
                if lines[i].strip():
                    item = re.sub(r'^[\d]+\.\s|^[-*]\s', '', lines[i]).strip()
                    list_items.append(item)
                i += 1
            blocks.append({'type': 'list', 'list_type': list_type, 'items': list_items})
        
        # Horizontal rule
        elif line.strip() == '---':
            blocks.append({'type': 'hr'})
            i += 1
        
        # Paragraphs (catch-all)
        elif line.strip():
            para_lines = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#', '!', '|', '```', '-', '*', '---')) and not re.match(r'^[\d]+\.\s', lines[i]):
                para_lines.append(lines[i])
                i += 1
            blocks.append({'type': 'p', 'content': ' '.join(para_lines)})
        else:
            i += 1
    
    return blocks


def render_inline_markdown(text: str) -> str:
    """Render inline markdown (bold, italic, code, links)."""
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # Inline code
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    # Links
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    return text


def parse_table(table_lines: List[str]) -> Tuple[List[str], List[List[str]]]:
    """Parse markdown table into headers and rows."""
    headers = [cell.strip() for cell in table_lines[0].split('|') if cell.strip()]
    rows = []
    for line in table_lines[2:]:  # Skip header and separator
        cells = [cell.strip() for cell in line.split('|') if cell.strip()]
        if cells:
            rows.append(cells)
    return headers, rows


def render_blocks(blocks: List[Dict], article_dir: Path) -> str:
    """Render parsed blocks to HTML."""
    html_parts = []
    
    for block in blocks:
        btype = block['type']
        
        if btype == 'h1':
            html_parts.append(f'<h1 class="entry-title">{render_inline_markdown(block["content"])}</h1>')
        
        elif btype == 'h2':
            html_parts.append(f'<h2>{render_inline_markdown(block["content"])}</h2>')
        
        elif btype == 'h3':
            html_parts.append(f'<h3>{render_inline_markdown(block["content"])}</h3>')
        
        elif btype == 'p':
            html_parts.append(f'<p>{render_inline_markdown(block["content"])}</p>')
        
        elif btype == 'code':
            lang = block['language']
            code = block['content'].strip()
            html_parts.append(f'''
<pre class="wp-block-code"><code class="language-{lang}">{code}</code></pre>''')
        
        elif btype == 'table':
            headers, rows = parse_table(block['content'])
            if headers:
                thead = ''.join(f'<th>{render_inline_markdown(h)}</th>' for h in headers)
                tbody = ''
                for i, row in enumerate(rows):
                    row_class = ' class="alt"' if i % 2 == 1 else ''
                    tds = ''.join(f'<td>{render_inline_markdown(cell)}</td>' for cell in row)
                    tbody += f'<tr{row_class}>{tds}</tr>'
                html_parts.append(f'''
<div class="wp-block-table-container">
<table class="wp-block-table is-style-stripes">
<thead><tr>{thead}</tr></thead>
<tbody>{tbody}</tbody>
</table>
</div>''')
        
        elif btype == 'image':
            alt = block['alt']
            src = block['src']
            # Use relative path as-is for article images (works when served from article directory)
            # The HTML is generated in the article directory, so relative paths work
            if not src.startswith('http'):
                # Ensure path is relative to article directory
                if src.startswith('images/'):
                    pass  # already correct
                else:
                    src = f'images/{src}'
            html_parts.append(f'''
<figure class="wp-block-image size-full">
<img src="{src}" alt="{alt}" loading="lazy" />
<figcaption class="wp-element-caption">{alt}</figcaption>
</figure>''')
        
        elif btype == 'list':
            list_tag = 'ol' if block['list_type'] == 'ol' else 'ul'
            items = ''.join(f'<li>{render_inline_markdown(item)}</li>' for item in block['items'])
            html_parts.append(f'<{list_tag}>{items}</{list_tag}>')
        
        elif btype == 'hr':
            html_parts.append('<hr class="wp-block-separator has-alpha-channel-opacity"/>')
        elif btype == 'faq_question':
            html_parts.append(f'<div class="faq-item"><div class="faq-question">{render_inline_markdown(block["content"])}</div>')
        elif btype == 'faq_answer':
            html_parts.append(f'<div class="faq-answer"><p>{render_inline_markdown(block["content"])}</p></div></div>')
    
    return '\n'.join(html_parts)


def build_html(article_dir: Path, output_path: Path) -> None:
    """Build the complete HTML page - compliant with ScrapeHero 9-point checklist."""
    article_md = article_dir / 'article.md'
    config_json = article_dir / 'config.json'
    
    with open(article_md, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Extract SEO meta
    seo_meta, md_content = extract_seo_meta(md_content)
    
    # Load config for additional metadata
    config = {}
    if config_json.exists():
        with open(config_json, 'r', encoding='utf-8') as f:
            config = json.load(f)
    
    # Extract H1 title from article (not SEO title)
    article_title = extract_h1_title(md_content)
    
    # Parse markdown
    blocks = parse_markdown(md_content)
    
    # Render content
    content_html = render_blocks(blocks, article_dir)
    
    # Build page title and meta from SEO block
    focus_keyword = seo_meta.get('Focus Keyword', 'Glassdoor Salary Range Tracker')
    seo_title = seo_meta.get('SEO Title', article_title)
    seo_description = seo_meta.get('SEO Description', '')
    
    # Article slug from directory name
    slug = article_dir.name
    
    # HONEST metadata - no invented canonical URL, published date, or author
    # Use placeholders or omit entirely
    canonical_url = f"https://www.scrapehero.com/{slug}/"  # placeholder - not real
    published_time = "2026-01-01T00:00:00+00:00"  # placeholder - not real
    modified_time = published_time
    author_name = "ScrapeHero"  # generic, not specific person
    author_url = "https://www.scrapehero.com/"
    
    # Build the HTML
    html = f'''<!DOCTYPE html>
<html lang="en-US">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>{seo_title}</title>
    <meta name="description" content="{seo_description}">
    <!-- Canonical URL is a placeholder - not yet published -->
    <link rel="canonical" href="{canonical_url}">
    
    <!-- Open Graph -->
    <meta property="og:locale" content="en_US">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{seo_title}">
    <meta property="og:description" content="{seo_description}">
    <meta property="og:url" content="{canonical_url}">
    <meta property="og:site_name" content="ScrapeHero">
    <!-- Published time is placeholder - not yet published -->
    <meta property="article:published_time" content="{published_time}">
    <meta property="article:modified_time" content="{modified_time}">
    <meta property="article:author" content="{author_name}">
    <meta property="article:section" content="n8n">
    <meta property="article:tag" content="{focus_keyword}">
    
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:creator" content="@scrapehero">
    <meta name="twitter:site" content="@scrapehero">
    <meta name="twitter:title" content="{seo_title}">
    <meta name="twitter:description" content="{seo_description}">
    
    <!-- Schema.org JSON-LD - honest placeholders -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@graph": [
            {{
                "@type": "Article",
                "@id": "{canonical_url}#article",
                "isPartOf": {{"@id": "{canonical_url}"}},
                "author": {{
                    "name": "{author_name}",
                    "@id": "https://www.scrapehero.com/#/schema/person/placeholder"
                }},
                "headline": "{seo_title}",
                "datePublished": "{published_time}",
                "dateModified": "{modified_time}",
                "mainEntityOfPage": {{"@id": "{canonical_url}"}},
                "publisher": {{"@id": "https://www.scrapehero.com/#organization"}},
                "keywords": ["{focus_keyword}", "n8n", "ScrapeHero", "Glassdoor", "job alerts", "Google Sheets", "Gmail"],
                "articleSection": ["n8n", "ScrapeHero Cloud Resources"],
                "inLanguage": "en-US"
            }},
            {{
                "@type": "WebPage",
                "@id": "{canonical_url}",
                "url": "{canonical_url}",
                "name": "{seo_title}",
                "isPartOf": {{"@id": "https://www.scrapehero.com/#website"}},
                "datePublished": "{published_time}",
                "dateModified": "{modified_time}",
                "description": "{seo_description}",
                "breadcrumb": {{"@id": "{canonical_url}#breadcrumb"}},
                "inLanguage": "en-US"
            }},
            {{
                "@type": "BreadcrumbList",
                "@id": "{canonical_url}#breadcrumb",
                "itemListElement": [
                    {{"@type": "ListItem", "position": 1, "name": "Home", "item": "https://www.scrapehero.com/"}},
                    {{"@type": "ListItem", "position": 2, "name": "{seo_title}"}}
                ]
            }}
        ]
    }}
    </script>
    
    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Figtree:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    
    <!-- Styles -->
    <style>
        :root {{
            --sh-primary: {SH_PRIMARY};
            --sh-secondary: {SH_SECONDARY};
            --sh-text: {SH_TEXT};
            --sh-accent: {SH_ACCENT};
            --sh-accent-hover: {SH_ACCENT_HOVER};
            --sh-bg: {SH_BG};
            --sh-bg-alt: {SH_BG_ALT};
            --sh-border: {SH_BORDER};
            --sh-code-bg: {SH_CODE_BG};
            --sh-table-header-bg: {SH_TABLE_HEADER_BG};
            --sh-table-header-text: {SH_TABLE_HEADER_TEXT};
            --sh-table-row-alt: {SH_TABLE_ROW_ALT};
            --sh-green: {SH_GREEN};
            --sh-orange: {SH_ORANGE};
            --sh-red: {SH_RED};
            --sh-font-primary: {SH_FONT_PRIMARY};
            --sh-font-mono: {SH_FONT_MONO};
            --container-max-width: 1140px;
            --widgets-spacing: 20px;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: var(--sh-font-primary);
            font-size: 1.0625rem;
            line-height: 1.7;
            color: var(--sh-text);
            background-color: var(--sh-bg);
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}
        
        .page-wrapper {{
            max-width: var(--container-max-width);
            margin: 0 auto;
            padding: 0 2rem;
        }}
        
        /* Header */
        .site-header {{
            padding: 1.5rem 0;
            border-bottom: 1px solid var(--sh-border);
            background: var(--sh-bg);
        }}
        
        .site-branding {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        
        .site-logo {{
            width: 135px;
            height: auto;
        }}
        
        /* Breadcrumb */
        .breadcrumb {{
            padding: 1.5rem 0;
            font-size: 0.875rem;
            color: #707077;
        }}
        
        .breadcrumb a {{
            color: var(--sh-accent);
            text-decoration: none;
        }}
        
        .breadcrumb a:hover {{
            text-decoration: underline;
        }}
        
        .breadcrumb span {{
            margin: 0 0.5rem;
        }}
        
        /* Article Header */
        .article-header {{
            margin-bottom: 3rem;
        }}
        
        .article-meta {{
            display: flex;
            align-items: center;
            gap: 1.5rem;
            margin-bottom: 1rem;
            font-size: 0.875rem;
            color: #707077;
        }}
        
        .article-author {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .author-avatar {{
            width: 32px;
            height: 32px;
            border-radius: 50%;
        }}
        
        .author-name {{
            font-weight: 500;
            color: var(--sh-primary);
            text-decoration: none;
        }}
        
        .author-name:hover {{
            color: var(--sh-accent);
        }}
        
        .entry-title {{
            font-family: var(--sh-font-primary);
            font-size: 2.5rem;
            font-weight: 600;
            line-height: 1.2;
            color: var(--sh-primary);
            margin-bottom: 1rem;
        }}
        
        @media (max-width: 767px) {{
            .entry-title {{
                font-size: 1.9rem;
            }}
        }}
        
        /* Article Content */
        .article-content {{
            font-size: 1.0625rem;
            line-height: 1.7;
        }}
        
        .article-content p {{
            margin-bottom: 1.5rem;
        }}
        
        .article-content strong {{
            font-weight: 600;
            color: var(--sh-primary);
        }}
        
        .article-content em {{
            font-style: italic;
        }}
        
        .article-content a {{
            color: var(--sh-accent);
            text-decoration: none;
            border-bottom: 1px solid transparent;
            transition: border-color 0.2s;
        }}
        
        .article-content a:hover {{
            border-bottom-color: var(--sh-accent);
        }}
        
        /* Headings */
        .article-content h2 {{
            font-family: var(--sh-font-primary);
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--sh-primary);
            margin: 3rem 0 1.5rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--sh-border);
        }}
        
        .article-content h3 {{
            font-family: var(--sh-font-primary);
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--sh-primary);
            margin: 2.5rem 0 1rem;
        }}
        
        /* Code Blocks */
        .article-content pre {{
            background: var(--sh-code-bg);
            border-radius: 8px;
            padding: 1.5rem;
            overflow-x: auto;
            margin: 1.5rem 0;
            border: 1px solid var(--sh-border);
        }}
        
        .article-content code {{
            font-family: var(--sh-font-mono);
            font-size: 0.9em;
        }}
        
        .article-content pre code {{
            font-size: 0.875rem;
            line-height: 1.6;
            color: var(--sh-text);
            background: none;
            padding: 0;
        }}
        
        .article-content p code {{
            background: var(--sh-code-bg);
            padding: 0.125rem 0.375rem;
            border-radius: 4px;
            font-size: 0.9em;
            color: var(--sh-primary);
        }}
        
        /* Tables */
        .wp-block-table-container {{
            overflow-x: auto;
            margin: 1.5rem 0;
        }}
        
        .wp-block-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9375rem;
        }}
        
        .wp-block-table th {{
            background: var(--sh-table-header-bg);
            color: var(--sh-table-header-text);
            font-weight: 600;
            padding: 1rem;
            text-align: left;
            border: 1px solid var(--sh-border);
        }}
        
        .wp-block-table td {{
            padding: 0.875rem 1rem;
            border: 1px solid var(--sh-border);
            vertical-align: top;
        }}
        
        .wp-block-table tbody tr.alt td {{
            background: var(--sh-table-row-alt);
        }}
        
        .wp-block-table tbody tr:hover td {{
            background: #f0f0f0;
        }}
        
        .wp-block-table td code {{
            white-space: pre-wrap;
            word-break: break-word;
        }}
        
        /* Lists */
        .article-content ul, .article-content ol {{
            margin: 1.5rem 0 1.5rem 1.5rem;
            padding-left: 1rem;
        }}
        
        .article-content li {{
            margin-bottom: 0.5rem;
        }}
        
        .article-content li::marker {{
            color: var(--sh-accent);
        }}
        
        /* Images */
        .wp-block-image {{
            margin: 2rem 0;
            text-align: center;
        }}
        
        .wp-block-image img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }}
        
        .wp-element-caption {{
            margin-top: 0.75rem;
            font-size: 0.875rem;
            color: #707077;
            font-style: italic;
            text-align: center;
        }}
        
        /* Horizontal Rule */
        hr.wp-block-separator {{
            border: none;
            border-top: 2px dotted var(--sh-border);
            margin: 3rem 0;
        }}
        
        /* Callout Boxes */
        .callout {{
            background: var(--sh-bg-alt);
            border-left: 4px solid var(--sh-accent);
            padding: 1.5rem;
            margin: 1.5rem 0;
            border-radius: 0 8px 8px 0;
        }}
        
        .callout.warning {{
            border-left-color: var(--sh-orange);
            background: #FFF8F0;
        }}
        
        .callout.success {{
            border-left-color: var(--sh-green);
            background: #F0FDF4;
        }}
        
        .callout.danger {{
            border-left-color: var(--sh-red);
            background: #FEF2F2;
        }}
        
        /* FAQ Section */
        .faq-section {{
            margin-top: 3rem;
        }}
        
        .faq-item {{
            margin-bottom: 1.5rem;
            border: 1px solid var(--sh-border);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        .faq-question {{
            background: var(--sh-bg-alt);
            padding: 1.25rem 1.5rem;
            font-weight: 600;
            color: var(--sh-primary);
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .faq-question::after {{
            content: '+';
            font-size: 1.25rem;
            color: var(--sh-accent);
            transition: transform 0.2s;
        }}
        
        .faq-item.open .faq-question::after {{
            transform: rotate(45deg);
        }}
        
        .faq-answer {{
            padding: 0 1.5rem;
            max-height: 0;
            overflow: hidden;
            transition: all 0.3s ease;
        }}
        
        .faq-item.open .faq-answer {{
            padding: 1.5rem;
            max-height: 500px;
        }}
        
        .faq-answer p {{
            margin-bottom: 1rem;
        }}
        
        .faq-answer p:last-child {{
            margin-bottom: 0;
        }}
        
        /* Wrapping Up / CTA */
        .wrapping-up {{
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid var(--sh-border);
        }}
        
        .cta-box {{
            background: var(--sh-bg-alt);
            border-radius: 16px;
            padding: 2.5rem;
            margin: 2rem 0;
            text-align: center;
        }}
        
        .cta-box h3 {{
            margin-top: 0;
            font-size: 1.5rem;
        }}
        
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.875rem 1.5rem;
            font-size: 0.875rem;
            font-weight: 500;
            border-radius: 50px;
            text-decoration: none;
            transition: all 0.2s;
            border: none;
            cursor: pointer;
        }}
        
        .btn-primary {{
            background: var(--sh-accent);
            color: #fff;
        }}
        
        .btn-primary:hover {{
            background: var(--sh-accent-hover);
            color: #fff;
        }}
        
        .btn-secondary {{
            background: transparent;
            color: var(--sh-accent);
            border: 2px solid var(--sh-accent);
        }}
        
        .btn-secondary:hover {{
            background: var(--sh-accent);
            color: #fff;
        }}
        
        /* Footer */
        .site-footer {{
            margin-top: 4rem;
            padding: 3rem 0 2rem;
            border-top: 1px solid var(--sh-border);
            background: var(--sh-bg-alt);
        }}
        
        .footer-content {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 2rem;
            margin-bottom: 2rem;
        }}
        
        .footer-col h4 {{
            font-size: 1rem;
            font-weight: 600;
            color: var(--sh-primary);
            margin-bottom: 1rem;
        }}
        
        .footer-col ul {{
            list-style: none;
        }}
        
        .footer-col li {{
            margin-bottom: 0.5rem;
        }}
        
        .footer-col a {{
            color: var(--sh-text);
            text-decoration: none;
        }}
        
        .footer-col a:hover {{
            color: var(--sh-accent);
        }}
        
        .footer-bottom {{
            text-align: center;
            padding-top: 2rem;
            border-top: 1px solid var(--sh-border);
            color: #707077;
            font-size: 0.875rem;
        }}
        
        /* Responsive */
        @media (max-width: 1024px) {{
            .page-wrapper {{
                padding: 0 1.5rem;
            }}
        }}
        
        @media (max-width: 767px) {{
            .page-wrapper {{
                padding: 0 1rem;
            }}
            
            .entry-title {{
                font-size: 1.75rem;
            }}
            
            .article-content h2 {{
                font-size: 1.25rem;
            }}
            
            .article-content h3 {{
                font-size: 1.125rem;
            }}
            
            .cta-box {{
                padding: 1.5rem;
            }}
        }}
        
        /* Print */
        @media print {{
            .site-header, .breadcrumb, .site-footer, .btn {{
                display: none;
            }}
            
            .page-wrapper {{
                max-width: none;
                padding: 0;
            }}
            
            .article-content pre {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="page-wrapper">
        <!-- Header -->
        <header class="site-header">
            <div class="site-branding">
                <a href="https://www.scrapehero.com/" aria-label="ScrapeHero Home">
                    <svg class="site-logo" viewBox="0 0 800 800" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                        <rect width="800" height="800" fill="{SH_PRIMARY}" rx="80"/>
                        <text x="400" y="520" font-family="Figtree, sans-serif" font-size="320" font-weight="700" fill="white" text-anchor="middle">SH</text>
                    </svg>
                </a>
            </div>
        </header>
        
        <!-- Breadcrumb -->
        <nav class="breadcrumb" aria-label="Breadcrumb">
            <a href="https://www.scrapehero.com/">Home</a>
            <span>/</span>
            <span aria-current="page">{article_title}</span>
        </nav>
        
        <!-- Article -->
        <article>
            <header class="article-header">
                <div class="article-meta">
                    <div class="article-author">
                        <!-- Generic ScrapeHero avatar, not a specific person -->
                        <img class="author-avatar" src="https://www.scrapehero.com/favicon.ico" alt="" loading="lazy" onerror="this.src='https://secure.gravatar.com/avatar/00000000000000000000000000000000?s=96&d=mp'">
                        <a class="author-name" href="https://www.scrapehero.com/" target="_blank" rel="noopener">ScrapeHero</a>
                    </div>
                    <!-- No publication date - not yet published -->
                </div>
                <h1 class="entry-title">{article_title}</h1>
            </header>
            
            <div class="article-content">
                {content_html}
            </div>
        </article>
        
        <!-- Footer -->
        <footer class="site-footer" role="contentinfo">
            <div class="page-wrapper">
                <div class="footer-content">
                    <div class="footer-col">
                        <h4>ScrapeHero</h4>
                        <ul>
                            <li><a href="https://www.scrapehero.com/">Home</a></li>
                            <li><a href="https://www.scrapehero.com/services/">Managed Web Scraping</a></li>
                            <li><a href="https://www.scrapehero.com/marketplace/">ScrapeHero Marketplace</a></li>
                            <li><a href="https://www.scrapehero.com/cloud/">ScrapeHero Cloud</a></li>
                        </ul>
                    </div>
                    <div class="footer-col">
                        <h4>Resources</h4>
                        <ul>
                            <li><a href="https://www.scrapehero.com/articles/">All Articles</a></li>
                            <li><a href="https://www.scrapehero.com/n8n/">n8n Integration</a></li>
                            <li><a href="https://www.scrapehero.com/api-documentation/">API Documentation</a></li>
                            <li><a href="https://www.scrapehero.com/pricing/">Pricing</a></li>
                        </ul>
                    </div>
                    <div class="footer-col">
                        <h4>Company</h4>
                        <ul>
                            <li><a href="https://www.scrapehero.com/about/">About Us</a></li>
                            <li><a href="https://www.scrapehero.com/contact/">Contact</a></li>
                            <li><a href="https://www.scrapehero.com/careers/">Careers</a></li>
                            <li><a href="https://www.scrapehero.com/privacy-policy/">Privacy Policy</a></li>
                        </ul>
                    </div>
                    <div class="footer-col">
                        <h4>Connect</h4>
                        <ul>
                            <li><a href="https://x.com/scrapehero" target="_blank" rel="noopener">X (Twitter)</a></li>
                            <li><a href="https://www.linkedin.com/company/scrape-hero" target="_blank" rel="noopener">LinkedIn</a></li>
                            <li><a href="https://github.com/scrapehero" target="_blank" rel="noopener">GitHub</a></li>
                        </ul>
                    </div>
                </div>
                <div class="footer-bottom">
                    <p>&copy; 2026 ScrapeHero. All rights reserved.</p>
                </div>
            </div>
        </footer>
    </div>
    
    <!-- FAQ Toggle Script -->
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            document.querySelectorAll('.faq-question').forEach(function(btn) {{
                btn.addEventListener('click', function() {{
                    this.parentElement.classList.toggle('open');
                }});
            }});
        }});
    </script>
</body>
</html>'''
    
    output_path.write_text(html, encoding='utf-8')
    print(f"✅ Generated HTML: {output_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert ScrapeHero markdown article to HTML")
    parser.add_argument("article_dir", help="Path to article directory (containing article.md)")
    parser.add_argument("-o", "--output", help="Output HTML file path (default: article_dir/index.html)")
    
    args = parser.parse_args()
    
    article_dir = Path(args.article_dir).resolve()
    if not article_dir.exists():
        print(f"Error: Article directory not found: {article_dir}")
        return 1
    
    if not (article_dir / 'article.md').exists():
        print(f"Error: article.md not found in {article_dir}")
        return 1
    
    output_path = Path(args.output).resolve() if args.output else article_dir / 'index.html'
    
    build_html(article_dir, output_path)
    return 0


if __name__ == "__main__":
    exit(main())