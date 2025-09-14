# generator/services/selection.py
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Set, Tuple
import hashlib, random, re

# Imports des modèles Wagtail
from wagtail.models import Page
from qcm.models import QcmQuestionAPage, QcmBankBPage, QcmQuestionCPage
from flashcard.models import FlashcardItem, FlashcardSetPage
from exo.models import ExoPageSimple

_html_tag_re = re.compile(r"<[^>]+>")

def _canon_html(s: str) -> str:
    """Normalise HTML pour clés de variante stables"""
    if not s:
        return ""
    # retire balises + normalise espaces pour clefs stables
    t = _html_tag_re.sub("", s).strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t

@dataclass
class QcmItem:
    id_page: int
    type_qcm: str  # "A"|"B"|"C"
    variant_key: str
    statement_html: str
    media: List[str]
    options: List[str]  # A..D HTML
    correct_index: int  # 1..4
    correct_letter: str # "A".."D"
    correct_text: str
    explanation_html: Optional[str] = None
    points: float = 1.0

@dataclass
class QaItem:
    id_card: int
    question_html: str
    answer_html: str
    media: List[str] = field(default_factory=list)
    points: Optional[float] = None

@dataclass
class ExoItem:
    id_page: int
    title: str
    difficulty: Optional[int]
    estimated_time_min: Optional[int]
    total_points: float
    statement_html: Optional[str] = None
    correction_html: Optional[str] = None
    param_values: Dict[str, Any] = field(default_factory=dict)
    media: List[str] = field(default_factory=list)

@dataclass
class SelectionBundle:
    seed_effective: str
    type: str  # "ds"|"serie"
    meta: Dict[str, Any]
    qcms: List[QcmItem] = field(default_factory=list)
    flashcards: List[QaItem] = field(default_factory=list)
    exercices: List[ExoItem] = field(default_factory=list)

    def to_jsonable(self) -> Dict[str, Any]:
        return {
            "seed_effective": self.seed_effective,
            "type": self.type,
            "meta": self.meta,
            "qcms": [asdict(x) for x in self.qcms],
            "flashcards": [asdict(x) for x in self.flashcards],
            "exercices": [asdict(x) for x in self.exercices],
        }

_letters = ("A","B","C","D")

def _variant_key_for_qcmA(page_id: int, statement: str, options: List[str], correct_index: int) -> str:
    """Clé de variante stable pour QCM A"""
    canon_opts = "|".join(_canon_html(o) for o in options)
    base = f"A|{page_id}|{_canon_html(statement)}|{canon_opts}|{correct_index}"
    return hashlib.sha1(base.encode()).hexdigest()[:16]

def _variant_key_for_qcmB(page_id: int, variant_id: Optional[str], statement: str, options: List[str]) -> str:
    """Clé de variante stable pour QCM B"""
    canon_opts = "|".join(_canon_html(o) for o in options)
    base = f"B|{page_id}|{variant_id or ''}|{_canon_html(statement)}|{canon_opts}"
    return hashlib.sha1(base.encode()).hexdigest()[:16]

def _variant_key_for_qcmC(page_id: int, variant_id: Optional[str], statement: str) -> str:
    """Clé de variante stable pour QCM C"""
    base = f"C|{page_id}|{variant_id or ''}|{_canon_html(statement)}"
    return hashlib.sha1(base.encode()).hexdigest()[:16]

def _rng_from_seed(base_seed: str, *parts: str) -> random.Random:
    """Générateur déterministe basé sur seed + parties"""
    seed_str = f"{base_seed}-" + "-".join(map(str, parts))
    return random.Random(seed_str)

