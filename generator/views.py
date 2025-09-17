# generator/views.py
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_GET
from django.template.loader import render_to_string
from django.conf import settings

import os
import re
import random
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse
import hashlib
import json

from referentiel.models import Niveau
from kahoot.utils import get_available_chapters_by_niveau
from .services.selection import build_selection_bundle
from .services.media_paths import normalize_media_url, extract_img_srcs



# =========================
# Utils
# =========================
def _is_true(v) -> bool:
    return str(v).lower() in ("1", "true", "yes", "on")
def _rng_from_seed(base_seed: str, *parts: str) -> random.Random:
    """Crée un RNG déterministe à partir d'une graine de base et de sous-clés.
    Utilise md5 pour un entier stable indépendamment de l'instance Python.
    """
    key = (base_seed or "0") + "::" + "::".join(str(p) for p in parts)
    h = hashlib.md5(key.encode("utf-8")).hexdigest()
    seed_int = int(h[:16], 16)
    return random.Random(seed_int)


def _image_abspath(img):
    """
    Retourne un chemin disque exploitable par LaTeX pour une Wagtail Image/Rendition.
    None si pas trouvable.
    """
    try:
        f = getattr(img, "file", None)
        if f and hasattr(f, "path"):
            return f.path
        # parfois "img" est une rendition
        rend = getattr(img, "image", None)
        if rend and hasattr(rend, "file") and hasattr(rend.file, "path"):
            return rend.file.path
    except Exception:
        pass
    return None


def _logo_path_for_latex(value: str | None) -> str:
    """
    LaTeX ne charge pas les URLs http/https. On renvoie un chemin disque ou "".
    """
    if not value:
        return ""
    
    # chemin absolu
    if os.path.isabs(value) and os.path.exists(value):
        return value
    
    # chemin /media/... (convertir en chemin local)
    if value.startswith("/media/"):
        # Convertir /media/images/logo.original.png en chemin local
        media_root = os.path.join(settings.MEDIA_ROOT)
        local_path = os.path.join(media_root, value[7:])  # Enlever "/media/"
        if os.path.exists(local_path):
            return local_path
    
    # chemin relatif depuis la racine du projet
    if value.startswith("/"):
        abs_guess = os.path.abspath(value)
        if os.path.exists(abs_guess):
            return abs_guess
    
    # Pour les URLs, essayer de deviner le chemin local
    if value.startswith("http"):
        # Essayer de convertir l'URL en chemin local
        if "media/images/logo.original.png" in value:
            # Chemin par défaut pour le logo
            default_logo = os.path.join(settings.MEDIA_ROOT, "images", "logo.original.png")
            if os.path.exists(default_logo):
                return default_logo
    
    # sinon (URL, etc.)
    return ""


