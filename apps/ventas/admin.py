from django.contrib import admin

from .models import Despacho, LineaPedido, PedidoVenta


class LineaInline(admin.TabularInline):
    model = LineaPedido
    extra = 0


@admin.register(PedidoVenta)
class PedidoVentaAdmin(admin.ModelAdmin):
    list_display = ("numero", "cliente", "fecha", "estado")
    list_filter = ("estado",)
    inlines = [LineaInline]


admin.site.register(Despacho)
