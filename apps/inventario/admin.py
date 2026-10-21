from django.contrib import admin

from .models import Lote, Movimiento


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ("codigo", "producto", "origen", "documento", "estado", "costo_unitario", "fecha")
    list_filter = ("estado", "origen")
    search_fields = ("codigo",)


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    """Solo lectura: el libro mayor no se edita desde el administrador."""

    list_display = ("fecha", "tipo", "producto", "lote", "almacen_origen", "almacen_destino", "cantidad", "referencia")
    list_filter = ("tipo",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