def _html_to_tex(s: str) -> str:
    """(optionnel) mini nettoyage HTML -> LaTeX pour QCM courts."""
    if not s:
        return ""
    txt = str(s)
    txt = re.sub(r"<\s*br\s*/?\s*>", r"\\newline ", txt, flags=re.I)
    txt = re.sub(r"</?\s*(b|strong)\s*>", r"", txt, flags=re.I)
    txt = re.sub(r"</?\s*(i|em)\s*>", r"", txt, flags=re.I)
    txt = re.sub(r"<\s*sub\s*>", r"$_{", txt, flags=re.I)
    txt = re.sub(r"<\s*/\s*sub\s*>", r"}$", txt, flags=re.I)
    txt = re.sub(r"<\s*sup\s*>", r"$^{", txt, flags=re.I)
    txt = re.sub(r"<\s*/\s*sup\s*>", r"}$", txt, flags=re.I)
    txt = re.sub(r"<[^>]+>", "", txt)
    for a, b in [
        ("\\", r"\textbackslash{}"),
        ("{", r"\{"), ("}", r"\}"),
        ("#", r"\#"), ("$", r"\$"), ("%", r"\%"),
        ("&", r"\&"), ("_", r"\_"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]:
        txt = txt.replace(a, b)
    return txt


# =========================
# Pages HTML
# =========================
def index(request: HttpRequest) -> HttpResponse:
    return render(request, "generator/index.html")


def devoir_page(request: HttpRequest) -> HttpResponse:
    niveaux = list(Niveau.objects.all())
    chapters_structure = get_available_chapters_by_niveau()
    return render(
        request,
        "generator/devoir_wizard.html",
        {"niveaux": niveaux, "chapters_structure": chapters_structure},
    )


# =========================
# API payload (session)
# =========================
@csrf_exempt
def save_payload(request: HttpRequest):
    """Sauvegarde du payload JSON dans la session."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Invalid method"}, status=405)
    import json
    try:
        data = json.loads(request.body.decode("utf-8"))
        request.session["generator_payload"] = data
        request.session.modified = True
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)


# =========================
# Preview HTML (QCM/QR/Exos)
# =========================
@require_http_methods(["GET"])
def qcm_preview_old(request: HttpRequest) -> HttpResponse:
    """
    ANCIENNE FONCTION - Remplacée par la nouvelle utilisant le service de sélection
    Prévisualisation DS ou Série.
    - DS : barème (approx) / min-max
    - Série : compteurs fixes
    """
    from qcm.models import QcmQuestionAPage, QcmBankBPage, QcmQuestionCPage
    from flashcard.models import FlashcardItem
    from exo.models import ExoPageSimple, ParametreExoPage

    payload = request.session.get("generator_payload", {}) or {}
    type_ds = str(payload.get("type", request.GET.get("type", "ds"))).lower()

    # seed base (varie en JS via Date.now())
    base_seed = str(request.GET.get("seed") or payload.get("seed") or random.randint(1, 10**9))

    qcm_pool, qcms, qa_pool, qa_cards, exercices = [], [], [], [], []
    letters = ["A", "B", "C", "D"]

    # QCM A
    for q in QcmQuestionAPage.objects.live().specific():
        opts = list(q.options.all())
        if len(opts) >= 4:
            corrects = [o for o in opts if o.is_correct]
            incorrects = [o for o in opts if not o.is_correct]
            if len(corrects) >= 1 and len(incorrects) >= 3:
                rng = _rng_from_seed(base_seed, f"QA-{q.id}")
                correct = rng.choice(corrects)
                distractors = rng.sample(incorrects, 3)
                pool = [correct, *distractors]
                rng.shuffle(pool)
                options_html = [o.text for o in pool]
                correct_index = pool.index(correct) + 1
                qcm_pool.append({
                    "statement": q.statement,
                    "image": q.image,
                    "options": options_html,
                    "correct_index": correct_index,
                    "correct_letter": letters[correct_index - 1],
                    "correct_text": options_html[correct_index - 1],
                    "bareme": float(payload.get("ds_qcm_point", 1)),
                })

    # QCM B
    for bank in QcmBankBPage.objects.live().specific():
        variants = list(bank.variants.all())
        if len(variants) >= 4:
            rng = _rng_from_seed(base_seed, f"QB-{bank.id}")
            correct = rng.choice(variants)
            others = [v for v in variants if v != correct]
            if len(others) >= 3:
                distractors = rng.sample(others, 3)
                pool = [correct.answer] + [d.answer for d in distractors]
                rng.shuffle(pool)
                correct_index = pool.index(correct.answer) + 1
                qcm_pool.append({
                    "statement": correct.statement,
                    "image": correct.image,
                    "options": pool,
                    "correct_index": correct_index,
                    "correct_letter": letters[correct_index - 1],
                    "correct_text": pool[correct_index - 1],
                    "bareme": float(payload.get("ds_qcm_point", 1)),
                })

    # QCM C
    for q in QcmQuestionCPage.objects.live().specific():
        correct_answers = q.get_correct_answers_list()
        incorrect_answers = q.get_incorrect_answers_list()
        if len(correct_answers) >= 1 and len(incorrect_answers) >= 3:
            rng = _rng_from_seed(base_seed, f"QC-{q.id}")
            correct = rng.choice(correct_answers)
            distractors = rng.sample(incorrect_answers, 3)
            pool = [correct, *distractors]
            rng.shuffle(pool)
            correct_index = pool.index(correct) + 1
            qcm_pool.append({
                "statement": q.statement,
                "image": q.image,
                "options": pool,
                "correct_index": correct_index,
                "correct_letter": letters[correct_index - 1],
                "correct_text": pool[correct_index - 1],
                "bareme": float(payload.get("ds_qcm_point", 1)),
            })

    # Flashcards
    for card in FlashcardItem.objects.filter(is_active=True)[:50]:
        # Une seule "variante" logique par carte (déterministe)
        rng = _rng_from_seed(base_seed, f"FC-{card.id}")
        qa_pool.append({
            "question_html": str(card.question),
            "answer_html": str(card.answer),
            "image": getattr(card, "image", None),
            "_seed": rng.random(),
        })

    # Exercices
    exo_pool = list(ExoPageSimple.objects.live().specific())

    # --- DS
    if type_ds == "ds":
        bareme_global = float(payload.get("bareme_global", request.GET.get("bareme_global", 20)))
        remaining = bareme_global

        if _is_true(payload.get("ds_qcm_enable", True)):
            pt_q = float(payload.get("ds_qcm_point", 1))
            min_q = int(payload.get("ds_qcm_min", 0))
            if pt_q > 0 and min_q > 0 and remaining >= pt_q:
                n_q_min = min(min_q, int(remaining // pt_q), len(qcm_pool))
                if n_q_min > 0:
                    qcms.extend(random.sample(qcm_pool, n_q_min))
                    remaining -= n_q_min * pt_q

        if _is_true(payload.get("ds_qr_enable", False)):
            pt_fc = float(payload.get("ds_qr_point", 1))
            min_fc = int(payload.get("ds_qr_min", 0))
            if pt_fc > 0 and min_fc > 0 and remaining >= pt_fc:
                n_fc_min = min(min_fc, int(remaining // pt_fc), len(qa_pool))
                if n_fc_min > 0:
                    qa_cards.extend(random.sample(qa_pool, n_fc_min))
                    remaining -= n_fc_min * pt_fc

        if exo_pool and (
            _is_true(payload.get("ds_exo_application_enable", False)) or
            _is_true(payload.get("ds_exo_entrainement_enable", False)) or
            _is_true(payload.get("ds_exo_approfondissement_enable", False))
        ):
            by_level = {1: [], 2: [], 3: []}
            for exo in exo_pool:
                lvl = getattr(exo, "difficulty", 2) or 2
                if lvl in by_level:
                    by_level[lvl].append(exo)

            for lvl in (1, 2, 3):
                random.shuffle(by_level[lvl])
                for exo in list(by_level[lvl]):
                    pts = float(getattr(exo, "total_points", 0) or 0)
                    if pts > 0 and pts <= remaining:
                        seed_for_this = f"{base_seed}-{exo.id}-{len(exercices)}"
                        params_page = exo.get_children().type(ParametreExoPage).specific().first()
                        param_values = params_page.build_random_context(seed=seed_for_this) if params_page else {}
                        exercices.append({
                            "page": exo,
                            "title": exo.title,
                            "difficulty": exo.difficulty,
                            "estimated_time_min": exo.estimated_time_min,
                            "total_points": pts,
                            "param_values": param_values,
                        })
                        remaining -= pts
                    if remaining <= 0:
                        break
                if remaining <= 0:
                    break

        if _is_true(payload.get("ds_qcm_enable", True)) and remaining > 0:
            pt_q = float(payload.get("ds_qcm_point", 1))
            max_q = int(payload.get("ds_qcm_max", 10))
            cur_q = len(qcms)
            while cur_q < max_q and remaining >= pt_q and qcm_pool:
                rng_pick = _rng_from_seed(base_seed, f"PICK-Q-{cur_q}")
                qcms.append(rng_pick.choice(qcm_pool))
                remaining -= pt_q
                cur_q += 1

        if _is_true(payload.get("ds_qr_enable", False)) and remaining > 0:
            pt_fc = float(payload.get("ds_qr_point", 1))
            max_fc = int(payload.get("ds_qr_max", 10))
            cur_fc = len(qa_cards)
            while cur_fc < max_fc and remaining >= pt_fc and qa_pool:
                rng_pick = _rng_from_seed(base_seed, f"PICK-FC-{cur_fc}")
                qa_cards.append(rng_pick.choice(qa_pool))
                remaining -= pt_fc
                cur_fc += 1

        barreme_total = bareme_global - remaining
        barreme_cible = bareme_global

    # --- Série
    else:
        serie_qcm_count = int(payload.get("serie_qcm_count", 0))
        serie_qr_count = int(payload.get("serie_qr_count", 0))
        serie_exo_app = int(payload.get("serie_exo_application_count", 0))
        serie_exo_ent = int(payload.get("serie_exo_entrainement_count", 0))
        serie_exo_appf = int(payload.get("serie_exo_approfondissement_count", 0))

        if serie_qcm_count > 0:
            qcms = random.sample(qcm_pool, min(len(qcm_pool), serie_qcm_count))
        if serie_qr_count > 0:
            qa_cards = random.sample(qa_pool, min(len(qa_pool), serie_qr_count))

        nb_exos = max(0, serie_exo_app + serie_exo_ent + serie_exo_appf)
        if nb_exos > 0 and exo_pool:
            picked = random.sample(exo_pool, min(nb_exos, len(exo_pool)))
            for i, chosen in enumerate(picked):
                seed_for_this = f"{base_seed}-{chosen.id}-{i}"
                params_page = chosen.get_children().type(ParametreExoPage).specific().first()
                param_values = params_page.build_random_context(seed=seed_for_this) if params_page else {}
                exercices.append({
                    "page": chosen,
                    "title": chosen.title,
                    "difficulty": chosen.difficulty,
                    "estimated_time_min": chosen.estimated_time_min,
                    "total_points": float(chosen.total_points),
                    "param_values": param_values,
                })

        barreme_total = None
        barreme_cible = None

    return render(
        request,
        "generator/qcm_preview.html",
        {
            "type": type_ds,
            "qcms": qcms,
            "qa_cards": qa_cards,
            "exercices": exercices,
            "barreme_total": barreme_total,
            "barreme_cible": barreme_cible,
            # recap
            "ds_qcm_min": int(payload.get("ds_qcm_min") or request.GET.get("ds_qcm_min") or 0),
            "ds_qcm_max": int(payload.get("ds_qcm_max") or request.GET.get("ds_qcm_max") or 0),
            "ds_qr_min": int(payload.get("ds_qr_min") or request.GET.get("ds_qr_min") or 0),
            "ds_qr_max": int(payload.get("ds_qr_max") or request.GET.get("ds_qr_max") or 0),
            "ds_qcm_enable": str(payload.get("ds_qcm_enable") or request.GET.get("ds_qcm_enable") or "1") in ("1","true","True","yes","on"),
            "ds_qr_enable": str(payload.get("ds_qr_enable") or request.GET.get("ds_qr_enable") or "0") in ("1","true","True","yes","on"),
            "ds_exo_application_enable": str(payload.get("ds_exo_application_enable") or request.GET.get("ds_exo_application_enable") or "0") in ("1","true","True","yes","on"),
            "ds_exo_entrainement_enable": str(payload.get("ds_exo_entrainement_enable") or request.GET.get("ds_exo_entrainement_enable") or "0") in ("1","true","True","yes","on"),
            "ds_exo_approfondissement_enable": str(payload.get("ds_exo_approfondissement_enable") or request.GET.get("ds_exo_approfondissement_enable") or "0") in ("1","true","True","yes","on"),
        },
    )


# =========================
# Génération PDF LaTeX
# =========================
def pdf_build(request: HttpRequest, mode: str) -> HttpResponse:
    """
    Construit le PDF (énoncé|correction) à partir de templates LaTeX :
    templates/generator/pdf/{main.tex, header.tex, section_qcm.tex, section_flashcards.tex, section_exercices.tex}
    Utilise le bundle en session pour garantir la cohérence avec la preview.
    """
    mode = (mode or "").lower().strip()
    if mode not in ("enonce", "correction"):
        return HttpResponseBadRequest("Mode invalide (enonce|correction)")

    payload = request.session.get("generator_payload", {}) or {}
    type_ds = str(payload.get("type", "ds")).lower()
    is_correction = 1 if mode == "correction" else 0

    # Récupérer le bundle en session (garantit la cohérence avec la preview)
    bundle_json = request.session.get("selection_bundle")
    if not bundle_json:
        # Si pas de bundle en session, en créer un
        seed = str(payload.get("seed") or random.randint(1, 10**9))
        bundle = build_selection_bundle(payload, seed)
        bundle_json = bundle.to_jsonable()
        request.session["selection_bundle"] = bundle_json
        request.session["selection_seed"] = seed

    # Enrichissement images pour TeX (et debug)
    def enrich_images(items, media_key="media"):
        for it in items:
            # 1) sources directes (media)
            imgs = list(it.get(media_key, []) or [])
            # 2) fallback: extraire <img> du HTML si pas de media explicite
            if not imgs:
                imgs += extract_img_srcs(it.get("statement_html"))
            if not imgs:
                imgs += extract_img_srcs(it.get("correction_html"))
            # 3) compat: champ 'image' simple éventuel
            if not imgs and it.get("image"):
                imgs.append(it["image"])

            resolved = []
            for src in imgs:
                abs_path, ok = normalize_media_url(src)
                resolved.append({
                    "src": src,
                    "image_abs_path": abs_path,
                    "image_exists": bool(ok),
                })
            it["resolved_media"] = resolved
            # Compat: première image rapide
            if resolved:
                it["has_image"] = any(x["image_exists"] for x in resolved)
                first_ok = next((x for x in resolved if x["image_exists"]), None)
                it["image_path"] = first_ok["image_abs_path"] if first_ok else resolved[0]["image_abs_path"]
            else:
                it["has_image"] = False
                it["image_path"] = None

    enrich_images(bundle_json.get("qcms", []))
    enrich_images(bundle_json.get("exercices", []))  # <<< essentiel pour la section exercices

    # Fonction helper pour convertir URL en chemin disque
    def _image_abspath_from_url(image_url):
        """Convertit une URL d'image en chemin disque pour LaTeX"""
        if not image_url:
            return None
        try:
            # Si c'est une URL relative /media/...
            if image_url.startswith('/media/'):
                return os.path.join(settings.MEDIA_ROOT, image_url[7:])  # Enlever '/media/'
            # Si c'est une URL complète, essayer d'extraire le chemin
            elif 'media/' in image_url:
                parts = image_url.split('media/')
                if len(parts) > 1:
                    return os.path.join(settings.MEDIA_ROOT, parts[1])
        except Exception:
            pass
        return None

    # Extraire les données du bundle
    qcms_data = bundle_json.get("qcms", [])
    flashcards_data = bundle_json.get("flashcards", [])
    exercices_data = bundle_json.get("exercices", [])

    # Adapter les données du bundle pour les templates LaTeX
    qcm_for_tex = []
    for qcm in qcms_data:
        options = qcm.get("options", [])
        A, B, C, D = (options + ["", "", "", ""])[:4]
        
        # Récupérer l'image depuis les médias
        media_list = qcm.get("media", [])
        image_path = ""
        if media_list:
            # Prendre la première image de la liste (c'est un ID, pas une URL)
            image_id = media_list[0]
            try:
                from wagtail.images.models import Image
                image_obj = Image.objects.filter(id=int(image_id)).first()
                if image_obj and image_obj.file:
                    # Convertir le chemin de l'image en chemin absolu pour LaTeX
                    image_path = _image_abspath_from_url(image_obj.file.url) or ""

            except (ValueError, TypeError):
                pass
        
        qcm_for_tex.append({
            "statement": qcm.get("statement_html", ""),
            "A": A, "B": B, "C": C, "D": D,
            "points": qcm.get("points", 1),
            "correct_index": int(qcm.get("correct_index", 1)),
            "image_path": image_path,
            "has_image": bool(image_path),
        })

    # Adapter les flashcards pour les templates LaTeX
    flashcards_for_tex = []
    for fc in flashcards_data:
        media_list = fc.get("media", [])
        image_path = ""
        if media_list:
            # Prendre la première image de la liste (c'est un ID, pas une URL)
            image_id = media_list[0]
            try:
                from wagtail.images.models import Image
                image_obj = Image.objects.filter(id=int(image_id)).first()
                if image_obj and image_obj.file:
                    # Convertir le chemin de l'image en chemin absolu pour LaTeX
                    image_path = _image_abspath_from_url(image_obj.file.url) or ""

            except (ValueError, TypeError):
                pass
        
        flashcards_for_tex.append({
            "question_html": fc.get("question_html", ""),
            "answer_html": fc.get("answer_html", ""),
            "image_path": image_path,
            "has_image": bool(image_path),
            "points": fc.get("points", 1),
        })

    # Adapter les exercices pour les templates LaTeX (comme qcm_preview)
    exercices_for_tex = []
    for ex in exercices_data:
        # Récupérer l'objet ExoPageSimple depuis la base de données
        ex_page = None
        try:
            from exo.models import ExoPageSimple
            ex_page = ExoPageSimple.objects.filter(id=ex.get("id_page")).first()
        except Exception:
            pass
        
        # Construire la liste de candidats d'images (ordre de priorité)
        candidates = []
        
        # (a) déjà enrichi en amont ?
        if ex.get("image_path"):
            candidates.append(ex["image_path"])
        for m in ex.get("resolved_media", []) or []:
            # resolved_media vient de enrich_images : garde les absolus d'abord
            if m.get("image_abs_path"):
                candidates.append(m["image_abs_path"])
            if m.get("src"):
                candidates.append(m["src"])

        # (b) champ "media" brut du bundle (ids/urls)
        for src in ex.get("media", []) or []:
            candidates.append(src)

        # (c) extraire du HTML rendu (statement, puis correction)
        for src in extract_img_srcs(ex.get("statement_html")):
            candidates.append(src)
        for src in extract_img_srcs(ex.get("correction_html")):
            candidates.append(src)

        # Pré-rendre les blocs avec les paramètres pour le template LaTeX
        rendered_blocks = []
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG PDF: ex_page = {ex_page}")
        logger.info(f"DEBUG PDF: ex_page.contenu = {ex_page.contenu if ex_page else 'None'}")
        if ex_page and ex_page.contenu:
            from django.template import engines
            from exo.templatetags.param_tags import render_with_params
            django_engine = engines['django']
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"DEBUG PDF: Traitement de {len(ex_page.contenu)} blocs pour la page {ex_page.id}")
            
            # Contexte partagé pour stabiliser N et les seeds entre énoncé et solution
            shared_context = {
                'request': request,
                'param_values': ex.get("param_values", {}) or {},
            }
            # Graine stable si disponible (cohérente avec preview)
            try:
                base_seed = str(request.session.get("selection_seed") or payload.get("seed") or "0")
                shared_context['K'] = base_seed
                shared_context['__render_seed'] = int(hashlib.md5(base_seed.encode()).hexdigest()[:8], 16)
            except Exception:
                pass

            for block in ex_page.contenu:
                try:
                    # Rendre le bloc avec les paramètres, en réutilisant le même contexte
                    param_values = ex.get("param_values", {}) or {}
                    rendered_html = render_with_params(shared_context, block, param_values)
                    
                    # Filets de secours pour symboles (mojibake/grec) avant passage LaTeX
                    try:
                        rendered_html = rendered_html.replace("ÃŽÂ»", "${\\lambda}$").replace("Î»", "${\\lambda}$")
                    except Exception:
                        pass
                    
                    # FORCER le remplacement des paramètres si pas fait
                    if param_values:
                        import re
                        # Remplacer [[param]] par les valeurs (TOUTES les occurrences)
                        for param_name, param_value in param_values.items():
                            if isinstance(param_value, str):
                                pattern = re.compile(f'\\[\\[\\s*{re.escape(param_name)}\\s*\\]\\]', re.IGNORECASE)
                                rendered_html = pattern.sub(str(param_value), rendered_html)
                        
                        # DEBUG: Vérifier si les paramètres de tableau sont présents
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.info(f"DEBUG PDF: param_values pour exercice {ex.get('title', 'Unknown')}: {list(param_values.keys())}")
                        for name, value in param_values.items():
                            if isinstance(value, dict) and 'orientation' in value:
                                logger.info(f"DEBUG PDF: Paramètre tableau {name}: {value}")
                    rendered_blocks.append({
                        'block_type': block.block_type,
                        'value': block.value,
                        'rendered_html': rendered_html,
                    })
                    
                    # Extraire les images du HTML rendu et les ajouter aux candidats
                    for src in extract_img_srcs(rendered_html):
                        candidates.append(src)
                        
                except Exception as e:
                    print(f"Erreur rendu bloc {block.block_type}: {e}")
                    # Fallback: rendu simple
                    rendered_html = str(block)
                    rendered_blocks.append({
                        'block_type': block.block_type,
                        'value': block.value,
                        'rendered_html': rendered_html,
                    })
                    
                    # Extraire les images du fallback aussi
                    for src in extract_img_srcs(rendered_html):
                        candidates.append(src)

        # Résoudre vers un chemin disque existant (premier OK) - APRÈS le rendu des blocs
        image_path = ""
        for src in candidates:
            if not src:
                continue
            # si déjà un chemin absolu plausible
            if isinstance(src, str) and src.startswith(("/", "/srv/", "/var/", "/home/")):
                if os.path.exists(src):
                    image_path = src
                    break
            # sinon normaliser via MEDIA_ROOT, online/media, /media, etc.
            abs_path, ok = normalize_media_url(str(src))
            if ok and abs_path:
                image_path = abs_path
                break

        # Assembler l'item pour TeX
        exercices_for_tex.append({
            "title": ex.get("title", ""),
            "total_points": ex.get("total_points", 1),
            "difficulty": ex.get("difficulty"),
            "estimated_time_min": ex.get("estimated_time_min"),
            "page": ex_page,  # ← OBJET PAGE COMPLET (comme qcm_preview)
            "rendered_blocks": rendered_blocks,  # ← BLOCS PRÉ-RENDUS
            "param_values": ex.get("param_values", {}),  # ← PARAMÈTRES
            "image_path": image_path,  # ← GARDER POUR COMPATIBILITÉ
            "has_image": bool(image_path),  # ← GARDER POUR COMPATIBILITÉ
        })

        # Log côté serveur utile pour debug
        print("DEBUG EXO PICKED IMAGE:", ex.get("title", ""), "->", image_path)

    DEFAULT_LOGO_URL = "https://physiquechimie.online/media/images/logo.original.png"

