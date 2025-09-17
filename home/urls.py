from django.urls import path
from .views import homepage, mon_compagnon_page

urlpatterns = [
    path("", homepage, name="home"),
    path("mon-compagnon/", mon_compagnon_page, name="mon_compagnon"),
]