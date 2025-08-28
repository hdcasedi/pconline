from django.shortcuts import render, get_object_or_404
from django.http import Http404
from wagtail.models import Page
from referentiel.models import Niveau
from .models import CoursRootPage, CoursIndexPage

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
