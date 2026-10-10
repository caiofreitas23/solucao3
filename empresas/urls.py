from django.urls import path

from . import views

urlpatterns = [
    path("", views.mapa_esg, name="mapa_esg"),
    path("api/empresas/", views.api_empresas, name="api_empresas"),
    path("api/parceiros/", views.api_parceiros, name="api_parceiros"),
    path("api/locais/", views.api_locais, name="api_locais"),
]