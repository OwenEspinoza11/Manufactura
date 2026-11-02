from django.conf import settings

from .permisos import PERMISOS_MODULO, puede, roles_de


def permisos(request):
    usuario = request.user
    contexto = {
        "puede": {m: puede(usuario, m) for m in PERMISOS_MODULO},
        "mis_roles": sorted(roles_de(usuario)),
        "MONEDA": settings.MONEDA,
    }
    if usuario.is_authenticated:
        from apps.iiot.models import Alerta

        nombre = usuario.get_full_name() or usuario.username
        contexto["iniciales"] = "".join(p[0] for p in nombre.split()[:2]).upper()
        contexto["alertas_pendientes"] = Alerta.objects.filter(atendida=False).count()
    return contexto
