from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista, name="op_lista"),
    path("nueva/", views.nueva, name="op_nueva"),
    path("<int:pk>/", views.detalle, name="op_detalle"),
    path("<int:pk>/terminar/", views.terminar, name="op_terminar"),
    path("<int:pk>/consumo/", views.consumo_adicional, name="op_consumo"),
    path("<int:pk>/<str:accion>/", views.accion, name="op_accion"),
    path("operacion/<int:pk>/<str:accion>/", views.operacion, name="op_operacion"),
]
