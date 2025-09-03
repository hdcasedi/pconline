"""
Module pour construire le contexte de sélection à partir du payload JSON.
Réutilise les fonctions existantes des selectors.
"""
import json
from typing import Dict, Any, List
import random
import re
from django.template import Context
from django.utils.safestring import mark_safe
from .selectors import ContentSelector, generate_ds_content, generate_serie_content
from referentiel.models import Niveau, Chapitre
from cours.models import CoursPage
from exo.models import ExoPageSimple, ParametreExoPage
from wagtail.images import get_image_model


def _build_param_values_for_exo(exo: ExoPageSimple, seed: int | None) -> Dict[str, Any]:
    """Construit les paramètres d'un exercice via sa page ParametreExoPage si présente."""
    if seed is None:
        seed = random.randint(1, 10000)
    try:
        params_page = exo.get_children().type(ParametreExoPage).specific().first()
        if params_page:
            return params_page.build_random_context(seed=seed)
    except Exception:
        pass
    # Fallback simple
    random.seed(seed)
    return {
        'a': random.randint(10, 100),
        'b': random.randint(200, 500),
        'c': random.randint(1, 50),
        'd': random.randint(100, 1000),
    }


def _render_block_with_params(block, param_values: Dict[str, Any]) -> str:
    """Rend un bloc Wagtail et applique les remplacements [[param]], [[slot:name]], [[image:name]]."""
    try:
        html = block.render(Context({}))
    except Exception:
        try:
            html = str(block)
        except Exception:
            html = ""

    if not param_values:
        return html

    # Patterns
    param_pattern = re.compile(r"\[\[\s*([A-Za-z_][A-Za-z0-9_]*)\s*\]\]")
    slot_pattern = re.compile(r"\[\[\s*slot:([A-Za-z_][A-Za-z0-9_]*)\s*\]\](.*?)\[\[\s*/\s*slot\s*\]\]", re.DOTALL)
    image_pattern = re.compile(r"\[\[\s*image:([A-Za-z_][A-Za-z0-9_]*)\s*\]\]")

    def _inline_slot_html(html_str: str) -> str:
        if not html_str:
            return ''
        s = html_str.strip()
        m = re.match(r"^<p[^>]*>([\s\S]*?)</p>$", s, flags=re.IGNORECASE)
        if m:
            s = m.group(1)
        s = re.sub(r"</?p[^>]*>", " ", s, flags=re.IGNORECASE)
        s = re.sub(r"</?div[^>]*>", " ", s, flags=re.IGNORECASE)
        s = re.sub(r"<br\s*/?>", " ", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+", " ", s)
        return s.strip()

    # Slots
    def slot_repl(match):
        name = match.group(1)
        default_html = match.group(2)
        value = param_values.get(name)
        if value is None:
            return ''
        return _inline_slot_html(str(value))

    html = slot_pattern.sub(slot_repl, html)

    # Images
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
        return ''

    html = image_pattern.sub(image_repl, html)

    # Nettoyage divers
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

    # Params simples
    def param_repl(match):
        name = match.group(1)
        value = param_values.get(name)
        if value is None:
            return match.group(0)
        return str(value)

    rendered = param_pattern.sub(param_repl, html)
    # Fallback layout wrappers for section blocks (non Tailwind environments)
    try:
        btype = getattr(block, "block_type", "")
        if btype in ("s100", "s50_50", "s70_30"):
            rendered = f'<div class="{btype}">{rendered}</div>'
    except Exception:
        pass

    # Remove isolated 'FC' lines
    rendered = re.sub(r'(?is)<p[^>]*>\s*FC\s*</p>', '', rendered)
    return rendered


def _apply_params_to_text(s: str, param_values: Dict[str, Any]) -> str:
    if not isinstance(s, str) or not param_values:
        return s or ""
    param_pattern = re.compile(r"\[\[\s*([A-Za-z_][A-Za-z0-9_]*)\s*\]\]")
    def repl(m):
        k = m.group(1)
        return str(param_values.get(k, m.group(0)))
    return param_pattern.sub(repl, s)


def _inline_html_once(html_str: str) -> str:
    """Compacte un petit bloc HTML en une seule ligne lisible (retire <p>, <div>, <br>)."""
    if not html_str:
        return ''
    s = html_str.strip()
    # Retirer un <p> englobant
    m = re.match(r"^<p[^>]*>([\s\S]*?)</p>$", s, flags=re.IGNORECASE)
    if m:
        s = m.group(1)
    # Aplatir quelques balises de bloc
    s = re.sub(r"</?p[^>]*>", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"</?div[^>]*>", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.IGNORECASE)
    # Espaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


def build_selection_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Construit le contexte de sélection à partir du payload JSON.
    Réutilise les fonctions existantes des selectors.
    """
    # Récupérer les objets depuis la base
    niveau_id = payload.get('niveau_id')
    chapitre_ids = payload.get('chapitre_ids', [])
    cours_ids = payload.get('cours_ids', [])

    try:
        niveau = Niveau.objects.get(id=niveau_id) if niveau_id else None
        # Priorité aux cours si fournis
        cours_pages = []
        if cours_ids:
            cours_pages = list(CoursPage.objects.filter(id__in=cours_ids))
        # Sinon, on retombe sur les chapitres
        chapitres = list(Chapitre.objects.filter(id__in=chapitre_ids)) if chapitre_ids else []
        # Si aucun des deux n'est fourni, on retourne vide
        if not cours_pages and not chapitres:
            return {
                'qcms': [],
                'flashcards': [],
                'exercices': [],
                'sommaire': [],
                'options': {}
            }
    except (Niveau.DoesNotExist, Chapitre.DoesNotExist):
        return {
            'qcms': [],
            'flashcards': [],
            'exercices': [],
            'sommaire': [],
            'options': {}
        }
    
    # Déterminer le type de génération
    generation_type = payload.get('type', 'ds')  # 'ds' ou 'serie'
    
    if generation_type == 'ds':
        # Utiliser la fonction existante pour DS
        params = {
            'niveau': niveau,
            # ContentSelector accepte une liste de CoursPage ou de Chapitre
            'chapitres': (cours_pages if cours_pages else chapitres),
            'qcm_min': payload.get('qcm_min', 0),
            'qcm_max': payload.get('qcm_max', 10),
            'points_par_qcm': payload.get('points_par_qcm', 1.0),
            'fc_min': payload.get('fc_min', 0),
            'fc_max': payload.get('fc_max', 10),
            'points_par_fc': payload.get('points_par_fc', 1.0),
            'use_lvl1': payload.get('use_lvl1', True),
            'ex_lvl1_min': payload.get('ex_lvl1_min', 0),
            'ex_lvl1_max': payload.get('ex_lvl1_max', 5),
            'use_lvl2': payload.get('use_lvl2', True),
            'ex_lvl2_min': payload.get('ex_lvl2_min', 0),
            'ex_lvl2_max': payload.get('ex_lvl2_max', 5),
            'use_lvl3': payload.get('use_lvl3', True),
            'ex_lvl3_min': payload.get('ex_lvl3_min', 0),
            'ex_lvl3_max': payload.get('ex_lvl3_max', 5),
            'equilibrer_par_chapitre': payload.get('equilibrer_par_chapitre', True),
            'bareme_global': payload.get('bareme_global', 20),
        }
        
        content_data = generate_ds_content(params)
        
        # Séparer exercices et questions de cours
        exercices = content_data['exercices']
        questions_cours = content_data['questions_cours']
        
        # Construire le sommaire
        sommaire = []
        for exo in exercices:
            sommaire.append({
                'titre': exo['titre'],
                'points': exo['points'],
                'duree': exo['duree']
            })
        
        # Convertir en format HTML pour le template + variantes via seed
        seed = payload.get('seed')  # optionnel : seed global
        exo_variants: Dict[int, Any] = {}
        try:
            # Dictionnaire { exo_id: seed }
            exo_variants = payload.get('exo_variants', {}) or {}
        except Exception:
            exo_variants = {}
        exercices_html = []
        for exo in exercices:
            try:
                exo_obj = ExoPageSimple.objects.filter(id=exo.get('exo_id')).specific().first()
                exo_seed = None
                if isinstance(exo_variants, dict):
                    exo_seed = exo_variants.get(exo.get('exo_id'))
                param_values = _build_param_values_for_exo(exo_obj, exo_seed if exo_seed is not None else seed)

                enonce_parts, correction_parts = [], []
                for block in exo_obj.contenu:
                    rendered = _render_block_with_params(block, param_values)
                    if block.block_type == 'question':
                        val = getattr(block, 'value', {}) or {}
                        pts = val.get('points') or val.get('bareme') or val.get('score') or val.get('pts') or ''
                        corr_src = val.get('correction') or val.get('reponse') or ''
                        corr_html = _apply_params_to_text(corr_src, param_values)
                        compact_line = _inline_html_once(rendered)
                        enonce_parts.append(
                            f'''<div class="exo-q avoid-break" style="display:grid;grid-template-columns:90% 10%;gap:16px;">
                                  <div>{compact_line}</div>
                                  <div class="text-right font-semibold">{((str(pts)+' pts') if pts else '')}</div>
                                </div>'''
                        )
                        corr_block = f'<div class="mt-2 text-green-700">{corr_html}</div>' if corr_html else ''
                        correction_parts.append(
                            f'''<div class="exo-q avoid-break" style="display:grid;grid-template-columns:90% 10%;gap:16px;">
                                  <div>{compact_line}{corr_block}</div>
                                  <div class="text-right font-semibold">{((str(pts)+' pts') if pts else '')}</div>
                                </div>'''
                        )
                    else:
                        enonce_parts.append(rendered)
                        correction_parts.append(rendered)

                enonce_html = "\n".join(enonce_parts)
                correction_html = "\n".join(correction_parts)
            except Exception:
                enonce_html = exo['enonce']
                correction_html = exo.get('correction') or exo['enonce']

            exercices_html.append({
                'titre': exo['titre'],
                'html_enonce': enonce_html,
                'html_correction': correction_html,
                'points': exo['points'],
                'duree': exo['duree']
            })
        
        # Convertir QCM et FC en format HTML (supporte options {'html','is_correct'})
        qcms_html = []
        for qcm in questions_cours:
            if qcm['type'].startswith('qcm'):
                opts = qcm.get('options', []) or []
                choices = []
                correct_idx = None
                for i, opt in enumerate(opts):
                    # Accepte 'html' ou 'text'
                    html_val = None
                    if isinstance(opt, dict):
                        html_val = opt.get('html') or opt.get('text')
                        if opt.get('is_correct') and correct_idx is None:
                            correct_idx = i
                    if html_val is None:
                        html_val = str(opt)
                    choices.append(html_val)

                qcms_html.append({
                    'question_html': qcm.get('enonce'),
                    'choices': choices,
                    'correct_answer': correct_idx if correct_idx is not None else qcm.get('correct_answer'),
                    'points': payload.get('points_par_qcm', 1.0)
                })
        
        # Forcer l'absence de flashcards dans le PDF (demande spécifiée)
        flashcards_html = []
        
        return {
            'qcms': qcms_html,
            'flashcards': flashcards_html,
            'exercices': exercices_html,
            'sommaire': sommaire,
            'options': {
                'points_total': content_data['points_total'],
                'duree_totale': content_data['duree_totale'],
                'bareme_global': content_data['bareme_global'],
            }
        }
    
    else:  # serie
        # Utiliser la fonction existante pour série
        params = {
            'niveau': niveau,
            'chapitres': (cours_pages if cours_pages else chapitres),
            'nb_ex_lvl1': payload.get('nb_ex_lvl1', 0),
            'nb_ex_lvl2': payload.get('nb_ex_lvl2', 0),
            'nb_ex_lvl3': payload.get('nb_ex_lvl3', 0),
            'nb_qcm': payload.get('nb_qcm', 0),
            'nb_fc': payload.get('nb_fc', 0),
            'equilibrer_par_chapitre': payload.get('equilibrer_par_chapitre', True),
        }
        
        content_data = generate_serie_content(params)
        
        # Construire le sommaire
        sommaire = []
        for exo in content_data['exercices']:
            sommaire.append({
                'titre': exo['titre'],
                'points': exo['points'],
                'duree': exo['duree']
            })
        
        # Convertir en format HTML pour le template
        exercices_html = []
        for exo in content_data['exercices']:
            exercices_html.append({
                'titre': exo['titre'],
                'html': exo['enonce'],
                'points': exo['points'],
                'duree': exo['duree']
            })
        
        # Convertir QCM et FC en format HTML
        qcms_html = []
        for qcm in content_data['questions_cours']:
            if qcm['type'].startswith('qcm'):
                qcms_html.append({
                    'question_html': qcm['enonce'],
                    'choices': [opt['text'] for opt in qcm.get('options', [])],
                    'points': 1.0
                })
        
        flashcards_html = []
        for fc in content_data['questions_cours']:
            if fc['type'].startswith('fc'):
                flashcards_html.append({
                    'front': fc['enonce'],
                    'hint': fc.get('reponse', ''),
                })
        
        return {
            'qcms': qcms_html,
            'flashcards': flashcards_html,
            'exercices': exercices_html,
            'sommaire': sommaire,
            'options': {}
        }
