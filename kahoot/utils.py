import random
from typing import List, Dict, Any
from django.db.models import Q

# Import explicite des modèles QCM avec gestion d'erreur
try:
    from qcm.models import QcmQuestionAPage, QcmBankBPage, QcmQuestionCPage
    QCM_AVAILABLE = True
except ImportError:
    QCM_AVAILABLE = False
    QcmQuestionAPage = None
    QcmBankBPage = None
    QcmQuestionCPage = None

try:
    from referentiel.models import Chapitre
    REFERENTIEL_AVAILABLE = True
except ImportError:
    REFERENTIEL_AVAILABLE = False
    Chapitre = None


def extract_options_from_type_a(question: QcmQuestionAPage) -> List[Dict[str, Any]]:
    """
    Extrait et traite les options d'une question Type A.
    Retourne 4 options mélangées (1 correcte + 3 distracteurs).
    """
    opts = list(question.options.all())
    if len(opts) < 4:
        return []
    
    corrects = [o for o in opts if o.is_correct]
    incorrects = [o for o in opts if not o.is_correct]
    
    if not corrects or len(incorrects) < 3:
        return []
    
    correct = random.choice(corrects)
    distractors = random.sample(incorrects, 3)
    
    final_opts = [{"html": o.text, "is_correct": (o == correct)} for o in [correct, *distractors]]
    random.shuffle(final_opts)
    
    return final_opts


def extract_options_from_type_b(bank: QcmBankBPage) -> tuple[List[Dict[str, Any]], str]:
    """
    Extrait et traite les options d'une banque Type B.
    Retourne 4 options mélangées (1 correcte + 3 distracteurs) et l'énoncé.
    """
    variants = list(bank.variants.all())
    if len(variants) < 4:
        return [], ""
    
    correct_var = random.choice(variants)
    other_vars = [v for v in variants if v != correct_var]
    distractors = random.sample(other_vars, 3)
    
    opts = [{"html": correct_var.answer, "is_correct": True}]
    for d in distractors:
        opts.append({"html": d.answer, "is_correct": False})
    random.shuffle(opts)
    
    return opts, correct_var.statement


def extract_options_from_type_c(question: QcmQuestionCPage) -> List[Dict[str, Any]]:
    """
    Extrait et traite les options d'une question Type C.
    Retourne 4 options mélangées (1 correcte + 3 distracteurs).
    """
    correct_answers = question.get_correct_answers_list()
    incorrect_answers = question.get_incorrect_answers_list()
    
    if len(correct_answers) < 1 or len(incorrect_answers) < 3:
        return []
    
    correct = random.choice(correct_answers)
    distractors = random.sample(incorrect_answers, 3)
    
    opts = [{"html": correct, "is_correct": True}]
    for d in distractors:
        opts.append({"html": d, "is_correct": False})
    random.shuffle(opts)
    
    return opts


