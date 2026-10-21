from decimal import Decimal

from django import template
from django.contrib.humanize.templatetags.humanize import intcomma
from django.utils.html import format_html

register = template.Library()

COLORES_ESTADO = {
    # documentos
    "BOR": "secondary", "CON": "primary", "PAR": "info", "REC": "success", "CAN": "dark",
    "PRO": "warning", "TER": "success", "DES": "success",
    # lotes
    "CUA": "warning", "LIB": "success", "RET": "info",
    # calidad
    "APR": "success", "ABI": "danger", "CER": "secondary",
    # operaciones
    "PEN": "secondary",
}


@register.filter
def pct(valor, decimales=1):
    if valor is None:
        return "—"
    return f"{Decimal(valor) * 100:.{decimales}f} %"


@register.filter
def num(valor, decimales=2):
    if valor in (None, ""):
        return "—"
    return intcomma(f"{Decimal(valor):.{decimales}f}")


@register.filter
def moneda(valor):
    if valor in (None, ""):
        return "—"
    return f"C$ {intcomma(f'{Decimal(valor):.2f}')}"


@register.simple_tag
def estado(obj, campo="estado"):
    codigo = getattr(obj, campo)
    texto = getattr(obj, f"get_{campo}_display")()
    # Un lote "REC" es rechazado (rojo); una OC "REC" es recibida (verde)
    color = "danger" if (codigo == "REC" and obj.__class__.__name__ in ("Lote", "Inspeccion")) else COLORES_ESTADO.get(codigo, "secondary")
    return format_html('<span class="badge text-bg-{}">{}</span>', color, texto)


@register.filter
def semaforo(valor, metas="0.85,0.65"):
    """Clase de color según metas (alta, media)."""
    if valor is None:
        return "secondary"
    alta, media = (Decimal(x) for x in metas.split(","))
    v = Decimal(valor)
    return "success" if v >= alta else "warning" if v >= media else "danger"


@register.filter
def sangria(nivel):
    return f"padding-left:{0.5 + int(nivel) * 1.6}rem"
