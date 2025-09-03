"""
Vues pour l'application generateurs.
"""
import json
from io import BytesIO
from django.http import JsonResponse, FileResponse, HttpResponseBadRequest
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from django.template.loader import render_to_string
from django.templatetags.static import static
from wagtail.models import Page
from .models import GenerateursHubPage, DSGeneratorPage, SerieGeneratorPage
from .utils.selectors import generate_ds_content, generate_serie_content
from .utils.pdf import render_tex_to_pdf, get_branding_settings
from .utils.exceptions import LatexCompileError
from .utils import selection as selection_utils
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os

# Playwright (sync)
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def generateurs_hub_page(request):
    """Vue pour la page hub des générateurs"""
    # Créer un objet page virtuel pour le template
    class VirtualPage:
        def __init__(self):
            self.title = "Générateurs"
            self.introduction = "Créez automatiquement des devoirs surveillés et des séries d'exercices personnalisés."
    
    page = VirtualPage()
    
    return render(request, 'generateurs/generateurs_hub_page.html', {
        'page': page,
    })


def ds_generator_page(request):
    """Vue pour la page de génération de devoirs surveillés"""
    # Créer un objet page virtuel pour le template
    class VirtualPage:
        def __init__(self):
            self.title = "Générateur de devoir surveillé"
    
    page = VirtualPage()
    
    # Récupérer les niveaux et chapitres pour le template
    from referentiel.models import Niveau, Chapitre
    
    niveaux = Niveau.objects.all().order_by('nom')
    chapitres = Chapitre.objects.all().select_related('theme__niveau').order_by('theme__niveau__nom', 'theme__nom', 'numero')
    
    return render(request, 'generateurs/ds_generator_page.html', {
        'page': page,
        'niveaux': niveaux,
        'chapitres': chapitres,
    })


def serie_generator_page(request):
    """Vue pour la page de génération de séries d'exercices"""
    # Créer un objet page virtuel pour le template
    class VirtualPage:
        def __init__(self):
            self.title = "Générateur de série d'exercices"
    
    page = VirtualPage()
    
    # Récupérer les niveaux et chapitres pour le template
    from referentiel.models import Niveau, Chapitre
    
    niveaux = Niveau.objects.all().order_by('nom')
    chapitres = Chapitre.objects.all().select_related('theme__niveau').order_by('theme__niveau__nom', 'theme__nom', 'numero')
    
    return render(request, 'generateurs/serie_generator_page.html', {
        'page': page,
        'niveaux': niveaux,
        'chapitres': chapitres,
    })


