from decimal import Decimal

from django import template
from django.contrib.humanize.templatetags.humanize import intcomma
from django.utils.html import format_html, format_html_join

register = template.Library()

# Color de la etiqueta por código de estado. "REC" depende del documento: OC recibida (verde), lote o inspección rechazada (rojo).
TONO_ESTADO = {
    "BOR": "neutral", "CON": "info", "PAR": "info", "REC": "ok", "CAN": "neutral",
    "PRO": "warn", "TER": "ok", "DES": "ok",
    "CUA": "warn", "LIB": "ok", "RET": "lav",
    "APR": "ok", "ABI": "bad", "CER": "neutral",
    "PEN": "neutral",
}

# Secuencia de estados que se muestra como avance en cada documento
FLUJOS = {
    "OrdenCompra": [("BOR", "Borrador"), ("CON", "Confirmada"), ("REC", "Recibida")],
    "OrdenProduccion": [("BOR", "Borrador"), ("CON", "Confirmada"), ("PRO", "En proceso"), ("TER", "Terminada")],
    "PedidoVenta": [("BOR", "Borrador"), ("CON", "Confirmado"), ("DES", "Despachado")],
    "NoConformidad": [("ABI", "Abierta"), ("RET", "En retrabajo"), ("CER", "Cerrada")],
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


@register.filter
def porcentaje_ancho(valor, tope=1):
    """Ancho CSS (0–100 %) para barras de meta y progreso."""
    if not valor:
        return "0%"
    return f"{min(Decimal(valor) / Decimal(tope), Decimal(1)) * 100:.1f}%"


@register.simple_tag
def estado(obj, campo="estado"):
    codigo = getattr(obj, campo)
    texto = getattr(obj, f"get_{campo}_display")()
    rechazo = codigo == "REC" and obj.__class__.__name__ in ("Lote", "Inspeccion")
    tono = "bad" if rechazo else TONO_ESTADO.get(codigo, "neutral")
    return format_html('<span class="pill pill-{}">{}</span>', tono, texto.split(" (")[0])


@register.simple_tag
def pasos(obj):
    """Avance del documento por su flujo de estados."""
    flujo = list(FLUJOS.get(obj.__class__.__name__, []))
    actual = obj.estado
    if obj.__class__.__name__ == "NoConformidad" and actual != "RET" and getattr(obj, "disposicion", "") != "RET":
        flujo = [p for p in flujo if p[0] != "RET"]
    if actual == "PAR":
        actual = "REC"
    codigos = [c for c, _ in flujo]
    cancelado = actual == "CAN"
    indice = codigos.index(actual) if actual in codigos else -1
    ultimo = indice == len(codigos) - 1
    items = []
    for i, (codigo, nombre) in enumerate(flujo):
        clase = "hecho" if i < indice or (ultimo and i == indice) else "actual" if i == indice else ""
        marca = "✓" if clase == "hecho" else str(i + 1)
        items.append((clase, marca, nombre))
    return format_html(
        '<ol class="pasos{}">{}</ol>', " cancelado" if cancelado else "",
        format_html_join("", '<li class="paso {}"><span class="paso-n">{}</span>{}</li>', items),
    )


@register.filter
def semaforo(valor, metas="0.85,0.65"):
    """Clase de color según metas (alta, media)."""
    if valor is None:
        return "neutral"
    alta, media = (Decimal(x) for x in metas.split(","))
    v = Decimal(valor)
    return "ok" if v >= alta else "warn" if v >= media else "bad"


@register.filter
def sangria(nivel):
    return f"padding-left:{0.9 + int(nivel) * 1.6}rem"