# on prend l'URL du payload si fournie, sinon le logo par défaut
    logo_url = payload.get("header_logo_url") or DEFAULT_LOGO_URL

# convertit l'URL /media/... en chemin disque pour LaTeX
    header_logo_path = _logo_path_for_latex(logo_url)
    
    # Debug: afficher les chemins pour comprendre
    print(f"DEBUG: logo_url = {logo_url}")
    print(f"DEBUG: header_logo_path = {header_logo_path}")
    print(f"DEBUG: settings.MEDIA_ROOT = {settings.MEDIA_ROOT}")

# (optionnel) si le fichier n'existe pas en local, on force le mode "texte"
    if not header_logo_path:
    # laisser vide => l’entête LaTeX affichera les 3 lignes de texte
         header_logo_path = ""
    # Contexte LaTeX
    ctx = {
    # === jeux de variables attendues par tes .tex ===
    # (A) Noms "bruts" utilisés par ton main.tex actuel
        "type": "ds" if type_ds == "ds" else "serie",
        "barreme_cible": int(float(payload.get("bareme_global", 20))),
        "sous_titre_1": payload.get("sous_titre_1", ""),
        "sous_titre_2": payload.get("sous_titre_2", ""),
        "header_logo_path": header_logo_path,
        "header_line1": payload.get("header_line1", "PHYSIQUE"),
        "header_line2": payload.get("header_line2", "CHIMIE"),
        "header_line3": payload.get("header_line3", "ONLINE"),
        "titre": payload.get("titre", "Devoir"),
        "is_correction": 1 if mode == "correction" else 0,

        # (B) Anciennes clés (si d'autres templates les utilisent)
        "typeDS": "ds" if type_ds == "ds" else "serie",
        "baremeGlobal": int(float(payload.get("bareme_global", 20))),
        "sousTitreUn": payload.get("sous_titre_1", ""),
        "sousTitreDeux": payload.get("sous_titre_2", ""),
        "headerLineUn": payload.get("header_line1", "PHYSIQUE"),
        "headerLineDeux": payload.get("header_line2", "CHIMIE"),
        "headerLineTrois": payload.get("header_line3", "ONLINE"),
        "logoPath": header_logo_path,
        "classe": payload.get("classe", "Classe"),
        "isCorrection": 1 if mode == "correction" else 0,
        
        # Barème ajusté
        "barreme_cible": bundle_json.get("meta", {}).get("barreme_cible", 0),
        "barreme_obtenu": bundle_json.get("meta", {}).get("barreme_obtenu", 0),

        # QCM
        "qcms": qcm_for_tex,
        # Flashcards
        "flashcards": flashcards_for_tex,
        # Exercices
        "exercices": exercices_for_tex,
        # Mode pour les templates
        "mode": mode,
    }

    # Fournir également des graines stables aux templates LaTeX pour les tableaux dynamiques
    ctx.update({
        "K": str(request.session.get("selection_seed") or payload.get("seed") or "0"),
        "__render_seed": int(hashlib.md5(str(request.session.get("selection_seed") or payload.get("seed") or "0").encode()).hexdigest()[:8], 16),
    })

    # Totaux et flags pour l'entête "Questions de cours"
    qcm_points_sum = sum(float(x.get("points") or 0) for x in qcm_for_tex)
    flashcards_points_sum = sum(float(x.get("points") or 0) for x in flashcards_for_tex)
    has_qcms = bool(qcm_for_tex)
    has_flashcards = bool(flashcards_for_tex)

    ctx.update({
        "has_qcms": has_qcms,
        "has_flashcards": has_flashcards,
        "qcm_points_sum": qcm_points_sum,
        "flashcards_points_sum": flashcards_points_sum,
    })

    # Rendu & compilation
    with tempfile.TemporaryDirectory() as tmpdir:
        main_tex = render_to_string("generator/pdf/main.tex", ctx)
        header_tex = render_to_string("generator/pdf/header.tex", ctx)
        qcm_tex = render_to_string("generator/pdf/section_qcm.tex", ctx)
        flashcards_tex = render_to_string("generator/pdf/section_flashcards.tex", ctx)
        exercices_tex = render_to_string("generator/pdf/section_exercices.tex", ctx)

        with open(os.path.join(tmpdir, "main.tex"), "w", encoding="utf-8") as f:
            f.write(main_tex)
        with open(os.path.join(tmpdir, "header.tex"), "w", encoding="utf-8") as f:
            f.write(header_tex)
        with open(os.path.join(tmpdir, "section_qcm.tex"), "w", encoding="utf-8") as f:
            f.write(qcm_tex)
        with open(os.path.join(tmpdir, "section_flashcards.tex"), "w", encoding="utf-8") as f:
            f.write(flashcards_tex)
        with open(os.path.join(tmpdir, "section_exercices.tex"), "w", encoding="utf-8") as f:
            f.write(exercices_tex)

        def _run(cmd):
            return subprocess.run(
                cmd,
                cwd=tmpdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='latin-1',  # Utiliser latin-1 pour éviter les erreurs d'encodage
                errors='replace',    # Remplacer les caractères non décodables
                check=False,
            )

        # deux passes LaTeX
        for _ in range(2):
            r = _run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"])
            if r.returncode != 0:
                return HttpResponse("Erreur LaTeX:\n\n" + r.stdout, content_type="text/plain", status=500)

        pdf_path = os.path.join(tmpdir, "main.pdf")
        if not os.path.exists(pdf_path):
            return HttpResponse("PDF non généré.", status=500, content_type="text/plain")

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    filename = f"{payload.get('titre', 'devoir')}-{mode}.pdf"
    resp["Content-Disposition"] = f'inline; filename="{filename}"'
    return resp


