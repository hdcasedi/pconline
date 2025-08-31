#!/usr/bin/env python
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pconline_site.settings.dev')
django.setup()

# Test des imports
try:
    from kahoot.utils import get_available_chapters_by_niveau, select_questions_from_chapters
    print("✓ Imports kahoot.utils réussis")
    
    # Test de la fonction get_available_chapters_by_niveau
    structure = get_available_chapters_by_niveau()
    print(f"✓ Structure des chapitres récupérée: {len(structure)} niveaux")
    
    # Test de la fonction select_questions_from_chapters
    if structure:
        # Prendre le premier chapitre disponible
        first_niveau = list(structure.keys())[0]
        first_theme = list(structure[first_niveau].keys())[0]
        first_chapter_id = structure[first_niveau][first_theme][0]['id']
        
        questions = select_questions_from_chapters([first_chapter_id], 5)
        print(f"✓ Questions récupérées: {len(questions)} questions")
        
        if questions:
            print(f"  - Première question: Type {questions[0]['type']}")
            print(f"  - Options: {len(questions[0]['options'])}")
    else:
        print("⚠ Aucun niveau/thème/chapitre trouvé")
    
    print("✅ Tests kahoot réussis !")
    
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()


