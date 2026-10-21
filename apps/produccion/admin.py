from django.contrib import admin

from .models import ConsumoOP, OrdenProduccion, RegistroOperacion


class RegistroInline(admin.TabularInline):
    model = RegistroOperacion
    extra = 0


class ConsumoInline(admin.TabularInline):
    model = ConsumoOP
    extra = 0
    readonly_fields = ("componente", "lote", "cantidad", "costo_unitario", "adicional", "movimiento")


@admin.register(OrdenProduccion)
class OrdenProduccionAdmin(admin.ModelAdmin):
    list_display = ("numero", "producto", "cantidad_planificada", "cantidad_producida", "estado", "lote")
    list_filter = ("estado",)
    inlines = [RegistroInline, ConsumoInline]
