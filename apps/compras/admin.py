from django.contrib import admin

from .models import LineaOrdenCompra, OrdenCompra, Recepcion


class LineaInline(admin.TabularInline):
    model = LineaOrdenCompra
    extra = 0


@admin.register(OrdenCompra)
class OrdenCompraAdmin(admin.ModelAdmin):
    list_display = ("numero", "proveedor", "fecha", "estado")
    list_filter = ("estado",)
    inlines = [LineaInline]


admin.site.register(Recepcion)
