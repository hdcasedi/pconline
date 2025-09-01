from django import template
from django.utils.safestring import mark_safe
from wagtail.images import get_image_model
import re

register = template.Library()

_param_pattern = re.compile(r"\[\[\s*([A-Za-z_][A-Za-z0-9_]*)\s*\]\]")
_slot_pattern = re.compile(r"\[\[\s*slot:([A-Za-z_][A-Za-z0-9_]*)\s*\]\](.*?)\[\[\s*/\s*slot\s*\]\]", re.DOTALL)
_image_pattern = re.compile(r"\[\[\s*image:([A-Za-z_][A-Za-z0-9_]*)\s*\]\]")


def _replace_placeholders(html: str, param_values: dict) -> str:
    if not html:
        return html

    def repl(match):
        name = match.group(1)
        value = param_values.get(name)
        if value is None:
            return match.group(0)  # laisse tel quel si non défini
        return str(value)

    return _param_pattern.sub(repl, html)


def _inline_slot_html(html: str) -> str:
    """Sanitize slot HTML to avoid forcing new lines.
    - Remove outer <p> wrappers
    - Replace <p>, </p>, <div>, </div>, <br> with spaces
    - Collapse whitespace
    """
    if not html:
        return ''
    s = html.strip()
    # Remove single outer <p>...</p>
    m = re.match(r"^<p[^>]*>([\s\S]*?)</p>$", s, flags=re.IGNORECASE)
    if m:
        s = m.group(1)
    # Replace block tags with spaces
    s = re.sub(r"</?p[^>]*>", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"</?div[^>]*>", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.IGNORECASE)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)
    return s.strip()


@register.simple_tag(takes_context=True)
def render_with_params(context, block, param_values=None):
    """Rend un bloc StreamField et applique le remplacement [[name]] avec param_values."""
    try:
        # Rendre le bloc avec le contexte actuel (Wagtail BoundBlock possède render)
        html = block.render(context)
    except Exception:
        try:
            # Fallback : tenter un rendu simple
            html = str(block)
        except Exception:
            html = ""

    if param_values is None:
        param_values = context.get('param_values', {}) or {}

    # Remplacer d'abord les slots [[slot:name]]...[[/slot]] si une valeur HTML est fournie
    def slot_repl(match):
        name = match.group(1)
        default_html = match.group(2)
        value = param_values.get(name)
        # Slot sans variantes (K=0): insérer vide (aucun retour à la ligne superflu)
        if value is None:
            return ''
        # Sinon insérer la variante fournie (HTML déjà prêt)
        return _inline_slot_html(str(value))

    html = _slot_pattern.sub(slot_repl, html)

    # Remplacer ensuite les images [[image:name]] par <img ...>
    Image = get_image_model()
    def image_repl(m):
        name = m.group(1)
        val = param_values.get(name)
        try:
            if val:
                img = Image.objects.filter(id=val).first()
                if img:
                    url = img.file.url
                    return f'<img src="{url}" alt="{name}" style="max-width:100%;height:auto;vertical-align:middle;" />'
        except Exception:
            pass
        # Si rien trouvé: insérer vide (pas de saut de ligne)
        return ''
    html = _image_pattern.sub(image_repl, html)
    # Nettoyage: retirer des paragraphes isolés "image" ou "caption" autour
    html = re.sub(r"(?i)<p[^>]*>\s*(image|caption)\s*</p>", "", html)
    # Supprimer les tokens 'image' ou 'caption' collés au tag <img>
    # ... 'image' juste avant l'img
    html = re.sub(r"(?i)\bimage\b\s*(<img[^>]*>)", r"\1", html)
    # ... 'caption' juste après l'img
    html = re.sub(r"(?i)(<img[^>]*>)\s*\bcaption\b", r"\1", html)
    # ... gérer 'image:' ou 'caption:'
    html = re.sub(r"(?i)\bimage\s*:\s*(<img[^>]*>)", r"\1", html)
    html = re.sub(r"(?i)(<img[^>]*>)\s*:\s*\bcaption\b", r"\1", html)
    # Nettoyage des listes de définitions (dl/dt/dd) générées par certains rendus
    # Retirer les balises <dt>image</dt> / <dt>caption</dt>
    html = re.sub(r"(?is)<dt[^>]*>\s*image\s*</dt>\s*", "", html)
    html = re.sub(r"(?is)<dt[^>]*>\s*caption\s*</dt>\s*", "", html)
    # Retirer les <dd> qui ne contiennent pas d'image (souvent le nom du fichier)
    html = re.sub(r"(?is)<dd[^>]*>(?!.*<img)(.*?)</dd>", "", html)
    # Si un <dd> contient un <img>, ne garder que l'<img>
    html = re.sub(r"(?is)<dd[^>]*>.*?(<img[^>]*>).*?</dd>", r"\1", html)
    # Nettoyer d'éventuels <dl> vides
    html = re.sub(r"(?is)<dl[^>]*>\s*</dl>", "", html)

    # Puis remplacer les [[name]] restants
    rendered = _replace_placeholders(html, param_values)
    return mark_safe(rendered)