def select_questions_from_chapters(chapter_ids: List[int], total: int = 10, shuffle: bool = True) -> List[Dict[str, Any]]:
    """
    Sélectionne des questions depuis les chapitres spécifiés.
    Agrége les types A, B et C selon la même logique que l'onglet QCM.
    """
    if not chapter_ids:
        return []
    
    all_questions = []
    
    try:
        # Récupérer les pages de cours correspondant aux chapitres
        from cours.models import CoursPage
        cours_pages = CoursPage.objects.filter(
            chapitre_id__in=chapter_ids
        ).live()
        
        for cours_page in cours_pages:
            # Récupérer les enfants publiés
            children = cours_page.get_children().live().specific()
            
            # ---- TYPE A : Questions complètes ----
            qcm_a = [c for c in children if isinstance(c, QcmQuestionAPage)]
            for q in qcm_a:
                if not q.sans_redaction:  # On ne prend que les QCM sans rédaction
                    continue
                    
                options = extract_options_from_type_a(q)
                if options:
                    # Convertir l'image en URL si elle existe
                    image_url = ""
                    if q.image:
                        try:
                            image_url = q.image.get_rendition('max-400x300').url
                        except:
                            image_url = ""
                    
                    all_questions.append({
                        "type": "A",
                        "statement": q.statement,
                        "image_url": image_url,
                        "video_url": q.video_url or "",
                        "layout": q.layout,
                        "options": options,
                        "explanation": getattr(q, "explanation", "") or "",
                    })
            
            # ---- TYPE B : Banques de variantes ----
            qcm_banks = [c for c in children if isinstance(c, QcmBankBPage)]
            for bank in qcm_banks:
                if not bank.sans_redaction:  # On ne prend que les QCM sans rédaction
                    continue
                    
                options, statement = extract_options_from_type_b(bank)
                if options:
                    all_questions.append({
                        "type": "B",
                        "statement": statement,
                        "image_url": "",  # Type B n'a pas d'image au niveau banque
                        "video_url": "",
                        "layout": "text",
                        "options": options,
                        "explanation": "",
                    })
            
            # ---- TYPE C : Questions avec listes de réponses ----
            qcm_c = [c for c in children if isinstance(c, QcmQuestionCPage)]
            for q in qcm_c:
                if not q.sans_redaction:  # On ne prend que les QCM sans rédaction
                    continue
                    
                options = extract_options_from_type_c(q)
                if options:
                    # Convertir l'image en URL si elle existe
                    image_url = ""
                    if q.image:
                        try:
                            image_url = q.image.get_rendition('max-400x300').url
                        except:
                            image_url = ""
                    
                    all_questions.append({
                        "type": "C",
                        "statement": q.statement,
                        "image_url": image_url,
                        "video_url": q.video_url or "",
                        "layout": q.layout,
                        "options": options,
                        "explanation": getattr(q, "explanation", "") or "",
                    })
        
        # Mélange global si demandé
        if shuffle:
            random.shuffle(all_questions)
        
        # Limite au nombre demandé
        return all_questions[:total]
    except Exception as e:
        print(f"Erreur dans select_questions_from_chapters: {e}")
        return []


def get_available_chapters_by_niveau() -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """
    Retourne la structure hiérarchique : Niveau → Thèmes → Chapitres
    Ne retourne que les chapitres qui ont des QCM.
    """
    try:
        from referentiel.models import Niveau, Theme
        from cours.models import CoursPage
        
        structure = {}
        
        niveaux = Niveau.objects.all().prefetch_related('themes__chapitres')
        
        for niveau in niveaux:
            structure[niveau.nom] = {}
            
            for theme in niveau.themes.all():
                structure[niveau.nom][theme.nom] = []
                
                for chapitre in theme.chapitres.all():
                    # Vérifier si ce chapitre a des QCM
                    cours_page = CoursPage.objects.filter(chapitre=chapitre).live().first()
                    if cours_page:
                        # Compter les QCM dans ce chapitre
                        children = cours_page.get_children().live().specific()
                        qcm_count = 0
                        
                        # Compter les QCM Type A, B et C
                        qcm_a_count = len([c for c in children if hasattr(c, 'options') and c.options.count() >= 4])
                        qcm_b_count = len([c for c in children if hasattr(c, 'variants') and c.variants.count() >= 4])
                        qcm_c_count = len([c for c in children if hasattr(c, 'correct_answers') and c.get_correct_answers_list() and c.get_incorrect_answers_list()])
                        
                        qcm_count = qcm_a_count + qcm_b_count + qcm_c_count
                        
                        if qcm_count > 0:
                            structure[niveau.nom][theme.nom].append({
                                'id': chapitre.id,
                                'numero': chapitre.numero,
                                'titre': chapitre.titre,
                            })
        
        return structure
    except Exception as e:
        print(f"Erreur dans get_available_chapters_by_niveau: {e}")
        return {}

