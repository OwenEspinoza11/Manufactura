from apps.core.crud import Catalogo

from .models import Almacen, CentroTrabajo, Cliente, Producto, Proveedor, UnidadMedida

CATALOGOS = [
    Catalogo(
        Producto, "productos",
        columnas=[("Código", "codigo"), ("Nombre", "nombre"), ("Tipo", "tipo"), ("Línea", "linea"),
                  ("UdM", "unidad"), ("Costo est.", "costo_estandar"), ("Precio", "precio_venta"),
                  ("Stock mín.", "stock_minimo"), ("Activo", "activo")],
        campos=["codigo", "nombre", "tipo", "linea", "unidad", "costo_estandar", "precio_venta",
                "stock_minimo", "vida_util_dias", "es_reciclado", "activo"],
    ),
    Catalogo(
        Proveedor, "proveedores",
        columnas=[("Código", "codigo"), ("Nombre", "nombre"), ("Tipo", "tipo"), ("Contacto", "contacto"),
                  ("Teléfono", "telefono"), ("Activo", "activo")],
        campos=["codigo", "nombre", "ruc", "tipo", "contacto", "telefono", "email", "direccion", "activo"],
    ),
    Catalogo(
        Cliente, "clientes",
        columnas=[("Código", "codigo"), ("Nombre", "nombre"), ("Tipo", "tipo"), ("Contacto", "contacto"),
                  ("Teléfono", "telefono"), ("Activo", "activo")],
        campos=["codigo", "nombre", "ruc", "tipo", "contacto", "telefono", "email", "direccion", "activo"],
    ),
    Catalogo(
        Almacen, "almacenes",
        columnas=[("Código", "codigo"), ("Nombre", "nombre"), ("Tipo", "tipo"), ("Ubicación", "ubicacion"), ("Activo", "activo")],
        campos=["codigo", "nombre", "ubicacion", "tipo", "activo"],
    ),
    Catalogo(
        UnidadMedida, "unidades",
        columnas=[("Código", "codigo"), ("Nombre", "nombre")],
        campos=["codigo", "nombre"],
    ),
    Catalogo(
        CentroTrabajo, "centros",
        columnas=[("Código", "codigo"), ("Nombre", "nombre"), ("Capacidad", "capacidad"),
                  ("Costo/hora", "costo_hora"), ("Activo", "activo")],
        campos=["codigo", "nombre", "descripcion", "capacidad", "costo_hora", "activo"],
        modulo="ingenieria",
    ),
]

urlpatterns = [u for c in CATALOGOS for u in c.urls()]