def generate_entete_pdf(request: HttpRequest, mode: str) -> HttpResponse:
    """
    Wrapper pour tes boutons existants:
    /generator/pdf/entete/enonce/  et  /generator/pdf/entete/correction/
    Lit les champs GET (titre, sous_titre_*, header_*, type, bareme_global, classe),
    les pousse dans la session, puis appelle pdf_build(mode).
    """
    mode = (mode or "").strip().lower()
    if mode not in ("enonce", "correction"):
        return HttpResponseBadRequest("Mode invalide (enonce|correction)")

    payload = request.session.get("generator_payload", {}) or {}
    for k in [
        "type", "titre", "sous_titre_1", "sous_titre_2", "bareme_global",
        "header_logo_url", "header_line1", "header_line2", "header_line3",
        "classe",
    ]:
        v = request.GET.get(k)
        if v is not None:
            if k == "bareme_global":
                try:
                    payload[k] = float(v)
                except Exception:
                    payload[k] = v
            else:
                payload[k] = v

    payload["seed"] = payload.get("seed") or str(int(__import__("time").time() * 1000))
    request.session["generator_payload"] = payload
    request.session.modified = True
    return pdf_build(request, mode)


def _get_payload_and_seed(request: HttpRequest) -> tuple[dict, str]:
    """Helper pour récupérer payload et seed depuis session/GET"""
    payload = request.session.get("generator_payload") or {}
    
    # Si le payload de session est vide ou ne contient pas les paramètres essentiels, utiliser les valeurs par défaut
    if not payload or "type" not in payload:
        payload = {
            "type": "ds",
            "bareme_global": 20,
            "ds_qcm_enable": True,
            "ds_qr_enable": False,
            "ds_exo_application_enable": True,
            "ds_exo_entrainement_enable": True,
            "ds_exo_approfondissement_enable": True,
            "ds_qcm_point": 1,
            "ds_qr_point": 1,
        }
    
    # Permettre de surcharger les paramètres d'exercices via GET
    exo_params = [
        "ds_exo_application_enable", "ds_exo_entrainement_enable", "ds_exo_approfondissement_enable",
        "serie_exo_application_count", "serie_exo_entrainement_count", "serie_exo_approfondissement_count"
    ]
    for param in exo_params:
        if param in request.GET:
            if param.endswith("_enable"):
                payload[param] = request.GET.get(param, '').lower() in ('true', '1', 'on')
            else:
                try:
                    payload[param] = int(request.GET.get(param, 0))
                except ValueError:
                    payload[param] = 0
    
    seed = str(request.GET.get("seed") or request.session.get("selection_seed") or payload.get("seed") or "0")
    return payload, seed


