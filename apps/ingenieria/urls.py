from django.urls import path

from . import views

urlpatterns = [
    path("bom/", views.bom_lista, name="bom_lista"),
    path("bom/<int:pk>/", views.bom_detalle, name="bom_detalle"),
]
