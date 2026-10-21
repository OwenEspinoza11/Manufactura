from django.contrib import admin

from .models import BOM, LineaBOM, Operacion, Ruta


class LineaBOMInline(admin.TabularInline):
    model = LineaBOM
    extra = 1
    autocomplete_fields = ["componente"]


@admin.register(BOM)
class BOMAdmin(admin.ModelAdmin):
    list_display = ("producto", "version", "cantidad_base", "activa")
    list_filter = ("activa",)
    inlines = [LineaBOMInline]


class OperacionInline(admin.TabularInline):
    model = Operacion
    extra = 1


@admin.register(Ruta)
class RutaAdmin(admin.ModelAdmin):
    list_display = ("producto", "version", "cantidad_lote", "activa")
    inlines = [OperacionInline]
