from django.contrib import admin

from .models import Alerta, Dispositivo, Lectura, Sensor


class SensorInline(admin.TabularInline):
    model = Sensor
    extra = 0


@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "centro", "ultima_conexion", "activo")
    inlines = [SensorInline]


@admin.register(Lectura)
class LecturaAdmin(admin.ModelAdmin):
    list_display = ("sensor", "fecha", "valor", "fuera_rango", "orden")
    list_filter = ("sensor", "fuera_rango")


admin.site.register(Alerta)
