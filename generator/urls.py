from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="generator_index"),
    path("devoir/", views.devoir_page, name="generator_devoir"),
    path("pdf/entete/enonce/", lambda r: views.generate_entete_pdf(r, mode="enonce"), name="generator_entete_enonce"),
    path("pdf/entete/correction/", lambda r: views.generate_entete_pdf(r, mode="correction"), name="generator_entete_correction"),
    path("qcm/preview/", views.qcm_preview, name="generator_qcm_preview"),
    path("qcm/pdf/enonce/", views.qcm_pdf_enonce, name="qcm_pdf_enonce"),
    path("qcm/pdf/correction/", views.qcm_pdf_correction, name="qcm_pdf_correction"),
    path("payload/save/", views.save_payload, name="generator_save_payload"),
    # Alias compatible avec les anciens appels
    path("save-payload/", views.save_payload, name="generator_save_payload_alias"),
    path("pdf/<str:mode>/", views.pdf_build, name="generator_pdf_build"),


]