def qcm_preview(request: HttpRequest) -> HttpResponse:
    """Vue preview utilisant le service de sélection centralisé"""
    payload, seed = _get_payload_and_seed(request)
    
    # Vérifier si on peut réutiliser le bundle en session
    force_rebuild = request.GET.get('force_rebuild', 'false').lower() == 'true'
    bundle_json = request.session.get("selection_bundle")
    if not bundle_json or str(request.session.get("selection_seed")) != str(seed) or force_rebuild:
        bundle = build_selection_bundle(payload, seed)
        bundle_json = bundle.to_jsonable()
        request.session["selection_bundle"] = bundle_json
        request.session["selection_seed"] = seed

    # Enrichissement images pour TeX (et debug)
    def enrich_images(items, media_key="media"):
        for it in items:
            # 1) sources directes (media)
            imgs = list(it.get(media_key, []) or [])
            # 2) fallback: extraire <img> du HTML si pas de media explicite
            if not imgs:
                imgs += extract_img_srcs(it.get("statement_html"))
            if not imgs:
                imgs += extract_img_srcs(it.get("correction_html"))
            # 3) compat: champ 'image' simple éventuel
            if not imgs and it.get("image"):
                imgs.append(it["image"])

            resolved = []
            for src in imgs:
                abs_path, ok = normalize_media_url(src)
                resolved.append({
                    "src": src,
                    "image_abs_path": abs_path,
                    "image_exists": bool(ok),
                })
            it["resolved_media"] = resolved
            # Compat: première image rapide
            if resolved:
                it["has_image"] = any(x["image_exists"] for x in resolved)
                first_ok = next((x for x in resolved if x["image_exists"]), None)
                it["image_path"] = first_ok["image_abs_path"] if first_ok else resolved[0]["image_abs_path"]
            else:
                it["has_image"] = False
                it["image_path"] = None

    enrich_images(bundle_json.get("qcms", []))
    enrich_images(bundle_json.get("exercices", []))  # <<< essentiel pour la section exercices
    # enrich_images(bundle_json.get("flashcards", []))  # si tu veux gérer des images sur cartes

    # Adapter les données pour le template
    from wagtail.images import get_image_model
    Image = get_image_model()
    
    qcms_for_template = []
    for qcm in bundle_json.get("qcms", []):
        # Récupérer l'objet Image depuis la base de données si on a un ID
        image_obj = None
        media_list = qcm.get("media", [])
        if media_list and media_list[0]:
            try:
                # Si c'est un ID, récupérer l'objet Image
                if isinstance(media_list[0], (int, str)) and str(media_list[0]).isdigit():
                    image_obj = Image.objects.filter(id=int(media_list[0])).first()
                else:
                    image_obj = media_list[0]
            except Exception:
                image_obj = None
        
        qcms_for_template.append({
            "statement": qcm.get("statement_html", ""),
            "image": image_obj,
            "options": qcm.get("options", []),
            "correct_index": qcm.get("correct_index", 1),
            "correct_letter": qcm.get("correct_letter", "A"),
            "correct_text": qcm.get("correct_text", ""),
            "points": qcm.get("points", 1),
        })

    # Adapter les exercices pour le template
    from exo.models import ExoPageSimple
    exercices_for_template = []
    
    for ex_data in bundle_json.get("exercices", []):
        # Récupérer l'objet ExoPageSimple depuis la base de données
        ex_page = ExoPageSimple.objects.filter(id=ex_data.get("id_page")).first()
        exercices_for_template.append({
            "title": ex_data.get("title", ""),
            "total_points": ex_data.get("total_points", 0),
            "estimated_time_min": ex_data.get("estimated_time_min", 0),
            "difficulty": ex_data.get("difficulty", 0),
            "page": ex_page,  # Objet page pour accéder au contenu
            "param_values": ex_data.get("param_values", {}),  # Paramètres récupérés du service
        })

    ctx = {
        "type": (payload.get("type") or "ds"),
        "seed_effective": str(seed),
        # Graine stable pour tableaux dynamiques dans les templates
        "K": str(seed),
        "__render_seed": int(hashlib.md5(str(seed).encode()).hexdigest()[:8], 16),
        "qcms": qcms_for_template,
        "qa_cards": bundle_json.get("flashcards", []),
        "exercices": exercices_for_template,
        "barreme_cible": bundle_json["meta"].get("barreme_cible"),
        "barreme_total": bundle_json["meta"].get("barreme_obtenu", 0),
        # Paramètres d'activation pour l'affichage
        "ds_qcm_enable": payload.get("ds_qcm_enable", True),
        "ds_qr_enable": payload.get("ds_qr_enable", False),
        "ds_exo_application_enable": payload.get("ds_exo_application_enable", True),
        "ds_exo_entrainement_enable": payload.get("ds_exo_entrainement_enable", True),
        "ds_exo_approfondissement_enable": payload.get("ds_exo_approfondissement_enable", True),
        "ds_qcm_min": payload.get("ds_qcm_min", 0),
        "ds_qcm_max": payload.get("ds_qcm_max", 10),
        "ds_qr_min": payload.get("ds_qr_min", 0),
        "ds_qr_max": payload.get("ds_qr_max", 10),
    }
    return render(request, "generator/qcm_preview.html", ctx)


