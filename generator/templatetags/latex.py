from django import template
from django.utils.safestring import mark_safe
from django.conf import settings
import os
import html as _html
import re

register = template.Library()

# --- HTML table -> LaTeX tabular ---
def _esc_tex_inline(s: str) -> str:
    """Échapper les caractères LaTeX (sauf l'esperluette gérée à part)"""
    for a, b in [
        ("#", r"\#"), ("$", r"\$"), ("%", r"\%"),
        ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
        ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"),
    ]:
        s = s.replace(a, b)
    return s

def _html_table_to_tabular(html: str) -> str:
    """Convertit une table HTML en LaTeX tabular"""
    import re, html as _html
    rows_html = re.findall(r'(?is)<tr[^>]*>(.*?)</tr>', html)
    rows, maxcols = [], 0
    for row_html in rows_html:
        cells_th = re.findall(r'(?is)<th[^>]*>(.*?)</th>', row_html)
        cells_td = re.findall(r'(?is)<td[^>]*>(.*?)</td>', row_html)
        is_header = bool(cells_th)
        cells = cells_th if cells_th else cells_td
        cleaned = []
        for c in cells:
            txt = re.sub(r'(?is)<[^>]+>', '', c)
            txt = _html.unescape(txt).strip()
            txt = txt.replace('&', r'\&')
            txt = _esc_tex_inline(txt)
            if is_header:
                txt = r'\textbf{' + txt + '}'
            cleaned.append(txt)
        rows.append((cleaned, is_header))
        maxcols = max(maxcols, len(cleaned))
    if maxcols == 0:
        return ""
    spec = '|' + '|'.join(['l'] * maxcols) + '|'
    out = [r'\begin{tabular}{' + spec + r'}', r'\hline']
    for cells, _ in rows:
        cells = cells + [''] * (maxcols - len(cells))
        out.append(' ' + ' & '.join(cells) + r' \\ \hline')
    out.append(r'\end{tabular}')
    return '\n'.join(out)

# --- Helpers légers ---
def _repair_mojibake(s: str) -> str:
    if not s:
        return s
    if 'Ã' in s or 'Â' in s or 'â' in s:
        try:
            return s.encode('latin-1', 'ignore').decode('utf-8', 'ignore')
        except Exception:
            return s
    return s


def _html_to_tex(value: str) -> str:
    if value is None:
        return ""
    s = str(value)
    s = _html.unescape(s)
    s = _repair_mojibake(s)

    # Pass-through <tex>...</tex> → __TEX__i__
    tex_placeholders = []
    def _extract_tex(m):
        idx = len(tex_placeholders)
        tex_placeholders.append(m.group(1))
        return f"__TEX__{idx}__"
    s = re.sub(r"(?is)<tex>([\s\S]*?)</tex>", _extract_tex, s)

    # Tables HTML → __TAB__i__ avec conversion immédiate
    table_placeholders = []
    def _stash_table(m):
        table_tex = _html_table_to_tabular(m.group(0))
        table_placeholders.append(table_tex)
        return f"__TAB__{len(table_placeholders)-1}__"
    s = re.sub(r"(?is)<table[^>]*>.*?</table>", _stash_table, s)

    # Isoler maths
    math_pattern = re.compile(r'(\$[^$]+\$|\\\([^()]+\\\)|\\\[[^\[\]]+\\\])')
    parts, last = [], 0
    for match in math_pattern.finditer(s):
        if match.start() > last:
            parts.append(('text', s[last:match.start()]))
        parts.append(('math', match.group(0)))
        last = match.end()
    if last < len(s):
        parts.append(('text', s[last:]))

    result = []
    image_placeholders = []
    for typ, content in parts:
        if typ == 'math':
            result.append(content)
            continue
        text = content
        # Protéger placeholders avant échappement
        if table_placeholders:
            text = re.sub(r"__TAB__([0-9]+)__", lambda m: f"[[TAB{m.group(1)}]]", text)
        if tex_placeholders:
            text = re.sub(r"__TEX__([0-9]+)__", lambda m: f"[[TEX{m.group(1)}]]", text)
        text = re.sub(r"(?i)<\s*br\s*/?\s*>", r"\\newline ", text)
        text = re.sub(r"<[^>]+>", "", text)
        for a, b in [("\\", r"\\textbackslash{}"), ("{", r"\\{"), ("}", r"\\}"), ("#", r"\\#"), ("%", r"\\%"), ("&", r"\\&"), ("_", r"\\_"), ("~", r"\\textasciitilde{}"), ("^", r"\\textasciicircum{}")]:
            text = text.replace(a, b)
        # filet de secours lambda
        text = text.replace("ÃŽÂ»", r"$\\lambda$").replace("Î»", r"$\\lambda$")
        # Restaurer <table> converties
        if table_placeholders:
            def _restore_tab(m):
                i = int(m.group(1))
                return table_placeholders[i] if 0 <= i < len(table_placeholders) else ''
            text = re.sub(r"\[\[TAB([0-9]+)\]\]", _restore_tab, text)
        # Restaurer <tex>
        if tex_placeholders:
            def _restore_tex(m):
                i = int(m.group(1))
                return tex_placeholders[i] if 0 <= i < len(tex_placeholders) else ''
            text = re.sub(r"\[\[TEX([0-9]+)\]\]", _restore_tex, text)
        result.append(text)

    return ''.join(result)


