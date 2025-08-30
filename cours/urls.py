from django.urls import path
from .views import get_new_qcm_questions

# Pas de vues ici. Wagtail s'occupe du routage des pages.
urlpatterns = [
    path('qcm/new-questions/<int:cours_id>/', get_new_qcm_questions, name='get_new_qcm_questions'),
]