@require_GET
def qcm_pdf_enonce(request: HttpRequest) -> HttpResponse:
    """Génération PDF énoncé utilisant le bundle en session"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("DEBUG PDF: Fonction qcm_pdf_enonce appelée")
    
    payload, seed = _get_payload_and_seed(request)
    bundle_json = request.session.get("selection_bundle")
    if not bundle_json:
        # reconstruit au besoin
        bundle = build_selection_bundle(payload, seed)
        bundle_json = bundle.to_jsonable()
        request.session["selection_bundle"] = bundle_json
        request.session["selection_seed"] = seed

    # Utiliser la fonction pdf_build existante avec mode="enonce"
    return pdf_build(request, "enonce")


@require_GET
def qcm_pdf_correction(request: HttpRequest) -> HttpResponse:
    """Génération PDF correction utilisant le bundle en session"""
    payload, seed = _get_payload_and_seed(request)
    bundle_json = request.session.get("selection_bundle")
    if not bundle_json:
        # reconstruit au besoin
        bundle = build_selection_bundle(payload, seed)
        bundle_json = bundle.to_jsonable()
        request.session["selection_bundle"] = bundle_json
        request.session["selection_seed"] = seed

    # Utiliser la fonction pdf_build existante avec mode="correction"
    return pdf_build(request, "correction")

