import csv
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone

from apps.inventario.models import Lote, Movimiento
from apps.produccion.models import OrdenProduccion

from . import services


@login_required
def tablero(request):
    return render(request, "kpi/tablero.html", {
        **services.resumen(),
        "oee_centros": services.oee_por_centro(),
        "costos": services.costos_por_lote(),
        "ciclos": services.tiempo_ciclo(),
        "semanal": services.produccion_semanal(),
    })


def _jsonable(valor):
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, dict):
        return {k: _jsonable(v) for k, v in valor.items()}
    return valor


@login_required
def api(request):
    return JsonResponse({"generado": timezone.now().isoformat(), **_jsonable(services.resumen())})


@login_required
def exportar(request, nombre):
    """Exportaciones CSV como evidencia técnica (abre directo en Excel)."""
    respuesta = HttpResponse(content_type="text/csv; charset=utf-8")
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}_{timezone.localdate():%Y%m%d}.csv"'
    respuesta.write("﻿")
    w = csv.writer(respuesta)
    if nombre == "movimientos":
        w.writerow(["fecha", "tipo", "producto", "lote", "origen", "destino", "cantidad", "costo_unitario", "documento", "usuario"])
        for m in Movimiento.objects.select_related("producto", "lote", "almacen_origen", "almacen_destino", "usuario").order_by("fecha"):
            w.writerow([timezone.localtime(m.fecha).isoformat(), m.get_tipo_display(), m.producto.codigo, m.lote or "",
                        m.almacen_origen.codigo if m.almacen_origen else "", m.almacen_destino.codigo if m.almacen_destino else "",
                        m.cantidad, m.costo_unitario, m.referencia, m.usuario or ""])
    elif nombre == "lotes":
        w.writerow(["lote", "producto", "origen", "documento", "estado", "cantidad_inicial", "costo_unitario", "fecha", "vencimiento"])
        for l in Lote.objects.select_related("producto").order_by("fecha"):
            w.writerow([l.codigo, l.producto.codigo, l.get_origen_display(), l.documento, l.get_estado_display(),
                        l.cantidad_inicial, l.costo_unitario, timezone.localtime(l.fecha).date(), l.vencimiento or ""])
    elif nombre == "ordenes":
        w.writerow(["orden", "producto", "estado", "planificada", "producida", "inicio", "fin", "tiempo_ciclo_h",
                    "costo_material", "costo_conversion", "costo_unitario", "lote"])
        for o in OrdenProduccion.objects.select_related("producto", "lote").order_by("numero"):
            w.writerow([o.numero, o.producto.codigo, o.get_estado_display(), o.cantidad_planificada, o.cantidad_producida,
                        o.fecha_inicio and timezone.localtime(o.fecha_inicio).isoformat(), o.fecha_fin and timezone.localtime(o.fecha_fin).isoformat(),
                        o.tiempo_ciclo_h or "", o.costo_material, o.costo_conversion, o.costo_unitario, o.lote or ""])
    elif nombre == "kpi":
        r = services.resumen()
        w.writerow(["indicador", "valor"])
        w.writerow(["OEE", round(r["oee"]["oee"], 4)])
        w.writerow(["Disponibilidad", round(r["oee"]["disponibilidad"], 4)])
        w.writerow(["Rendimiento", round(r["oee"]["rendimiento"], 4)])
        w.writerow(["Calidad", round(r["oee"]["calidad"], 4)])
        w.writerow(["Yield", round(r["yield"]["yield"], 4)])
        w.writerow(["FPY", round(r["fpy"]["fpy"], 4)])
        w.writerow(["Rotación PT (30 días)", round(r["rotacion"]["rotacion"], 4)])
        w.writerow(["Costo unitario promedio PT (C$)", round(r["costo_unitario_pt"], 4)])
        w.writerow(["Aceite recuperado (L)", r["sostenibilidad"]["aceite_recuperado_l"]])
    else:
        raise Http404
    return respuesta
