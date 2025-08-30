from django.shortcuts import render, get_object_or_404
from django.http import Http404, JsonResponse
from wagtail.models import Page
from referentiel.models import Niveau
from .models import CoursRootPage, CoursIndexPage
import random

def cours_root_view(request):
    """Vue pour la page racine des cours"""
    try:
        root_page = CoursRootPage.objects.live().first()
        if not root_page:
            raise Http404("Page des cours non trouvée")
        
        # Récupérer tous les niveaux avec le nombre de cours
        niveaux = []
        for niveau in Niveau.objects.all():
            # Compter les cours pour ce niveau
            cours_count = 0
            for theme in niveau.themes.all():
                for chapitre in theme.chapitres.all():
                    cours_count += chapitre.cours.count()
            
            niveau.cours_count = cours_count
            niveaux.append(niveau)
        
        return render(request, 'cours/cours_root_page.html', {
            'page': root_page,
            'niveaux': niveaux,
        })
    except Exception as e:
        raise Http404(f"Erreur lors du chargement des cours: {e}")

def cours_by_niveau_view(request, niveau_id):
    """Vue pour afficher les cours d'un niveau spécifique"""
    niveau = get_object_or_404(Niveau, id=niveau_id)
    
    # Récupérer tous les cours pour ce niveau
    cours_list = []
    for theme in niveau.themes.all():
        for chapitre in theme.chapitres.all():
            for cours in chapitre.cours.all():
                cours_list.append(cours)
    
    return render(request, 'cours/cours_by_niveau.html', {
        'niveau': niveau,
        'cours_list': cours_list,
    })


def get_chapitres_by_niveau(request, niveau_id):
    """Vue AJAX pour récupérer les chapitres d'un niveau spécifique"""
    from django.http import JsonResponse
    from referentiel.models import Chapitre
    
    try:
        niveau = get_object_or_404(Niveau, id=niveau_id)
        chapitres = Chapitre.objects.filter(theme__niveau=niveau).select_related('theme')
        
        chapitres_data = []
        for chapitre in chapitres:
            chapitres_data.append({
                'id': chapitre.id,
                'titre': f"{chapitre.theme.nom} - {chapitre.numero}. {chapitre.titre}",
                'theme': chapitre.theme.nom,
                'numero': chapitre.numero
            })
        
        return JsonResponse({'chapitres': chapitres_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def get_new_qcm_questions(request, cours_id):
    """Vue AJAX pour obtenir de nouvelles questions QCM"""
    try:
        from cours.models import CoursPage
        from qcm.models import QcmQuestionAPage, QcmBankBPage, QcmQuestionCPage
        
        cours_page = get_object_or_404(CoursPage, id=cours_id)
        
        # Par défaut, on ne génère que les QCM sans rédaction
        include_justification = request.GET.get('justification', 'false').lower() == 'true'
        
        # Récupérer les enfants (publiés) de la CoursPage
        children = cours_page.get_children().live().specific()
        
        # ---- TYPE A : une question = 4 options (1 correcte + 3 distracteurs) ----
        qcm_a = [c for c in children if isinstance(c, QcmQuestionAPage)]
        payload_a = []
        for q in qcm_a:
            # Filtrer selon le paramètre sans_redaction
            if not q.sans_redaction and not include_justification:
                continue
                
            opts = list(q.options.all())
            if len(opts) < 4:
                continue  # on exige 4 propositions min
            corrects = [o for o in opts if o.is_correct]
            incorrects = [o for o in opts if not o.is_correct]
            if not corrects:
                continue

            correct = random.choice(corrects)
            # 3 distracteurs si possible, sinon on saute
            if len(incorrects) < 3:
                continue
            distractors = random.sample(incorrects, 3)

            # pool final et shuffle
            final_opts = [{"html": o.text, "is_correct": (o == correct)} for o in [correct, *distractors]]
            random.shuffle(final_opts)

            payload_a.append({
                "type": "A",
                "statement": q.statement,
                "image": q.image,
                "options": final_opts,
                "explanation": getattr(q, "explanation", ""),
            })

        # ---- TYPE B : piocher 1 variante correcte + 3 distracteurs dans la même banque ----
        qcm_banks = [c for c in children if isinstance(c, QcmBankBPage)]
        payload_b = []
        for bank in qcm_banks:
            # Filtrer selon le paramètre sans_redaction
            if not bank.sans_redaction and not include_justification:
                continue
                
            variants = list(bank.variants.all())
            if len(variants) < 4:
                continue
            correct_var = random.choice(variants)
            other_vars = [v for v in variants if v != correct_var]
            distractors = random.sample(other_vars, 3)

            # Construire options : 1 correcte (answer de correct_var) + 3 distracteurs (answers d'autres variantes)
            opts = [{"html": correct_var.answer, "is_correct": True}]
            for d in distractors:
                opts.append({"html": d.answer, "is_correct": False})
            random.shuffle(opts)

            payload_b.append({
                "type": "B",
                "statement": correct_var.statement,
                "options": opts,
                "explanation": "",
            })

        # ---- TYPE C : 1 bonne réponse + 3 mauvaises réponses depuis les listes ----
        qcm_c = [c for c in children if isinstance(c, QcmQuestionCPage)]
        payload_c = []
        for q in qcm_c:
            # Filtrer selon le paramètre sans_redaction
            if not q.sans_redaction and not include_justification:
                continue
                
            correct_answers = q.get_correct_answers_list()
            incorrect_answers = q.get_incorrect_answers_list()
            
            if len(correct_answers) < 1 or len(incorrect_answers) < 3:
                continue  # on exige au moins 1 bonne réponse et 3 mauvaises
            
            # Choisir 1 bonne réponse au hasard
            correct = random.choice(correct_answers)
            # Choisir 3 mauvaises réponses au hasard
            distractors = random.sample(incorrect_answers, 3)
            
            # Construire les options
            opts = [{"html": correct, "is_correct": True}]
            for d in distractors:
                opts.append({"html": d, "is_correct": False})
            random.shuffle(opts)
            
            payload_c.append({
                "type": "C",
                "statement": q.statement,
                "image": q.image,
                "options": opts,
                "explanation": getattr(q, "explanation", ""),
            })

        # Mélange global + limite 10
        all_q = payload_a + payload_b + payload_c
        random.shuffle(all_q)
        qcm_set = all_q[:10]
        
        # Convertir en HTML pour le rendu
        from django.template.loader import render_to_string
        from django.template import Context
        
        html_content = render_to_string('cours/partials/qcm_viewer.html', {
            'qcm_set': qcm_set
        })
        
        return JsonResponse({
            'success': True,
            'html': html_content,
            'questions_count': len(qcm_set)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
