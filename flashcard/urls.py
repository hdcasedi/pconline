from django.urls import path
from . import views

app_name = 'flashcard'

urlpatterns = [
    path('chapitre/<int:chapitre_id>/', views.flashcards_chapitre, name='flashcards_chapitre'),
    path('chapitre/<int:chapitre_id>/json/', views.flashcards_chapitre_json, name='flashcards_chapitre_json'),
    path('import/<int:flashcard_set_id>/', views.import_flashcards, name='import_flashcards'),
]




