"""Cálculo de indicadores directamente desde las transacciones del ERP (no desde hojas aparte).

OEE      = Disponibilidad × Rendimiento × Calidad
           Disponibilidad = (tiempo de operación − paros) / tiempo de operación
           Rendimiento    = tiempo estándar / tiempo neto de operación   (tope 100 %)
           Calidad        = unidades buenas / unidades producidas
Yield    = unidades buenas / unidades planificadas
FPY      = lotes aprobados en su primera inspección / lotes inspeccionados
Rotación = costo de lo vendido en el periodo / inventario promedio valorizado (PT)
"""
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from apps.calidad.models import Inspeccion, NoConformidad
from apps.ingenieria.services import costo_estandar
from apps.inventario.models import Movimiento
from apps.inventario.services import valor_inventario
from apps.maestros.models import Almacen
from apps.produccion.models import OrdenProduccion, RegistroOperacion

CERO = Decimal("0")


def _div(a, b):
    return (Decimal(a) / Decimal(b)) if b else CERO


def _ordenes_terminadas(desde=None, hasta=None):
    qs = OrdenProduccion.objects.filter(estado=OrdenProduccion.Estado.TERMINADA).select_related("producto__unidad", "lote")
    if desde:
        qs = qs.filter(fecha_fin__gte=desde)
    if hasta:
        qs = qs.filter(fecha_fin__lte=hasta)
    return qs


def scrap_por_lote(lotes_ids):
    filas = NoConformidad.objects.filter(lote_id__in=lotes_ids).values("lote_id").annotate(s=Sum("cantidad_scrap"))
    return {f["lote_id"]: f["s"] or CERO for f in filas}


def calidad_ordenes(ordenes):
    scrap = scrap_por_lote([o.lote_id for o in ordenes])
    producido = sum((o.cantidad_producida for o in ordenes), CERO)
    buenas = sum((o.cantidad_producida - scrap.get(o.lote_id, CERO) for o in ordenes), CERO)
    planificado = sum((o.cantidad_planificada for o in ordenes), CERO)
    return producido, buenas, planificado


def oee(desde=None, hasta=None, centro=None):
    ordenes = list(_ordenes_terminadas(desde, hasta))
    registros = RegistroOperacion.objects.filter(orden__in=ordenes, estado=RegistroOperacion.Estado.TERMINADA).select_related("operacion__ruta", "orden")
    if centro is not None:
        registros = registros.filter(operacion__centro=centro)
    operacion = paro = estandar = CERO
    for r in registros:
        operacion += r.duracion_min
        paro += r.tiempo_paro_min
        estandar += r.tiempo_estandar_min
    disponibilidad = _div(operacion - paro, operacion)
    rendimiento = min(_div(estandar, operacion - paro), Decimal("1"))
    producido, buenas, _ = calidad_ordenes(ordenes)
    calidad = _div(buenas, producido)
    return {
        "disponibilidad": disponibilidad, "rendimiento": rendimiento, "calidad": calidad,
        "oee": disponibilidad * rendimiento * calidad, "ordenes": len(ordenes),
        "minutos_operacion": operacion, "minutos_paro": paro, "minutos_estandar": estandar,
    }


def oee_por_centro(desde=None, hasta=None):
    centros = {r.operacion.centro for r in RegistroOperacion.objects.filter(estado=RegistroOperacion.Estado.TERMINADA).select_related("operacion__centro")}
    return [{"centro": c, **oee(desde, hasta, c)} for c in sorted(centros, key=lambda c: c.codigo)]


def yield_produccion(desde=None, hasta=None):
    ordenes = list(_ordenes_terminadas(desde, hasta))
    producido, buenas, planificado = calidad_ordenes(ordenes)
    return {"yield": _div(buenas, planificado), "buenas": buenas, "producido": producido, "planificado": planificado}


def fpy(desde=None, hasta=None):
    qs = Inspeccion.objects.all()
    if desde:
        qs = qs.filter(fecha__gte=desde)
    primeras = {}
    for i in qs.order_by("fecha", "id").values("lote_id", "resultado"):
        primeras.setdefault(i["lote_id"], i["resultado"])
    aprobados = sum(1 for r in primeras.values() if r == Inspeccion.Resultado.APROBADO)
    return {"fpy": _div(aprobados, len(primeras)), "aprobados": aprobados, "inspeccionados": len(primeras),
            "nc_abiertas": NoConformidad.objects.exclude(estado=NoConformidad.Estado.CERRADA).count()}


def rotacion_inventario(dias=30):
    """Inventario promedio = media de fotos semanales del inventario PT valorizado dentro del periodo."""
    hasta = timezone.now()
    desde = hasta - timedelta(days=dias)
    salidas = Movimiento.objects.filter(tipo=Movimiento.Tipo.SALIDA_VENTA, fecha__gte=desde)
    costo_ventas = sum((m.cantidad * m.costo_unitario for m in salidas), CERO)
    pt = [Almacen.Tipo.TERMINADO]
    fotos = [valor_inventario(pt, hasta=desde + timedelta(days=d)) for d in range(0, dias, 7)] + [valor_inventario(pt)]
    inicial, final = fotos[0], fotos[-1]
    promedio = sum(fotos, CERO) / len(fotos)
    rotacion = _div(costo_ventas, promedio)
    return {
        "dias_periodo": dias, "costo_ventas": costo_ventas, "inventario_inicial": inicial, "inventario_final": final,
        "inventario_promedio": promedio, "rotacion": rotacion,
        "dias_inventario": _div(Decimal(dias), rotacion) if rotacion else None,
        "rotacion_anual": rotacion * Decimal(365) / Decimal(dias),
    }


def costos_por_lote(limite=20):
    filas = []
    estandar = {}
    for o in _ordenes_terminadas().order_by("-fecha_fin")[:limite]:
        if o.producto_id not in estandar:
            estandar[o.producto_id] = costo_estandar(o.producto)
        est = estandar[o.producto_id]
        filas.append({
            "orden": o, "producto": o.producto, "lote": o.lote, "cantidad": o.cantidad_producida,
            "material": o.costo_material, "conversion": o.costo_conversion, "real": o.costo_unitario,
            "estandar": est, "variacion": _div(o.costo_unitario - est, est),
        })
    return filas


def costo_unitario_promedio(producto_tipo="PT"):
    ordenes = _ordenes_terminadas().filter(producto__tipo=producto_tipo)
    total = sum((o.costo_total for o in ordenes), CERO)
    unidades = sum((o.cantidad_producida for o in ordenes), CERO)
    return _div(total, unidades)


def sostenibilidad():
    recibido = Movimiento.objects.filter(tipo=Movimiento.Tipo.ENTRADA_COMPRA, producto__es_reciclado=True).aggregate(t=Sum("cantidad"))["t"] or CERO
    aprovechado = Movimiento.objects.filter(tipo=Movimiento.Tipo.CONSUMO_PRODUCCION, producto__es_reciclado=True).aggregate(t=Sum("cantidad"))["t"] or CERO
    eco = _ordenes_terminadas().filter(producto__linea="ECO", producto__tipo="PT")
    return {
        "aceite_recuperado_l": recibido,
        "aceite_aprovechado_l": aprovechado,
        "agua_protegida_l": recibido * settings.FACTOR_AGUA_POR_LITRO_ACEITE,
        "unidades_eco": sum((o.cantidad_producida for o in eco), CERO),
        "factor": settings.FACTOR_AGUA_POR_LITRO_ACEITE,
    }


def tiempo_ciclo():
    por_producto = defaultdict(list)
    for o in _ordenes_terminadas():
        if o.tiempo_ciclo_h is not None:
            por_producto[o.producto].append(o.tiempo_ciclo_h)
    return [{"producto": p, "ordenes": len(v), "promedio_h": sum(v) / len(v)} for p, v in sorted(por_producto.items(), key=lambda x: x[0].codigo)]


def produccion_semanal(semanas=8):
    inicio = timezone.localdate() - timedelta(weeks=semanas - 1, days=timezone.localdate().weekday())
    etiquetas = [(inicio + timedelta(weeks=i)) for i in range(semanas)]
    series = defaultdict(lambda: [0.0] * semanas)
    desde = timezone.make_aware(datetime.combine(inicio, time.min))
    for o in _ordenes_terminadas(desde=desde).filter(producto__tipo="PT"):
        i = (timezone.localtime(o.fecha_fin).date() - inicio).days // 7
        if 0 <= i < semanas:
            series[o.producto.nombre][i] += float(o.cantidad_producida)
    return {"etiquetas": [d.strftime("%d/%m") for d in etiquetas], "series": dict(series)}


def resumen():
    return {
        "oee": oee(),
        "yield": yield_produccion(),
        "fpy": fpy(),
        "rotacion": rotacion_inventario(),
        "costo_unitario_pt": costo_unitario_promedio(),
        "sostenibilidad": sostenibilidad(),
    }
