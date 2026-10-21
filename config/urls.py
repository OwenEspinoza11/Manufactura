from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

admin.site.site_header = "Blancos Aromáticos · Administración ERP"
admin.site.site_title = "ERP Blancos Aromáticos"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("apps.core.urls")),
    path("maestros/", include("apps.maestros.urls")),
    path("ingenieria/", include("apps.ingenieria.urls")),
    path("inventario/", include("apps.inventario.urls")),
    path("compras/", include("apps.compras.urls")),
    path("produccion/", include("apps.produccion.urls")),
    path("calidad/", include("apps.calidad.urls")),
    path("ventas/", include("apps.ventas.urls")),
    path("iiot/", include("apps.iiot.urls")),
    path("kpi/", include("apps.kpi.urls")),
]
