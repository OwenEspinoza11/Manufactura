from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista, name="pv_lista"),
    path("nuevo/", views.nuevo, name="pv_nuevo"),
    path("<int:pk>/", views.detalle, name="pv_detalle"),
    path("<int:pk>/<str:accion>/", views.accion, name="pv_accion"),
]
