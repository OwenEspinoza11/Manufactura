"""Control de acceso por roles (RNF-02). Los roles son grupos de Django."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

ADMIN = "Administrador"
GERENCIA = "Gerencia"
COMPRAS = "Compras"
ALMACEN = "Almacén"
PRODUCCION = "Producción"
CALIDAD = "Calidad"
VENTAS = "Ventas"

ROLES = [ADMIN, GERENCIA, COMPRAS, ALMACEN, PRODUCCION, CALIDAD, VENTAS]

# Qué roles pueden ejecutar transacciones en cada módulo (Gerencia solo consulta)
PERMISOS_MODULO = {
    "maestros": [ADMIN],
    "ingenieria": [ADMIN, PRODUCCION],
    "compras": [ADMIN, COMPRAS],
    "recepcion": [ADMIN, COMPRAS, ALMACEN],
    "produccion": [ADMIN, PRODUCCION],
    "calidad": [ADMIN, CALIDAD],
    "ventas": [ADMIN, VENTAS],
    "despacho": [ADMIN, VENTAS, ALMACEN],
    "iiot": [ADMIN, PRODUCCION, CALIDAD],
}


def roles_de(usuario):
    if not usuario.is_authenticated:
        return set()
    if usuario.is_superuser:
        return set(ROLES)
    return set(usuario.groups.values_list("name", flat=True))


def puede(usuario, modulo):
    roles = roles_de(usuario)
    return ADMIN in roles or bool(roles & set(PERMISOS_MODULO.get(modulo, [])))


def requiere_modulo(modulo):
    """Decorador de vista: exige sesión y permiso transaccional sobre el módulo."""

    def decorador(vista):
        @login_required
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not puede(request.user, modulo):
                raise PermissionDenied(f"Su rol no permite operar el módulo {modulo}.")
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador
