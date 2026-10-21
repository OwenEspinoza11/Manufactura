from django.contrib import admin

from .models import Almacen, CentroTrabajo, Cliente, Producto, Proveedor, UnidadMedida


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tipo", "linea", "unidad", "costo_estandar", "precio_venta", "stock_minimo", "activo")
    list_filter = ("tipo", "linea", "activo")
    search_fields = ("codigo", "nombre")


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tipo", "contacto", "telefono", "activo")
    list_filter = ("tipo",)
    search_fields = ("codigo", "nombre")


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tipo", "contacto", "telefono", "activo")
    list_filter = ("tipo",)
    search_fields = ("codigo", "nombre")


admin.site.register(Almacen)
admin.site.register(UnidadMedida)
admin.site.register(CentroTrabajo)
