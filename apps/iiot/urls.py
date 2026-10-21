from django.urls import path

from . import views

urlpatterns = [
    path("", views.panel, name="iiot_panel"),
    path("api/lecturas/", views.api_lecturas, name="iiot_api_lecturas"),
    path("api/serie/<int:pk>/", views.serie, name="iiot_serie"),
    path("alertas/<int:pk>/atender/", views.atender_alerta, name="iiot_atender"),
    path("alertas/atender-todas/", views.atender_todas, name="iiot_atender_todas"),
]
