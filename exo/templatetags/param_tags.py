from django import template
from django.utils.safestring import mark_safe
from wagtail.images import get_image_model
import re

register = template.Library()

_param_pattern = re.compile(r"\[\[\s*([A-Za-z_][A-Za-z0-9_]*)\s*\]\]")
_slot_pattern = re.compile(r"\[\[\s*slot:([A-Za-z_][A-Za-z0-9_]*)\s*\]\](.*?)\[\[\s*/\s*slot\s*\]\]", re.DOTALL)
_image_pattern = re.compile(r"\[\[\s*image:([A-Za-z_][A-Za-z0-9_]*)\s*\]\]")
_tableau_pattern = re.compile(r"\[\[\s*tableau:([A-Za-z_][A-Za-z0-9_]*)(?:\|([^]]*))?\s*\]\]")


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
    
    # DEBUG: Vérifier les paramètres
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"DEBUG render_with_params: param_values = {param_values}")
    logger.info(f"DEBUG render_with_params: HTML avant = {html[:200]}...")
    
    # Si c'est une chaîne simple (pas un bloc), traiter directement
    if isinstance(block, str):
        html = block

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

    # Remplacer les tableaux [[tableau:name|options]]
    def tableau_repl(match):
        name = match.group(1)
        options_str = match.group(2) or ""
        param_value = param_values.get(name)

        # DEBUG: Log pour diagnostiquer le problème
        logger.info(f"DEBUG tableau_repl: name={name}, param_value={param_value}")
        logger.info(f"DEBUG tableau_repl: param_value type={type(param_value)}")
        logger.info(f"DEBUG tableau_repl: param_values keys={list(param_values.keys())}")

        if param_value is None:
            # Essayer de récupérer le paramètre depuis la base de données
            try:
                from exo.models import ParamItem
                param_item = ParamItem.objects.filter(name=name).first()
                if param_item and param_item.kind == 'tableau':
                    param_value = {
                        'orientation': param_item.tableau_orientation,
                        'header': param_item.tableau_header,
                        'rows': param_item.tableau_rows.split('\n') if param_item.tableau_rows else []
                    }
                    logger.info(f"DEBUG tableau_repl: Paramètre récupéré depuis la DB: {param_value}")
                else:
                    return f'<div class="text-red-600">Paramètre tableau "{name}" non trouvé</div>'
            except Exception as e:
                logger.error(f"Erreur récupération paramètre {name}: {e}")
                return f'<div class="text-red-600">Erreur paramètre tableau "{name}": {str(e)}</div>'

        # Parser les options (format: view=eleve|orientation=h|n=3)
        options = {}
        if options_str:
            for option in options_str.split('|'):
                if '=' in option:
                    key, value = option.split('=', 1)
                    options[key.strip()] = value.strip()

        # Valeurs par défaut
        view = options.get('view', 'eleve')
        orientation = options.get('orientation', param_value.get('orientation', 'h'))
        n = int(options.get('n', '3'))

        import secrets, hashlib

        # Seed partagé pour TOUT le rendu (stable énoncé/corrigé), différent à chaque refresh
        base_seed = context.get('K', 1)
        render_seed = context.get('__render_seed')
        if render_seed is None:
            render_seed = secrets.randbits(32)
            context['__render_seed'] = render_seed

        # Cache local (par rendu) pour stabiliser un param précis sur toute la page
        cache = context.get('__table_seed_cache')
        if cache is None:
            cache = {}
            context['__table_seed_cache'] = cache

        # Option manuelle : [[tableau:...|seed=12345]]
        opt_seed = options.get('seed')
        if opt_seed is not None:
            unique_seed = int(opt_seed)
        else:
            if name not in cache:
                seed_string = f"{render_seed}_{name}"
                cache[name] = int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)
            unique_seed = cache[name]

        # Importer et utiliser notre template tag
        try:
            # Créer un contexte avec les paramètres nécessaires
            from django.template import Context
            
            # Construire le contexte exo_params attendu par render_param_table
            # param_value devrait être un dictionnaire {'orientation': 'h', 'header': '...', 'rows': [...]}
            if isinstance(param_value, dict) and 'orientation' in param_value:
                # C'est un paramètre tableau au bon format
                exo_params = {name: param_value}
            else:
                # Fallback: essayer de récupérer depuis la DB
                exo_params = {name: param_value}
            
            temp_context = Context({
                'exo_params': exo_params,
                'K': base_seed
            })
            from exo.templatetags.exo_tables import render_param_table
            logger.info(f"DEBUG tableau_repl: Appel render_param_table avec exo_params={exo_params}")
            result = render_param_table(temp_context, name, view, orientation, n, unique_seed)
            logger.info(f"DEBUG tableau_repl: Résultat render_param_table={str(result)[:200]}...")
            return str(result)
        except Exception as e:
            return f'<div class="text-red-600">Erreur rendu tableau "{name}": {str(e)}</div>'

    html = _tableau_pattern.sub(tableau_repl, html)

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
    logger.info(f"DEBUG render_with_params: HTML après = {rendered[:200]}...")
    return mark_safe(rendered)