def _html_to_tex_no_images(value: str) -> str:
    if value is None:
        return ""
    s = str(value)
    s = _html.unescape(s)
    s = _repair_mojibake(s)

    # Pass-through <tex>...</tex> → __TEX__i__
    tex_placeholders = []
    def _extract_tex(m):
        idx = len(tex_placeholders)
        tex_placeholders.append(m.group(1))
        return f"__TEX__{idx}__"
    s = re.sub(r"(?is)<tex>([\s\S]*?)</tex>", _extract_tex, s)

    # Tables HTML → __TAB__i__ avec conversion immédiate
    table_placeholders = []
    def _stash_table(m):
        table_tex = _html_table_to_tabular(m.group(0))
        table_placeholders.append(table_tex)
        return f"__TAB__{len(table_placeholders)-1}__"
    s = re.sub(r"(?is)<table[^>]*>.*?</table>", _stash_table, s)

    math_pattern = re.compile(r'(\$[^$]+\$|\\\([^()]+\\\)|\\\[[^\[\]]+\\\])')
    parts, last = [], 0
    for match in math_pattern.finditer(s):
        if match.start() > last:
            parts.append(('text', s[last:match.start()]))
        parts.append(('math', match.group(0)))
        last = match.end()
    if last < len(s):
        parts.append(('text', s[last:]))

    result = []
    for typ, content in parts:
        if typ == 'math':
            result.append(content)
            continue
        text = content
        # Protéger placeholders avant échappement
        if table_placeholders:
            text = re.sub(r"__TAB__([0-9]+)__", lambda m: f"[[TAB{m.group(1)}]]", text)
        if tex_placeholders:
            text = re.sub(r"__TEX__([0-9]+)__", lambda m: f"[[TEX{m.group(1)}]]", text)
        text = re.sub(r"(?i)<\s*br\s*/?\s*>", r"\\newline ", text)
        text = re.sub(r"<[^>]+>", "", text)
        for a, b in [("\\", r"\\textbackslash{}"), ("{", r"\\{"), ("}", r"\\}"), ("#", r"\\#"), ("%", r"\\%"), ("&", r"\\&"), ("_", r"\\_"), ("~", r"\\textasciitilde{}"), ("^", r"\\textasciicircum{}")]:
            text = text.replace(a, b)
        text = text.replace("ÃŽÂ»", r"$\\lambda$").replace("Î»", r"$\\lambda$")
        # Restaurer <table> converties puis blocs TeX
        if table_placeholders:
            def _restore_tab(m):
                i = int(m.group(1))
                return table_placeholders[i] if 0 <= i < len(table_placeholders) else ''
            text = re.sub(r"\[\[TAB([0-9]+)\]\]", _restore_tab, text)
        if tex_placeholders:
            def _restore_tex(m):
                i = int(m.group(1))
                return tex_placeholders[i] if 0 <= i < len(tex_placeholders) else ''
            text = re.sub(r"\[\[TEX([0-9]+)\]\]", _restore_tex, text)
        result.append(text)

    return ''.join(result)

@register.filter(name="html2tex")
def html2tex_filter(value):
    return mark_safe(_html_to_tex(value))

@register.filter(name="html2tex_no_images")
def html2tex_no_images_filter(value):
    return mark_safe(_html_to_tex_no_images(value))

@register.filter(name="tex")
def tex_filter(value):
    return mark_safe(_html_to_tex(value))

@register.filter(name="tex_safe")
def tex_safe_filter(value):
    """Version stricte: pas de pass-through <tex>, tout est échappé."""
    if value is None:
        return mark_safe("")
    s = str(value)
    s = _html.unescape(s)
    s = re.sub(r"(?is)<[^>]+>", "", s)
    for a, b in [
        ("\\", r"\\textbackslash{}"),
        ("{", r"\\{"), ("}", r"\\}"),
        ("#", r"\\#"), ("%", r"\\%"), ("&", r"\\&"),
        ("_", r"\\_"), ("~", r"\\textasciitilde{}"), ("^", r"\\textasciicircum{}"),
        ("$", r"\\$"),
    ]:
        s = s.replace(a, b)
    return mark_safe(s)

@register.filter
def strip_badges(text):
    if not text:
        return ""
    s = str(text)
    s = re.sub(r'^\s*\(\s*\d+(?:[.,]\d+)?\s*pt\s*\)\s*', '', s, flags=re.I)
    s = re.sub(r'^\s*(FC|APP|ENT)\s*[:\-]?\s*', '', s, flags=re.I)
    return s
