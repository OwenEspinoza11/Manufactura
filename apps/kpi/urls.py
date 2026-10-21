from django.urls import path

from . import views

urlpatterns = [
    path("", views.tablero, name="kpi_tablero"),
    path("api/", views.api, name="kpi_api"),
    path("exportar/<str:nombre>.csv", views.exportar, name="kpi_exportar"),
]
