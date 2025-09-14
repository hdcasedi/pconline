from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from referentiel.models import Chapitre
from .utils import get_flashcards_for_chapitre
from .models import FlashcardSetPage


def flashcards_chapitre(request, chapitre_id):
    """
    Vue pour afficher toutes les flashcards d'un chapitre
    """
    chapitre = get_object_or_404(Chapitre, id=chapitre_id)
    flashcards = get_flashcards_for_chapitre(chapitre)
    
    context = {
        'chapitre': chapitre,
        'flashcards': flashcards,
        'total_count': len(flashcards),
    }
    
    return render(request, 'flashcard/flashcards_chapitre.html', context)


def flashcards_chapitre_json(request, chapitre_id):
    """
    API JSON pour récupérer les flashcards d'un chapitre
    """
    chapitre = get_object_or_404(Chapitre, id=chapitre_id)
    n = request.GET.get('n', None)
    if n:
        try:
            n = int(n)
        except ValueError:
            n = None
    
    flashcards = get_flashcards_for_chapitre(chapitre, n=n)
    
    return JsonResponse({
        'chapitre': {
            'id': chapitre.id,
            'titre': chapitre.titre,
            'theme': chapitre.theme.nom,
            'niveau': chapitre.theme.niveau.nom,
        },
        'flashcards': flashcards,
        'total_count': len(flashcards),
    })


@csrf_exempt
@require_POST
def import_flashcards(request, flashcard_set_id):
    """
    Vue pour importer les flashcards depuis le fichier attaché
    """
    try:
        flashcard_set = get_object_or_404(FlashcardSetPage, id=flashcard_set_id)
        
        if not flashcard_set.source_file:
            return JsonResponse({
                'success': False,
                'message': 'Aucun fichier attaché'
            })
        
        # Importer les cartes
        created = flashcard_set.import_from_file()
        
        return JsonResponse({
            'success': True,
            'message': f'{created} cartes importées avec succès',
            'created': created
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors de l\'import: {str(e)}'
        })
