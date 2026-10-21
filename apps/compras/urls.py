from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista, name="oc_lista"),
    path("nueva/", views.nueva, name="oc_nueva"),
    path("<int:pk>/", views.detalle, name="oc_detalle"),
    path("<int:pk>/recibir/", views.recibir, name="oc_recibir"),
    path("<int:pk>/<str:accion>/", views.accion, name="oc_accion"),
]
