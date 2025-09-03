"""
Module de sélection automatique des contenus pour les générateurs.
Utilise les fonctions existantes des apps qcm, flashcard et exo.
"""
import random
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from django.db.models import Q

# Constantes pour durée indicative
QCM_MIN_PER_ITEM = 1
FC_MIN_PER_ITEM = 1 

class ContentSelector:
    """Sélecteur de contenu pour les générateurs - utilise les fonctions existantes"""
    
    def __init__(self, chapitres, niveau, rng: random.Random | None = None):
        # chapitres peut être une liste de CoursPage ou de Chapitre
        # Normaliser pour avoir les objets Chapitre
        self.chapitres = []
        for chapitre in chapitres:
            if hasattr(chapitre, 'chapitre'):
                # C'est un CoursPage, récupérer le chapitre
                self.chapitres.append(chapitre.chapitre)
            else:
                # C'est déjà un Chapitre
                self.chapitres.append(chapitre)
        
        self.niveau = niveau
        self.rng = rng or random.Random()
        self.chapitre_ids = [c.id for c in self.chapitres]
        
    def get_exercices_by_level(self, level: int) -> List[Dict[str, Any]]:
        """Récupère les exercices d'un niveau donné filtrés par chapitres"""
        from exo.models import ExoPageSimple
        
        # Récupérer tous les exercices du niveau demandé
        exercices = ExoPageSimple.objects.filter(difficulty=level).specific()
        
        result = []
        for exo in exercices:
            # Vérifier si l'exercice appartient à un chapitre sélectionné
            try:
                # Naviguer dans la hiérarchie : ExoPageSimple → ExoHubPage → CoursPage → chapitre
                parent = exo.get_parent()
                if parent and hasattr(parent, 'get_parent'):
                    grand_parent = parent.get_parent()
                    if grand_parent:
                        grand_parent_specific = getattr(grand_parent, 'specific', grand_parent)
                        if hasattr(grand_parent_specific, 'chapitre') and grand_parent_specific.chapitre in self.chapitres:
                            result.append({
                                'type': 'exercice',
                                'niveau': level,
                                'exo_id': exo.id,
                                'titre': exo.title,
                                'points': float(exo.total_points),
                                'duree': exo.estimated_time_min,
                                'enonce': self._extract_enonce(exo),
                                'correction': self._extract_correction(exo),
                                'chapitre': grand_parent_specific.chapitre,
                            })
            except Exception as e:
                # Ignorer les exercices avec des relations cassées
                print(f"Erreur avec l'exercice {exo.id}: {e}")
                continue
        
        return result
    
    def _extract_enonce(self, exo) -> str:
        """Extrait l'énoncé d'un exercice"""
        enonce_parts = []
        for block in exo.contenu:
            if block.block_type == 'enonce':
                enonce_parts.append(str(block.value))
            elif block.block_type in ['s100', 's50_50', 's70_30']:
                if hasattr(block.value, 'get'):
                    content = block.value.get('content', '')
                    if content:
                        enonce_parts.append(str(content))
        
        return '\n\n'.join(enonce_parts) if enonce_parts else "Énoncé de l'exercice"
    
    def _extract_correction(self, exo) -> str:
        """Extrait la correction d'un exercice"""
        correction_parts = []
        for block in exo.contenu:
            if block.block_type == 'question':
                if hasattr(block.value, 'get'):
                    correction = block.value.get('correction', '')
                    if correction:
                        correction_parts.append(str(correction))
        
        return '\n\n'.join(correction_parts) if correction_parts else "Correction de l'exercice"
    
    def get_qcm_pool(self) -> List[Dict[str, Any]]:
        """Construit le pool de QCM depuis l'app qcm en reproduisant la logique des types A/B/C."""
        from qcm.models import QcmQuestionAPage, QcmQuestionCPage
        try:
            from qcm.models import QcmBankBPage
        except Exception:  # app sans type B
            QcmBankBPage = None
        
        result = []
        
        # QCM Type A
        qcm_a_list = QcmQuestionAPage.objects.all()
        for qcm in qcm_a_list:
            try:
                parent = qcm.get_parent()
                if parent and hasattr(parent, 'specific'):
                    parent_specific = parent.specific
                    if hasattr(parent_specific, 'chapitre') and parent_specific.chapitre in self.chapitres:
                        # Reproduire logique: 1 bonne + 3 distracteurs, puis shuffle
                        opts = list(qcm.options.all())
                        if len(opts) < 4:
                            continue
                        corrects = [o for o in opts if o.is_correct]
                        incorrects = [o for o in opts if not o.is_correct]
                        if not corrects or len(incorrects) < 3:
                            continue
                        import random as _rnd
                        correct = self.rng.choice(corrects)
                        distractors = self.rng.sample(incorrects, 3)
                        final_opts = [{"html": str(o.text), "is_correct": (o == correct)} for o in [correct, *distractors]]
                        self.rng.shuffle(final_opts)

                        result.append({
                            'type': 'qcm_a',
                            'titre': qcm.title,
                            'enonce': str(qcm.statement),
                            'options': final_opts,
                            'explanation': str(getattr(qcm, 'explanation', '') or ''),
                            'chapitre': parent_specific.chapitre,
                        })
            except Exception as e:
                print(f"Erreur avec le QCM A {qcm.id}: {e}")
                continue
        
        # QCM Type B (banques et variantes)
        if QcmBankBPage is not None:
            b_list = QcmBankBPage.objects.all()
            for bank in b_list:
                try:
                    parent = bank.get_parent()
                    if parent and hasattr(parent, 'specific'):
                        parent_specific = parent.specific
                        if hasattr(parent_specific, 'chapitre') and parent_specific.chapitre in self.chapitres:
                            variants = list(bank.variants.all())
                            if len(variants) < 4:
                                continue
                            import random as _rnd
                            correct_var = self.rng.choice(variants)
                            other_vars = [v for v in variants if v != correct_var]
                            distractors = self.rng.sample(other_vars, 3)
                            opts = [{"html": str(correct_var.answer), "is_correct": True}]
                            for d in distractors:
                                opts.append({"html": str(d.answer), "is_correct": False})
                            self.rng.shuffle(opts)

                            result.append({
                                'type': 'qcm_b',
                                'titre': bank.title,
                                'enonce': str(correct_var.statement),
                                'options': opts,
                                'explanation': '',
                                'chapitre': parent_specific.chapitre,
                            })
                except Exception as e:
                    print(f"Erreur avec le QCM B {getattr(bank, 'id', '?')}: {e}")
                    continue

        # QCM Type C
        qcm_c_list = QcmQuestionCPage.objects.all()
        for qcm in qcm_c_list:
            try:
                parent = qcm.get_parent()
                if parent and hasattr(parent, 'specific'):
                    parent_specific = parent.specific
                    if hasattr(parent_specific, 'chapitre') and parent_specific.chapitre in self.chapitres:
                        # Construire options: 1 bonne parmi correct_answers + 3 mauvaises parmi incorrect_answers
                        corrects = [r.strip() for r in (qcm.correct_answers or '').split(';') if r.strip()]
                        incorrects = [r.strip() for r in (qcm.incorrect_answers or '').split(';') if r.strip()]
                        if not corrects or len(incorrects) < 3:
                            continue
                        import random as _rnd
                        good = self.rng.choice(corrects)
                        distractors = self.rng.sample(incorrects, 3)
                        opts = [{"html": str(good), "is_correct": True}] + [{"html": str(d), "is_correct": False} for d in distractors]
                        self.rng.shuffle(opts)
                        result.append({
                            'type': 'qcm_c',
                            'titre': qcm.title,
                            'enonce': str(qcm.statement),
                            'options': opts,
                            'chapitre': parent_specific.chapitre,
                        })
            except Exception as e:
                print(f"Erreur avec le QCM C {qcm.id}: {e}")
                continue
        
        return result
    
    def get_fc_pool(self) -> List[Dict[str, Any]]:
        """Construit le pool de flashcards depuis l'app flashcard + cours + exercices (avec variantes)."""
        from flashcard.models import FlashcardSetPage
        from cours.models import CoursPage
        from exo.models import ExoPageSimple

        result = []

        # 1) Flashcards manuelles (FlashcardSetPage)
        fc_sets = FlashcardSetPage.objects.all()
        for fc_set in fc_sets:
            try:
                parent = fc_set.get_parent()
                if parent and hasattr(parent, 'specific'):
                    parent_specific = parent.specific
                    if hasattr(parent_specific, 'chapitre') and parent_specific.chapitre in self.chapitres:
                        for card in fc_set.cards.filter(is_active=True):
                            result.append({
                                'type': 'fc_manual',
                                'titre': f"Question - {fc_set.title}",
                                'enonce': str(card.question),
                                'reponse': str(card.answer),
                                'chapitre': parent_specific.chapitre,
                            })
            except Exception as e:
                print(f"Erreur avec le set de flashcards {getattr(fc_set, 'id', '?')}: {e}")
                continue

        # 2) Définitions des cours (CoursPage)
        for chapitre in self.chapitres:
            cours_pages = CoursPage.objects.filter(chapitre=chapitre)
            for cours in cours_pages:
                try:
                    definition_cards = cours.definition_flashcards()
                    for card in definition_cards:
                        result.append({
                            'type': 'fc_definition',
                            'titre': f"Définition - {cours.title}",
                            'enonce': str(card.question),
                            'reponse': str(card.answer),
                            'chapitre': chapitre,
                        })
                except Exception as e:
                    print(f"Erreur avec les définitions du cours {getattr(cours, 'id', '?')}: {e}")
                    continue

        # 3) FC issues des exercices (avec variantes)
        exercices = ExoPageSimple.objects.all()
        for exo in exercices:
            try:
                parent = exo.get_parent()
                if parent and hasattr(parent, 'get_parent'):
                    grand_parent = parent.get_parent()
                    if grand_parent and hasattr(grand_parent, 'specific'):
                        gp = grand_parent.specific
                        if hasattr(gp, 'chapitre') and gp.chapitre in self.chapitres:
                            for block in exo.contenu:
                                # Cas explicite: bloc 'fc' ou 'flashcard'
                                if block.block_type in ('fc', 'flashcard'):
                                    val = getattr(block, 'value', {}) or {}
                                    variants = list(val.get('variants') or val.get('fc_variants') or [])
                                    if variants:
                                        for v in variants:
                                            q = v.get('question') or v.get('enonce') or val.get('question') or ''
                                            a = v.get('answer') or v.get('reponse') or val.get('reponse') or ''
                                            if q:
                                                result.append({
                                                    'type': 'fc_exercice',
                                                    'titre': f"FC - {exo.title}",
                                                    'enonce': str(q),
                                                    'reponse': str(a or ''),
                                                    'chapitre': gp.chapitre,
                                                })
                                    else:
                                        q = val.get('question') or val.get('enonce') or ''
                                        a = val.get('answer') or val.get('reponse') or ''
                                        if q:
                                            result.append({
                                                'type': 'fc_exercice',
                                                'titre': f"FC - {exo.title}",
                                                'enonce': str(q),
                                                'reponse': str(a or ''),
                                                'chapitre': gp.chapitre,
                                            })

                                # Cas “question” avec drapeau FC et/ou variantes
                                if block.block_type == 'question':
                                    val = getattr(block, 'value', {}) or {}
                                    if val.get('fc') or val.get('as_flashcard'):
                                        variants = list(val.get('variants') or val.get('fc_variants') or [])
                                        if variants:
                                            for v in variants:
                                                q = v.get('question') or v.get('enonce') or val.get('question') or ''
                                                a = v.get('answer') or v.get('reponse') or val.get('correction') or ''
                                                if q:
                                                    result.append({
                                                        'type': 'fc_exercice',
                                                        'titre': f"FC - {exo.title}",
                                                        'enonce': str(q),
                                                        'reponse': str(a or ''),
                                                        'chapitre': gp.chapitre,
                                                    })
                                        else:
                                            q = val.get('question') or val.get('enonce') or ''
                                            a = val.get('reponse') or val.get('correction') or ''
                                            if q:
                                                result.append({
                                                    'type': 'fc_exercice',
                                                    'titre': f"FC - {exo.title}",
                                                    'enonce': str(q),
                                                    'reponse': str(a or ''),
                                                    'chapitre': gp.chapitre,
                                                })
            except Exception as e:
                print(f"Erreur avec les FC de l'exercice {getattr(exo, 'id', '?')}: {e}")
                continue

        return result
    
    def select_exercices_balanced(self, level: int, min_count: int, max_count: int, 
                                equilibrer: bool = True) -> List[Dict[str, Any]]:
        """Sélectionne les exercices avec équilibrage par chapitre"""
        pool = self.get_exercices_by_level(level)
        
        if not pool:
            return []
        
        if equilibrer:
            chapitre_exercices = {}
            for exo in pool:
                chapitre_id = exo['chapitre'].id
                if chapitre_id not in chapitre_exercices:
                    chapitre_exercices[chapitre_id] = []
                chapitre_exercices[chapitre_id].append(exo)
            
            selected = []
            chapitres = list(chapitre_exercices.keys())
            current_chapitre_idx = 0
            
            while len(selected) < max_count and any(chapitre_exercices.values()):
                chapitre_id = chapitres[current_chapitre_idx]
                if chapitre_exercices[chapitre_id]:
                    selected.append(chapitre_exercices[chapitre_id].pop())
                
                current_chapitre_idx = (current_chapitre_idx + 1) % len(chapitres)
            
            if len(selected) < min_count:
                remaining = [exo for exos in chapitre_exercices.values() for exo in exos]
                self.rng.shuffle(remaining)
                selected.extend(remaining[:min_count - len(selected)])
            
            return selected[:max_count]
        else:
            self.rng.shuffle(pool)
            return pool[:max_count]
    
    def select_qcm(self, min_count: int, max_count: int, equilibrer: bool = True) -> List[Dict[str, Any]]:
        """Sélectionne les QCM"""
        pool = self.get_qcm_pool()
        
        if not pool:
            return []
        
        if equilibrer:
            chapitre_qcm = {}
            for qcm in pool:
                chapitre_id = qcm['chapitre'].id
                if chapitre_id not in chapitre_qcm:
                    chapitre_qcm[chapitre_id] = []
                chapitre_qcm[chapitre_id].append(qcm)
            
            selected = []
            chapitres = list(chapitre_qcm.keys())
            current_chapitre_idx = 0
            
            while len(selected) < max_count and any(chapitre_qcm.values()):
                chapitre_id = chapitres[current_chapitre_idx]
                if chapitre_qcm[chapitre_id]:
                    selected.append(chapitre_qcm[chapitre_id].pop())
                
                current_chapitre_idx = (current_chapitre_idx + 1) % len(chapitres)
            
            return selected[:max_count]
        else:
            self.rng.shuffle(pool)
            return pool[:max_count]
    
    def select_fc(self, min_count: int, max_count: int, equilibrer: bool = True) -> List[Dict[str, Any]]:
        """Sélectionne les flashcards"""
        pool = self.get_fc_pool()
        
        if not pool:
            return []
        
        if equilibrer:
            chapitre_fc = {}
            for fc in pool:
                chapitre_id = fc['chapitre'].id
                if chapitre_id not in chapitre_fc:
                    chapitre_fc[chapitre_id] = []
                chapitre_fc[chapitre_id].append(fc)
            
            selected = []
            chapitres = list(chapitre_fc.keys())
            current_chapitre_idx = 0
            
            while len(selected) < max_count and any(chapitre_fc.values()):
                chapitre_id = chapitres[current_chapitre_idx]
                if chapitre_fc[chapitre_id]:
                    selected.append(chapitre_fc[chapitre_id].pop())
                
                current_chapitre_idx = (current_chapitre_idx + 1) % len(chapitres)
            
            return selected[:max_count]
        else:
            self.rng.shuffle(pool)
            return pool[:max_count]


def generate_ds_content(params: Dict[str, Any]) -> Dict[str, Any]:
    """Génère le contenu d'un devoir surveillé selon les paramètres"""
    selector = ContentSelector(params['chapitres'], params['niveau'])
    
    # 1. Sélectionner les exercices par niveau
    exercices = []
    points_exos = 0
    
    if params.get('use_lvl1', True):
        ex_lvl1 = selector.select_exercices_balanced(
            1, params.get('ex_lvl1_min', 0), params.get('ex_lvl1_max', 5),
            params.get('equilibrer_par_chapitre', True)
        )
        exercices.extend(ex_lvl1)
        points_exos += sum(exo['points'] for exo in ex_lvl1)
    
    if params.get('use_lvl2', True):
        ex_lvl2 = selector.select_exercices_balanced(
            2, params.get('ex_lvl2_min', 0), params.get('ex_lvl2_max', 5),
            params.get('equilibrer_par_chapitre', True)
        )
        exercices.extend(ex_lvl2)
        points_exos += sum(exo['points'] for exo in ex_lvl2)
    
    if params.get('use_lvl3', True):
        ex_lvl3 = selector.select_exercices_balanced(
            3, params.get('ex_lvl3_min', 0), params.get('ex_lvl3_max', 5),
            params.get('equilibrer_par_chapitre', True)
        )
        exercices.extend(ex_lvl3)
        points_exos += sum(exo['points'] for exo in ex_lvl3)
    
    # 2. Sélectionner QCM et FC selon les minimums
    qcm_selected = selector.select_qcm(
        params.get('qcm_min', 0), params.get('qcm_max', 10),
        params.get('equilibrer_par_chapitre', True)
    )
    
    fc_selected = selector.select_fc(
        params.get('fc_min', 0), params.get('fc_max', 10),
        params.get('equilibrer_par_chapitre', True)
    )
    
    # 3. Compléter vers le barème global
    bareme_global = float(params.get('bareme_global', 20))
    points_par_qcm = float(params.get('points_par_qcm', 1.0))
    points_par_fc = float(params.get('points_par_fc', 1.0))
    
    points_actuels = points_exos + len(qcm_selected) * points_par_qcm + len(fc_selected) * points_par_fc
    
    # Compléter avec QCM d'abord, puis FC
    if points_actuels < bareme_global and params.get('qcm_min', 0) == 0:
        qcm_pool = selector.get_qcm_pool()
        qcm_available = [q for q in qcm_pool if q not in qcm_selected]
        random.shuffle(qcm_available)
        
        while points_actuels < bareme_global and len(qcm_selected) < params.get('qcm_max', 10) and qcm_available:
            qcm_selected.append(qcm_available.pop())
            points_actuels += points_par_qcm
    
    if points_actuels < bareme_global and params.get('fc_min', 0) == 0:
        fc_pool = selector.get_fc_pool()
        fc_available = [f for f in fc_pool if f not in fc_selected]
        random.shuffle(fc_available)
        
        while points_actuels < bareme_global and len(fc_selected) < params.get('fc_max', 10) and fc_available:
            fc_selected.append(fc_available.pop())
            points_actuels += points_par_fc
    
    # 4. Calculer la durée totale
    duree_totale = sum(exo['duree'] for exo in exercices)
    duree_totale += len(qcm_selected) * QCM_MIN_PER_ITEM
    duree_totale += len(fc_selected) * FC_MIN_PER_ITEM
    
    # 5. Ordonner la sortie : EXOS (lvl1→lvl2→lvl3) puis Questions de cours
    exercices_ordonnes = []
    for level in [1, 2, 3]:
        level_exos = [exo for exo in exercices if exo['niveau'] == level]
        exercices_ordonnes.extend(level_exos)
    
    questions_cours = qcm_selected + fc_selected
    random.shuffle(questions_cours)
    
    return {
        'exercices': exercices_ordonnes,
        'questions_cours': questions_cours,
        'points_total': points_actuels,
        'duree_totale': duree_totale,
        'bareme_global': bareme_global,
    }