@csrf_exempt
@require_http_methods(["POST"])
def generate_ds_pdf_view(request):
    """Endpoint pour générer les PDFs d'un devoir surveillé"""
    try:
        data = json.loads(request.body)
        
        # Récupérer les paramètres des 3 étapes
        niveau_id = data.get('niveau_id')
        chapitre_ids = data.get('chapitre_ids', [])
        
        # Étape 2
        titre = data.get('titre', 'Contrôle')
        sous_titre_1 = data.get('sous_titre_1', '')
        sous_titre_2 = data.get('sous_titre_2', '')
        bareme_global = data.get('bareme_global', 20)
        afficher_bareme = data.get('afficher_bareme', True)
        afficher_bareme_par_question = data.get('afficher_bareme_par_question', False)
        afficher_duree_par_exercice = data.get('afficher_duree_par_exercice', True)
        
        # Étape 3
        qcm_min = data.get('qcm_min', 0)
        qcm_max = data.get('qcm_max', 10)
        points_par_qcm = data.get('points_par_qcm', 1.0)
        fc_min = data.get('fc_min', 0)
        fc_max = data.get('fc_max', 10)
        points_par_fc = data.get('points_par_fc', 1.0)
        use_lvl1 = data.get('use_lvl1', True)
        ex_lvl1_min = data.get('ex_lvl1_min', 0)
        ex_lvl1_max = data.get('ex_lvl1_max', 5)
        use_lvl2 = data.get('use_lvl2', True)
        ex_lvl2_min = data.get('ex_lvl2_min', 0)
        ex_lvl2_max = data.get('ex_lvl2_max', 5)
        use_lvl3 = data.get('use_lvl3', True)
        ex_lvl3_min = data.get('ex_lvl3_min', 0)
        ex_lvl3_max = data.get('ex_lvl3_max', 5)
        equilibrer_par_chapitre = data.get('equilibrer_par_chapitre', True)
        
        # Récupérer les objets depuis la base
        from referentiel.models import Niveau, Chapitre
        
        try:
            niveau = Niveau.objects.get(id=niveau_id)
            chapitres = Chapitre.objects.filter(id__in=chapitre_ids)
        except (Niveau.DoesNotExist, Chapitre.DoesNotExist):
            return JsonResponse({'error': 'Niveau ou chapitres non trouvés'}, status=400)
        
        # Préparer les paramètres
        params = {
            'niveau': niveau,
            'chapitres': chapitres,
            'titre': titre,
            'sous_titre_1': sous_titre_1,
            'sous_titre_2': sous_titre_2,
            'bareme_global': bareme_global,
            'afficher_bareme': afficher_bareme,
            'afficher_bareme_par_question': afficher_bareme_par_question,
            'afficher_duree_par_exercice': afficher_duree_par_exercice,
            'qcm_min': qcm_min,
            'qcm_max': qcm_max,
            'points_par_qcm': points_par_qcm,
            'fc_min': fc_min,
            'fc_max': fc_max,
            'points_par_fc': points_par_fc,
            'use_lvl1': use_lvl1,
            'ex_lvl1_min': ex_lvl1_min,
            'ex_lvl1_max': ex_lvl1_max,
            'use_lvl2': use_lvl2,
            'ex_lvl2_min': ex_lvl2_min,
            'ex_lvl2_max': ex_lvl2_max,
            'use_lvl3': use_lvl3,
            'ex_lvl3_min': ex_lvl3_min,
            'ex_lvl3_max': ex_lvl3_max,
            'equilibrer_par_chapitre': equilibrer_par_chapitre,
        }
        
        # Générer le contenu
        content_data = generate_ds_content(params)
        
        # Fusionner exercices et questions de cours en une seule liste
        content = content_data['exercices'] + content_data['questions_cours']
        
        # Contexte commun pour LaTeX
        ctx = {
            'content': content,
            'params': params,
            'branding': get_branding_settings(),
        }

        # Générer enonce
        enonce_pdf_path, enonce_dir = render_tex_to_pdf("generateurs/pdf/enonce.tex", ctx)
        with open(enonce_pdf_path, 'rb') as f:
            enonce_name = f"generateurs/enonce_{os.path.basename(enonce_dir)}.pdf"
            enonce_saved = default_storage.save(enonce_name, ContentFile(f.read()))
        enonce_url = f"{settings.MEDIA_URL}{enonce_saved}"

        # Générer correction
        corr_pdf_path, corr_dir = render_tex_to_pdf("generateurs/pdf/correction.tex", ctx)
        with open(corr_pdf_path, 'rb') as f:
            corr_name = f"generateurs/correction_{os.path.basename(corr_dir)}.pdf"
            corr_saved = default_storage.save(corr_name, ContentFile(f.read()))
        corr_url = f"{settings.MEDIA_URL}{corr_saved}"

        return JsonResponse({'success': True, 'enonce_url': enonce_url, 'correction_url': corr_url})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Données JSON invalides'}, status=400)
    except LatexCompileError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Erreur lors de la génération: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def generate_serie_pdf_view(request):
    """Endpoint pour générer le PDF d'une série d'exercices"""
    try:
        data = json.loads(request.body)
        
        # Récupérer les paramètres
        niveau_id = data.get('niveau_id')
        chapitre_ids = data.get('chapitre_ids', [])
        titre = data.get('titre', 'Série d\'exercices')
        sous_titre_1 = data.get('sous_titre_1', '')
        sous_titre_2 = data.get('sous_titre_2', '')
        nb_qcm = data.get('nb_qcm', 0)
        nb_fc = data.get('nb_fc', 0)
        nb_ex_lvl1 = data.get('nb_ex_lvl1', 0)
        nb_ex_lvl2 = data.get('nb_ex_lvl2', 0)
        nb_ex_lvl3 = data.get('nb_ex_lvl3', 0)
        equilibrer_par_chapitre = data.get('equilibrer_par_chapitre', True)
        
        # Récupérer les objets depuis la base
        from referentiel.models import Niveau, Chapitre
        
        try:
            niveau = Niveau.objects.get(id=niveau_id)
            chapitres = Chapitre.objects.filter(id__in=chapitre_ids)
        except (Niveau.DoesNotExist, Chapitre.DoesNotExist):
            return JsonResponse({'error': 'Niveau ou chapitres non trouvés'}, status=400)
        
        # Préparer les paramètres
        params = {
            'niveau': niveau,
            'chapitres': chapitres,
            'titre': titre,
            'sous_titre_1': sous_titre_1,
            'sous_titre_2': sous_titre_2,
            'nb_qcm': nb_qcm,
            'nb_fc': nb_fc,
            'nb_ex_lvl1': nb_ex_lvl1,
            'nb_ex_lvl2': nb_ex_lvl2,
            'nb_ex_lvl3': nb_ex_lvl3,
            'equilibrer_par_chapitre': equilibrer_par_chapitre,
        }
        
        # Générer le contenu
        content_data = generate_serie_content(params)
        
        # Fusionner exercices et questions de cours en une seule liste
        content = content_data['exercices'] + content_data['questions_cours']
        
        # Contexte commun
        ctx = {
            'content': content,
            'params': params,
            'branding': get_branding_settings(),
        }

        # Générer l'énoncé
        enonce_pdf_path, enonce_dir = render_tex_to_pdf("generateurs/pdf/serie_enonce.tex", ctx)
        with open(enonce_pdf_path, 'rb') as f:
            enonce_name = f"generateurs/serie_{os.path.basename(enonce_dir)}.pdf"
            enonce_saved = default_storage.save(enonce_name, ContentFile(f.read()))
        enonce_url = f"{settings.MEDIA_URL}{enonce_saved}"

        return JsonResponse({'success': True, 'enonce_url': enonce_url})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Données JSON invalides'}, status=400)
    except LatexCompileError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Erreur lors de la génération: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_branding_settings(request):
    """Endpoint pour mettre à jour les paramètres de marque"""
    try:
        data = json.loads(request.body)
        
        from .models import DSBrandingSettings
        
        settings, created = DSBrandingSettings.objects.get_or_create()
        
        if 'logo_id' in data:
            from wagtail.images.models import Image
            try:
                logo = Image.objects.get(id=data['logo_id'])
                settings.logo = logo
            except Image.DoesNotExist:
                settings.logo = None
        
        if 'ecole_l1' in data:
            settings.ecole_l1 = data['ecole_l1']
        if 'ecole_l2' in data:
            settings.ecole_l2 = data['ecole_l2']
        if 'ecole_l3' in data:
            settings.ecole_l3 = data['ecole_l3']
        
        settings.save()
        
        return JsonResponse({'success': True})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Données JSON invalides'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Erreur lors de la mise à jour: {str(e)}'}, status=500)


