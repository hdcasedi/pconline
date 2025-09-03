# -*- coding: utf-8 -*-
from django import template
from exo.models import ExoPageSimple, ExoHubPage

register = template.Library()

@register.filter(name="get_item")
def get_item(dictionary, key):
    """Récupère un élément d'un dictionnaire par sa clé"""
    if dictionary is None:
        return None
    
    # Vérifier que dictionary est bien un dictionnaire
    if not isinstance(dictionary, dict):
        return None
    
    # Convertir la clé en entier si c'est une chaîne numérique
    try:
        if isinstance(key, str) and key.isdigit():
            key = int(key)
    except (ValueError, TypeError):
        pass
    
    return dictionary.get(key)

import random

@register.simple_tag(takes_context=True)
def get_exercices_by_level(context, page):
    """
    Template tag pour récupérer un exercice au hasard par niveau avec variante aléatoire
    """
    exercices_by_level = {1: None, 2: None, 3: None}
    
    # Récupérer tous les hubs d'exercices enfants de cette page de cours
    exo_hubs = page.get_children().type(ExoHubPage).specific()
    
    # Grouper les exercices par niveau
    all_exercices_by_level = {1: [], 2: [], 3: []}
    
    for hub in exo_hubs:
        # Récupérer tous les exercices de ce hub
        exercices = hub.get_children().type(ExoPageSimple).specific()
        for exo in exercices:
            level = exo.difficulty
            if level in all_exercices_by_level:
                all_exercices_by_level[level].append(exo)
    
    # Sélectionner un exercice au hasard par niveau
    for level in [1, 2, 3]:
        exercices = all_exercices_by_level[level]
        if exercices:
            # Sélectionner un exercice au hasard
            exercices_by_level[level] = random.choice(exercices)
    
    return exercices_by_level

@register.simple_tag(takes_context=True)
def get_exercice_context(context, exo):
    """
    Génère le contexte pour un exercice avec paramètres aléatoires
    """
    if not exo:
        return {}
    
    # Générer un seed aléatoire pour les paramètres
    seed = random.randint(1, 10000)
    
    # Récupérer les vrais paramètres depuis ParametreExoPage
    from exo.models import ParametreExoPage
    
    try:
        # Chercher la page de paramètres associée à cet exercice
        params_page = exo.get_children().type(ParametreExoPage).specific().first()
        
        if params_page:
            # Utiliser la méthode build_random_context de la page de paramètres
            param_values = params_page.build_random_context(seed=seed)
        else:
            # Fallback: paramètres par défaut
            random.seed(seed)
            param_values = {}
            param_values['a'] = random.randint(10, 100)
            param_values['b'] = random.randint(200, 500)
            param_values['c'] = random.randint(1, 50)
            param_values['d'] = random.randint(100, 1000)
    except Exception as e:
        print(f"Erreur lors de la récupération des paramètres pour l'exercice {exo.id}: {e}")
        # Fallback: paramètres par défaut
        random.seed(seed)
        param_values = {}
        param_values['a'] = random.randint(10, 100)
        param_values['b'] = random.randint(200, 500)
        param_values['c'] = random.randint(1, 50)
        param_values['d'] = random.randint(100, 1000)
    
    # Retourner le contexte complet
    return {
        'page': exo,
        'param_values': param_values,
        'points_sum': exo.get_points_sum(),
        'has_fc': exo.has_fc(),
    }

@register.simple_tag(takes_context=True)
def render_exercice_block(context, block, param_values):
    """
    Rend un bloc d'exercice avec remplacement des paramètres [[name]], [[slot:name]] et [[image:name]]
    """
    from django.utils.safestring import mark_safe
    from wagtail.images import get_image_model
    import re
    
    # Rendre le bloc
    try:
        html = block.render(context)
    except Exception:
        try:
            html = str(block)
        except Exception:
            html = ""
    
    if not param_values:
        return mark_safe(html)
    
    # Patterns pour les différents types de remplacements
    param_pattern = re.compile(r"\[\[\s*([A-Za-z_][A-Za-z0-9_]*)\s*\]\]")
    slot_pattern = re.compile(r"\[\[\s*slot:([A-Za-z_][A-Za-z0-9_]*)\s*\]\](.*?)\[\[\s*/\s*slot\s*\]\]", re.DOTALL)
    image_pattern = re.compile(r"\[\[\s*image:([A-Za-z_][A-Za-z0-9_]*)\s*\]\]")
    
    def _inline_slot_html(html_str):
        """Sanitize slot HTML to avoid forcing new lines."""
        if not html_str:
            return ''
        s = html_str.strip()
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
    
    # 1. Remplacer d'abord les slots [[slot:name]]...[[/slot]]
    def slot_repl(match):
        name = match.group(1)
        default_html = match.group(2)
        value = param_values.get(name)
        # Slot sans variantes: insérer vide
        if value is None:
            return ''
        # Sinon insérer la variante fournie
        return _inline_slot_html(str(value))
    
    html = slot_pattern.sub(slot_repl, html)
    
    # 2. Remplacer les images [[image:name]]
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
        # Si rien trouvé: insérer vide
        return ''
    
    html = image_pattern.sub(image_repl, html)
    
    # Nettoyage des images
    html = re.sub(r"(?i)<p[^>]*>\s*(image|caption)\s*</p>", "", html)
    html = re.sub(r"(?i)\bimage\b\s*(<img[^>]*>)", r"\1", html)
    html = re.sub(r"(?i)(<img[^>]*>)\s*\bcaption\b", r"\1", html)
    html = re.sub(r"(?i)\bimage\s*:\s*(<img[^>]*>)", r"\1", html)
    html = re.sub(r"(?i)(<img[^>]*>)\s*:\s*\bcaption\b", r"\1", html)
    html = re.sub(r"(?is)<dt[^>]*>\s*image\s*</dt>\s*", "", html)
    html = re.sub(r"(?is)<dt[^>]*>\s*caption\s*</dt>\s*", "", html)
    html = re.sub(r"(?is)<dd[^>]*>(?!.*<img)(.*?)</dd>", "", html)
    html = re.sub(r"(?is)<dd[^>]*>.*?(<img[^>]*>).*?</dd>", r"\1", html)
    html = re.sub(r"(?is)<dl[^>]*>\s*</dl>", "", html)
    
    # 3. Remplacer les [[name]] restants
    def param_repl(match):
        name = match.group(1)
        value = param_values.get(name)
        if value is None:
            return match.group(0)  # laisse tel quel si non défini
        return str(value)
    
    rendered = param_pattern.sub(param_repl, html)
    return mark_safe(rendered)

@register.simple_tag(takes_context=True)
def get_random_variant_url(context, exo):
    """
    Génère une URL avec une variante aléatoire pour un exercice
    """
    if not exo:
        return ""
    
    # Générer un seed aléatoire pour la variante
    seed = random.randint(1, 10000)
    return f"{exo.url}?seed={seed}"
