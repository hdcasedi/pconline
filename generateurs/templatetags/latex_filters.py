# -*- coding: utf-8 -*-
from django import template
import re

register = template.Library()

LATEX_REPL = [
    (r'\\', r'\\textbackslash '),
    (r'([{}$&#_%])', r'\\\1'),          # { } $ & # _ %
    (r'~', r'\\textasciitilde '),
    (r'\^', r'\\textasciicircum '),
]

@register.filter(name="trim")
def trim(value):
    return "" if value is None else str(value).strip()

@register.filter(name="texescape")
def texescape(value):
    s = "" if value is None else str(value)
    for pat, repl in LATEX_REPL:
        s = re.sub(pat, repl, s)
    return s

@register.filter(name="richtext_to_latex")
def richtext_to_latex(value):
    """Convertit du RichText HTML en LaTeX propre"""
    if value is None:
        return ""
    
    # Convertir en string si c'est du RichText
    s = str(value)
    
    # Supprimer les attributs data-block-key
    s = re.sub(r'data-block-key="[^"]*"', '', s)
    
    # Convertir les balises HTML en LaTeX
    replacements = [
        (r'<p[^>]*>', ''),  # Supprimer <p>
        (r'</p>', '\n\n'),  # Remplacer </p> par double saut de ligne
        (r'<ul[^>]*>', '\n\\begin{itemize}\n'),  # Liste à puces
        (r'</ul>', '\n\\end{itemize}\n'),
        (r'<ol[^>]*>', '\n\\begin{enumerate}\n'),  # Liste numérotée
        (r'</ol>', '\n\\end{enumerate}\n'),
        (r'<li[^>]*>', '\n\\item '),  # Élément de liste
        (r'</li>', ''),
        (r'<strong[^>]*>', '\\textbf{'),  # Gras
        (r'</strong>', '}'),
        (r'<b[^>]*>', '\\textbf{'),  # Gras
        (r'</b>', '}'),
        (r'<em[^>]*>', '\\textit{'),  # Italique
        (r'</em>', '}'),
        (r'<i[^>]*>', '\\textit{'),  # Italique
        (r'</i>', '}'),
        (r'<br[^>]*>', '\n'),  # Saut de ligne
        (r'<hr[^>]*>', '\n\\hrule\n'),  # Ligne horizontale
        (r'<h1[^>]*>', '\n\\section{'),  # Titres
        (r'</h1>', '}\n'),
        (r'<h2[^>]*>', '\n\\subsection{'),
        (r'</h2>', '}\n'),
        (r'<h3[^>]*>', '\n\\subsubsection{'),
        (r'</h3>', '}\n'),
    ]
    
    for pattern, replacement in replacements:
        s = re.sub(pattern, replacement, s)
    
    # Supprimer les autres balises HTML restantes
    s = re.sub(r'<[^>]*>', '', s)
    
    # Nettoyer les espaces multiples
    s = re.sub(r'\n\s*\n\s*\n', '\n\n', s)
    s = s.strip()
    
    # Échapper les caractères LaTeX spéciaux
    return texescape(s)


