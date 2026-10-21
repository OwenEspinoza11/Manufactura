from django.conf import settings

from .permisos import PERMISOS_MODULO, puede, roles_de


def permisos(request):
    usuario = request.user
    return {
        "puede": {m: puede(usuario, m) for m in PERMISOS_MODULO},
        "mis_roles": sorted(roles_de(usuario)),
        "MONEDA": settings.MONEDA,
    }