def generate_serie_content(params: Dict[str, Any]) -> Dict[str, Any]:
    """Génère le contenu d'une série d'exercices selon les paramètres"""
    selector = ContentSelector(params['chapitres'], params['niveau'])
    
    exercices = []
    
    if params.get('nb_ex_lvl1', 0) > 0:
        ex_lvl1 = selector.select_exercices_balanced(
            1, 0, params.get('nb_ex_lvl1', 0),
            params.get('equilibrer_par_chapitre', True)
        )
        exercices.extend(ex_lvl1)
    
    if params.get('nb_ex_lvl2', 0) > 0:
        ex_lvl2 = selector.select_exercices_balanced(
            2, 0, params.get('nb_ex_lvl2', 0),
            params.get('equilibrer_par_chapitre', True)
        )
        exercices.extend(ex_lvl2)
    
    if params.get('nb_ex_lvl3', 0) > 0:
        ex_lvl3 = selector.select_exercices_balanced(
            3, 0, params.get('nb_ex_lvl3', 0),
            params.get('equilibrer_par_chapitre', True)
        )
        exercices.extend(ex_lvl3)
    
    qcm_selected = selector.select_qcm(
        0, params.get('nb_qcm', 0),
        params.get('equilibrer_par_chapitre', True)
    )
    
    fc_selected = selector.select_fc(
        0, params.get('nb_fc', 0),
        params.get('equilibrer_par_chapitre', True)
    )
    
    exercices_ordonnes = []
    for level in [1, 2, 3]:
        level_exos = [exo for exo in exercices if exo['niveau'] == level]
        exercices_ordonnes.extend(level_exos)
    
    questions_cours = qcm_selected + fc_selected
    random.shuffle(questions_cours)
    
    return {
        'exercices': exercices_ordonnes,
        'questions_cours': questions_cours,
    }

