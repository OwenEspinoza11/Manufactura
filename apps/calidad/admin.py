from django.contrib import admin

from .models import Inspeccion, NoConformidad, ParametroCalidad, ResultadoInspeccion


@admin.register(ParametroCalidad)
class ParametroCalidadAdmin(admin.ModelAdmin):
    list_display = ("producto", "etapa", "nombre", "minimo", "maximo", "unidad", "activo")
    list_filter = ("etapa", "producto")


class ResultadoInline(admin.TabularInline):
    model = ResultadoInspeccion
    extra = 0


@admin.register(Inspeccion)
class InspeccionAdmin(admin.ModelAdmin):
    list_display = ("numero", "lote", "etapa", "resultado", "fecha")
    inlines = [ResultadoInline]


@admin.register(NoConformidad)
class NoConformidadAdmin(admin.ModelAdmin):
    list_display = ("numero", "lote", "estado", "disposicion")
