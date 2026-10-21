from django.urls import path

from . import views

urlpatterns = [
    path("inspecciones/", views.inspecciones, name="inspecciones"),
    path("inspecciones/nueva/", views.nueva_inspeccion, name="inspeccion_nueva"),
    path("inspecciones/<int:pk>/", views.inspeccion_detalle, name="inspeccion_detalle"),
    path("no-conformidades/", views.no_conformidades, name="nc_lista"),
    path("no-conformidades/<int:pk>/", views.nc_detalle, name="nc_detalle"),
    path("no-conformidades/<int:pk>/disponer/", views.nc_disponer, name="nc_disponer"),
]