def _is_true(value) -> bool:
    """Helper pour convertir string/boolean en bool"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    return bool(value)

def build_selection_bundle(payload: Dict[str, Any], seed: str) -> SelectionBundle:
    """
    SELECTION CORE: Reprend la logique actuelle (views.qcm_preview lignes ~167-414) mais
    en l'encapsulant ici. Respecte min/max + barème (mode DS) OU compte fixe (mode Série).
    Filtre chapitres si fournis. **Supprime doublons de variantes**.
    """
    rng = random.Random(str(seed))
    type_ds = (payload.get("type") or "ds").strip().lower()
    chapitre_ids = payload.get("chapitre_ids") or []
    meta: Dict[str, Any] = {
        "chapitre_ids": chapitre_ids,
        "barreme_cible": float(payload.get("bareme_global", 20)),
        "params": {k: payload.get(k) for k in payload.keys()},
    }
    
    # Vérification qu'au moins un type est activé
    qcm_enabled = _is_true(payload.get("ds_qcm_enable", True))
    qr_enabled = _is_true(payload.get("ds_qr_enable", False))
    exo_app_enabled = _is_true(payload.get("ds_exo_application_enable", True))
    exo_ent_enabled = _is_true(payload.get("ds_exo_entrainement_enable", True))
    exo_appf_enabled = _is_true(payload.get("ds_exo_approfondissement_enable", True))
    
    if not any([qcm_enabled, qr_enabled, exo_app_enabled, exo_ent_enabled, exo_appf_enabled]):
        raise ValueError("Veuillez choisir au moins un type d'exercices (QCM, QR, ou Exercices)")
    
    # Paramètres de base
    barreme_cible = float(payload.get("bareme_global", 20))
    qcm_point = float(payload.get("ds_qcm_point", 1))
    qr_point = float(payload.get("ds_qr_point", 1))

    # === Récupération pools existants ===
    qcms: List[QcmItem] = []
    qa_cards: List[QaItem] = []
    exercices: List[ExoItem] = []

    # QCM A - Logique déterministe avec déduplication
    qcm_a_pages = []
    
    if chapitre_ids:
        # Filtrer par chapitres spécifiés
        from cours.models import CoursPage
        cours_pages = CoursPage.objects.filter(chapitre__id__in=chapitre_ids).live()
        for cours_page in cours_pages:
            qcm_a_pages.extend(cours_page.get_children().type(QcmQuestionAPage).live().specific())
    else:
        # Tous les QCM A
        qcm_a_pages = list(QcmQuestionAPage.objects.live().specific())
    
    for q in qcm_a_pages:
        opts = list(q.options.all())
        if len(opts) >= 4:
            corrects = [o for o in opts if o.is_correct]
            incorrects = [o for o in opts if not o.is_correct]
            if len(corrects) >= 1 and len(incorrects) >= 3:
                rng_qcm = _rng_from_seed(seed, f"QA-{q.id}")
                correct = rng_qcm.choice(corrects)
                distractors = rng_qcm.sample(incorrects, 3)
                pool = [correct, *distractors]
                rng_qcm.shuffle(pool)
                options_html = [o.text for o in pool]
                correct_index = pool.index(correct) + 1
                
                # Sélectionner UN SEUL énoncé parmi tous les énoncés disponibles
                statements = list(q.statements.all())
                if not statements:
                    continue  # Pas d'énoncés, on saute
                    
                # Choisir un énoncé au hasard
                statement = rng_qcm.choice(statements)
                variant_key = _variant_key_for_qcmA(q.id, statement.statement, options_html, correct_index)
                qcms.append(QcmItem(
                    id_page=q.id,
                    type_qcm="A",
                    variant_key=variant_key,
                    statement_html=statement.statement,
                    media=[statement.image.id] if hasattr(statement, 'image') and statement.image else [],
                    options=options_html[:4],
                    correct_index=correct_index,
                    correct_letter=_letters[correct_index - 1],
                    correct_text=options_html[correct_index - 1],
                    points=float(payload.get("ds_qcm_point", 1)),
                ))

    # QCM B - Logique déterministe avec déduplication
    qcm_b_pages = []
    
    if chapitre_ids:
        # Filtrer par chapitres spécifiés
        from cours.models import CoursPage
        cours_pages = CoursPage.objects.filter(chapitre__id__in=chapitre_ids).live()
        for cours_page in cours_pages:
            qcm_b_pages.extend(cours_page.get_children().type(QcmBankBPage).live().specific())
    else:
        # Tous les QCM B
        qcm_b_pages = list(QcmBankBPage.objects.live().specific())
    
    for q in qcm_b_pages:
        variants = list(q.variants.all())
        if len(variants) >= 4:
            rng_qcm = _rng_from_seed(seed, f"QB-{q.id}")
            correct = rng_qcm.choice(variants)
            others = [v for v in variants if v != correct]
            if len(others) >= 3:
                distractors = rng_qcm.sample(others, 3)
                pool = [correct.answer] + [d.answer for d in distractors]
                rng_qcm.shuffle(pool)
                correct_index = pool.index(correct.answer) + 1
                
                variant_key = _variant_key_for_qcmB(q.id, None, correct.statement, pool)
                qcms.append(QcmItem(
                    id_page=q.id,
                    type_qcm="B",
                    variant_key=variant_key,
                    statement_html=correct.statement,
                    media=[correct.image.id] if hasattr(correct, 'image') and correct.image else [],
                    options=pool[:4],
                    correct_index=correct_index,
                    correct_letter=_letters[correct_index - 1],
                    correct_text=pool[correct_index - 1],
                    points=float(payload.get("ds_qcm_point", 1)),
                ))

    # QCM C - Logique déterministe avec déduplication
    qcm_c_pages = []
    
    if chapitre_ids:
        # Filtrer par chapitres spécifiés
        from cours.models import CoursPage
        cours_pages = CoursPage.objects.filter(chapitre__id__in=chapitre_ids).live()
        for cours_page in cours_pages:
            qcm_c_pages.extend(cours_page.get_children().type(QcmQuestionCPage).live().specific())
    else:
        # Tous les QCM C
        qcm_c_pages = list(QcmQuestionCPage.objects.live().specific())
    
    for q in qcm_c_pages:
        correct_answers = q.get_correct_answers_list()
        incorrect_answers = q.get_incorrect_answers_list()
        if len(correct_answers) >= 1 and len(incorrect_answers) >= 3:
            rng_qcm = _rng_from_seed(seed, f"QC-{q.id}")
            correct = rng_qcm.choice(correct_answers)
            distractors = rng_qcm.sample(incorrect_answers, 3)
            pool = [correct, *distractors]
            rng_qcm.shuffle(pool)
            correct_index = pool.index(correct) + 1
            
            variant_key = _variant_key_for_qcmC(q.id, None, q.statement)
            qcms.append(QcmItem(
                id_page=q.id,
                type_qcm="C",
                variant_key=variant_key,
                statement_html=q.statement,
                media=[q.image.id] if hasattr(q, 'image') and q.image else [],
                options=pool[:4],
                correct_index=correct_index,
                correct_letter=_letters[correct_index - 1],
                correct_text=pool[correct_index - 1],
                points=float(payload.get("ds_qcm_point", 1)),
            ))

    # Flashcards - Logique déterministe avec déduplication
    flashcard_items = []
    
    if chapitre_ids:
        # Filtrer par chapitres spécifiés
        from cours.models import CoursPage
        from flashcard.models import FlashcardSetPage
        cours_pages = CoursPage.objects.filter(chapitre_id__in=chapitre_ids).live()
        for cours_page in cours_pages:
            flashcard_sets = cours_page.get_children().type(FlashcardSetPage).live().specific()
            for flashcard_set in flashcard_sets:
                flashcard_items.extend(flashcard_set.cards.all())
    else:
        # Toutes les flashcards
        flashcard_items = list(FlashcardItem.objects.all())
    
    for fc in flashcard_items:
        rng_fc = _rng_from_seed(seed, f"FC-{fc.id}")
        
        # Générer le HTML de la question avec l'image si présente
        question_html = fc.question
        if fc.image:
            # Ajouter l'image au HTML de la question
            image_url = fc.image.file.url
            question_html += f'<br><img src="{image_url}" alt="Image" style="max-width:100%;height:auto;" />'
        
        qa_cards.append(QaItem(
            id_card=fc.id,
            question_html=question_html,
            answer_html=fc.answer,
            media=[fc.image.id] if fc.image else [],
            points=float(payload.get("ds_qr_point", 1)),
        ))

    # Exercices - Logique déterministe
    exo_pages = []
    
    if chapitre_ids:
        # Filtrer par chapitres spécifiés
        from cours.models import CoursPage
        from exo.models import ExoHubPage
        cours_pages = CoursPage.objects.filter(chapitre_id__in=chapitre_ids).live()
        for cours_page in cours_pages:
            # Chercher les exercices directement sous la CoursPage
            exo_pages.extend(cours_page.get_children().type(ExoPageSimple).live().specific())
            # Chercher les exercices sous les ExoHubPage
            for hub in cours_page.get_children().type(ExoHubPage).live().specific():
                exo_pages.extend(hub.get_children().type(ExoPageSimple).live().specific())
        
        # Ne pas inclure d'exercices d'autres chapitres si aucun n'est trouvé dans les chapitres sélectionnés
        # if not exo_pages:
        #     exo_pages = list(ExoPageSimple.objects.live().specific())
    else:
        # Tous les exercices (comportement par défaut)
        exo_pages = list(ExoPageSimple.objects.live().specific())
    
    for ex in exo_pages:
        # Récupérer les paramètres de l'exercice
        param_values = {}
        try:
            from exo.models import ParametreExoPage
            params_page = ex.get_children().type(ParametreExoPage).specific().first()
            if params_page:
                # Utiliser un seed déterministe pour cet exercice
                ex_seed = f"{seed}-exo-{ex.id}"
                param_values = params_page.build_random_context(seed=ex_seed)
        except Exception:
            param_values = {}
        
        # Rendre le contenu du StreamField avec les paramètres
        statement_html = ""
        if ex.contenu:
            from django.template import Context
            context = Context({
                'page': ex,
                'param_values': param_values,
            })
            for block in ex.contenu:
                try:
                    rendered_block = block.render(context)
                    statement_html += rendered_block
                except Exception:
                    statement_html += str(block.value)

        exo_item = ExoItem(
            id_page=ex.id,
            title=ex.title,
            difficulty=getattr(ex, 'difficulty', None),
            estimated_time_min=getattr(ex, 'estimated_time_min', None),
            total_points=float(ex.total_points or 1),  # Utilise le barème réel de l'exercice depuis Wagtail
            statement_html=statement_html,
            correction_html="",
            param_values=param_values,
        )
        exercices.append(exo_item)

    # DEDUPE: Suppression des doublons de variantes
    seen: Set[str] = set()
    qcms_dedup: List[QcmItem] = []
    for q in qcms:
        if q.variant_key in seen:
            continue
        seen.add(q.variant_key)
        qcms_dedup.append(q)
    qcms = qcms_dedup

    # === NOUVELLE LOGIQUE DE SÉLECTION ===
    
    if type_ds == "ds":
        selected_qcms = []
        selected_flashcards = []
        selected_exercices = []
        barreme_obtenu = 0.0
        
        # 1. Sélectionner les minimums (QCM + QR)
        if qcm_enabled:
            min_qcm = int(payload.get("ds_qcm_min", 0))
            if min_qcm > 0 and qcms:
                selected_qcms = rng.sample(qcms, min(min_qcm, len(qcms)))
                barreme_obtenu += len(selected_qcms) * qcm_point
        
        if qr_enabled:
            min_qr = int(payload.get("ds_qr_min", 0))
            if min_qr > 0 and qa_cards:
                selected_flashcards = rng.sample(qa_cards, min(min_qr, len(qa_cards)))
                barreme_obtenu += len(selected_flashcards) * qr_point
        
        # 2. Calculer le barème restant
        barreme_restant = barreme_cible - barreme_obtenu
        
        # 3. Sélectionner des exercices avec le barème restant
        if barreme_restant > 0 and any([exo_app_enabled, exo_ent_enabled, exo_appf_enabled]):
            # Filtrer les exercices selon les types activés
            exercices_disponibles = []
            for ex in exercices:
                if ex.difficulty == 1 and exo_app_enabled:
                    exercices_disponibles.append(ex)
                elif ex.difficulty == 2 and exo_ent_enabled:
                    exercices_disponibles.append(ex)
                elif ex.difficulty == 3 and exo_appf_enabled:
                    exercices_disponibles.append(ex)
            
            # Sélectionner un maximum d'exercices avec le barème restant
            rng.shuffle(exercices_disponibles)
            barreme_exercices = 0.0
            
            for ex in exercices_disponibles:
                if barreme_exercices + ex.total_points <= barreme_restant:
                    selected_exercices.append(ex)
                    barreme_exercices += ex.total_points
                    if barreme_exercices >= barreme_restant:
                        break
            
            barreme_obtenu += barreme_exercices
            barreme_restant = barreme_cible - barreme_obtenu
        
        # 4. Compléter avec QCM/QR si nécessaire
        if barreme_restant > 0:
            # Compléter avec QCM si activé et disponible
            if qcm_enabled and barreme_restant >= qcm_point:
                max_qcm = int(payload.get("ds_qcm_max", 10))
                qcms_disponibles = [q for q in qcms if q not in selected_qcms]
                
                while (len(selected_qcms) < max_qcm and 
                       qcms_disponibles and 
                       barreme_restant >= qcm_point):
                    qcm = rng.choice(qcms_disponibles)
                    selected_qcms.append(qcm)
                    qcms_disponibles.remove(qcm)
                    barreme_obtenu += qcm_point
                    barreme_restant -= qcm_point
            
            # Compléter avec QR si activé et disponible
            if qr_enabled and barreme_restant >= qr_point:
                max_qr = int(payload.get("ds_qr_max", 10))
                qr_disponibles = [q for q in qa_cards if q not in selected_flashcards]
                
                while (len(selected_flashcards) < max_qr and 
                       qr_disponibles and 
                       barreme_restant >= qr_point):
                    qr = rng.choice(qr_disponibles)
                    selected_flashcards.append(qr)
                    qr_disponibles.remove(qr)
                    barreme_obtenu += qr_point
                    barreme_restant -= qr_point
        
        # 5. Ajuster le barème cible si impossible d'atteindre l'objectif
        if barreme_obtenu < barreme_cible:
            barreme_cible = barreme_obtenu
        
        qcms = selected_qcms
        qa_cards = selected_flashcards
        exercices = selected_exercices

    # Calculer le barème obtenu final
    barreme_obtenu = sum(q.points for q in qcms) + sum(f.points for f in qa_cards) + sum(e.total_points for e in exercices)
    meta["barreme_cible"] = barreme_cible  # Mettre à jour le barème cible (peut être ajusté)
    meta["barreme_obtenu"] = barreme_obtenu
    meta["qcm_count"] = len(qcms)
    meta["qr_count"] = len(qa_cards)
    meta["exo_count"] = len(exercices)

    bundle = SelectionBundle(
        seed_effective=str(seed),
        type=type_ds,
        meta=meta,
        qcms=qcms,
        flashcards=qa_cards,
        exercices=exercices,
    )
    return bundle
