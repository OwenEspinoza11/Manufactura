"""Trazabilidad de lotes (RF-11).

Hacia atrás: lote terminado -> orden de producción -> lotes consumidos -> ... -> orden de compra / proveedor.
Hacia adelante: lote -> órdenes que lo consumieron -> lotes producidos -> ... -> despachos a clientes.
"""
from apps.produccion.models import ConsumoOP, OrdenProduccion
from apps.ventas.models import LineaDespacho

from .models import Lote


def hacia_atras(lote, cantidad=None, nivel=0, _visitados=None):
    visitados = _visitados or set()
    if lote.pk in visitados:
        return []
    visitados.add(lote.pk)
    nodo = {"nivel": nivel, "lote": lote, "cantidad": cantidad, "orden": None, "recepcion": None}
    filas = [nodo]
    if lote.origen == Lote.Origen.PRODUCCION:
        orden = OrdenProduccion.objects.filter(lote=lote).first()
        nodo["orden"] = orden
        if orden:
            for c in orden.consumos.select_related("lote__producto__unidad", "lote__proveedor"):
                filas += hacia_atras(c.lote, c.cantidad, nivel + 1, visitados)
    else:
        nodo["recepcion"] = lote.recepciones.select_related("recepcion__orden").first()
    return filas


def hacia_adelante(lote, nivel=0, _visitados=None):
    visitados = _visitados or set()
    if lote.pk in visitados:
        return []
    visitados.add(lote.pk)
    filas = []
    for c in ConsumoOP.objects.filter(lote=lote).select_related("orden__lote__producto__unidad"):
        destino = c.orden.lote
        filas.append({"nivel": nivel, "tipo": "consumo", "cantidad": c.cantidad, "orden": c.orden, "lote": destino})
        if destino:
            filas += hacia_adelante(destino, nivel + 1, visitados)
    for d in LineaDespacho.objects.filter(lote=lote).select_related("despacho__pedido__cliente"):
        filas.append({"nivel": nivel, "tipo": "despacho", "cantidad": d.cantidad, "despacho": d.despacho,
                      "cliente": d.despacho.pedido.cliente})
    return filas