@csrf_exempt
def build_pdf_from_selection(request):
    """Endpoint pour générer un PDF à partir de la sélection avec Playwright"""
    try:
        if request.method != "POST":
            return HttpResponseBadRequest("POST expected")

        if not PLAYWRIGHT_AVAILABLE:
            return HttpResponseBadRequest("Playwright non disponible")

        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return HttpResponseBadRequest("Invalid JSON")

        # 1) Reconstituer le contexte à partir de LA SÉLECTION EXISTANTE
        selection_ctx = selection_utils.build_selection_context(payload)

        # 2) Contexte d'affichage (brandings, titres, barème, options d'entête)
        branding = payload.get("branding", {})  # ecole_l1, l2, l3, logo, etc.
        header = {
            "titre": payload.get("titre", "Contrôle"),
            "sous_titre_1": payload.get("sous_titre_1", ""),
            "sous_titre_2": payload.get("sous_titre_2", ""),
            "bareme_global": payload.get("bareme_global", 20),
            "show_sommaire": payload.get("show_sommaire", True),
            "show_bareme_per_exo": payload.get("show_bareme_per_exo", True),
            "show_duree_per_exo": payload.get("show_duree_per_exo", True),
        }

        # URL absolue vers Tailwind (pour que Chromium puisse le charger)
        try:
            tailwind_url = request.build_absolute_uri(static('css/tailwind.css'))
        except Exception:
            tailwind_url = request.build_absolute_uri('/static/css/tailwind.css')

        # URL d'origine (pour <base href> afin de résoudre /media, /static)
        origin_url = request.build_absolute_uri('/')

        context = {
            "branding": branding,
            "header": header,
            "tailwind_url": tailwind_url,
            "origin_url": origin_url,
            # IMPORTANT: ces listes/vues sont celles que tes écrans produisent déjà
            "qcms": selection_ctx.get("qcms", []),
            "flashcards": selection_ctx.get("flashcards", []),
            "exercices": selection_ctx.get("exercices", []),
            "sommaire": selection_ctx.get("sommaire", []),
            "options": selection_ctx.get("options", {}),
        }

        # Sécurité: au moins un contenu
        if not (context["exercices"] or context["qcms"] or context["flashcards"]):
            return HttpResponseBadRequest("Aucun contenu à imprimer")

        # 3) Render HTML (énoncé)
        html_enonce = render_to_string("generateurs/pdf/print_enonce.html", context=context, request=request)
        pdf_enonce = html_to_pdf_with_playwright(html_enonce)

        # 4) Render HTML (correction)
        html_correction = render_to_string("generateurs/pdf/print_correction.html", context=context, request=request)
        pdf_correction = html_to_pdf_with_playwright(html_correction)

        # Par défaut, renvoyer l'énoncé; côté UI on peut appeler 2 fois si besoin.
        # Ici, on regroupe dans un ZIP serait possible; pour la simplicité on renvoie l'énoncé.
        return FileResponse(
            BytesIO(pdf_enonce),
            as_attachment=True,
            filename="enonce.pdf",
            content_type="application/pdf",
        )
    except Exception as e:
        # Renvoyer une erreur lisible côté JS
        return HttpResponseBadRequest(f"Erreur PDF: {e}")


