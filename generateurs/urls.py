"""
URLs pour l'application generateurs.
"""
from django.urls import path
from . import views

app_name = 'generateurs'

urlpatterns = [
    path('', views.generateurs_hub_page, name='generateurs_hub_page'),
    path('ds/', views.ds_generator_page, name='ds_generator_page'),
    path('serie/', views.serie_generator_page, name='serie_generator_page'),
    path('api/generate-ds/', views.generate_ds_pdf_view, name='generate_ds_pdf'),
    path('api/generate-serie/', views.generate_serie_pdf_view, name='generate_serie_pdf'),
    path('api/update-branding/', views.update_branding_settings, name='update_branding'),
    path('pdf/build/', views.build_pdf_from_selection, name='gen_build_pdf'),
]

