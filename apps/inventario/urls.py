from django.urls import path

from . import views

urlpatterns = [
    path("existencias/", views.existencias, name="existencias"),
    path("kardex/", views.kardex, name="kardex"),
    path("lotes/", views.lotes, name="lotes"),
    path("lotes/<int:pk>/", views.lote_detalle, name="lote_detalle"),
]