def html_to_pdf_with_playwright(html: str) -> bytes:
    """Rend un HTML arbitraire (inline) en PDF avec Chromium.
    - Injecte le HTML via data URL
    - Attend la fin de MathJax (typesetPromise)
    - Media print + A4 portrait + marges
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context()
        page = context.new_page()

        # Logs réseau (debug du chargement CSS)
        page.on("requestfailed", lambda r: print("[PW] FAIL", r.url, r.failure))
        page.on("response", lambda resp: print("[PW] RESP", resp.status, resp.url) if "tailwind.css" in resp.url else None)

        page.set_default_timeout(120_000)
        # Charger le HTML; Tailwind/MathJax se chargent ensuite
        page.set_content(html, wait_until="domcontentloaded", timeout=60_000)

        # Attendre MathJax (typesetPromise)
        page.evaluate(
            """() => new Promise((resolve) => {
                const mj = window.MathJax;
                if (mj && mj.typesetPromise) {
                    mj.typesetPromise().then(() => setTimeout(resolve, 150)).catch(() => resolve());
                } else {
                    setTimeout(resolve, 100);
                }
            })"""
        )

        page.emulate_media(media="print")
        pdf = page.pdf(format="A4", margin={"top": "15mm", "right": "15mm", "bottom": "15mm", "left": "15mm"}, print_background=True)
        browser.close()
        return pdf

