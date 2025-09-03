import random
from cours.models import CoursPage
from .models import FlashcardSetPage


def get_flashcards_for_chapitre(chapitre, n=None):
    """
    Récupère toutes les flashcards disponibles pour un chapitre donné.
    
    Args:
        chapitre: Instance du modèle Chapitre
        n: Nombre de flashcards à retourner (si None, retourne toutes)
    
    Returns:
        Liste de dictionnaires avec les clés: question, answer, source
    """
    pool = []

    # Définitions des cours
    for cours in CoursPage.objects.filter(chapitre=chapitre):
        for block in cours.body:
            if block.block_type == "definition":
                pool.append({
                    "question": block.value["titre"],
                    "answer": block.value["contenu"],
                    "source": "definition",
                })

    # Flashcards manuelles (FlashcardSetPage)
    # Les FlashcardSetPage sont enfants de CoursPage, donc on doit filtrer par parent
    for flashcard_set in FlashcardSetPage.objects.all():
        parent_cours = flashcard_set.get_parent().specific
        if hasattr(parent_cours, 'chapitre') and parent_cours.chapitre == chapitre:
            for card in flashcard_set.cards.filter(is_active=True):
                pool.append({
                    "question": card.question,
                    "answer": card.answer,
                    "source": "manual",
                })

    # Questions FC (une variante)
    for q in QcmQuestion.objects.filter(chapitre=chapitre, type="FC", is_active=True):
        variant = q.get_random_variant()
        pool.append({
            "question": variant["question"],
            "answer": variant["answer"],
            "source": "qcm_fc",
        })

    # Tirage final si n est précisé
    if n is not None:
        return random.sample(pool, min(n, len(pool)))
    return pool
