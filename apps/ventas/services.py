"""Ciclo de venta: borrador -> confirmado -> despachado (salida por lote FEFO, solo lotes liberados)."""
from django.db import transaction
from django.utils import timezone

from apps.core.models import siguiente_numero
from apps.inventario.models import Movimiento
from apps.inventario.services import InventarioError, asignar_fefo, disponible, registrar_movimiento
from apps.maestros.models import Almacen

from .models import Despacho, LineaDespacho, PedidoVenta

E = PedidoVenta.Estado
ALMACEN_VENTA = [Almacen.Tipo.TERMINADO]


class VentaError(Exception):
    pass


def nuevo_numero():
    return siguiente_numero(PedidoVenta, "PV-")


def faltantes(pedido):
    return [
        (l, disponible(l.producto, ALMACEN_VENTA)) for l in pedido.lineas.select_related("producto__unidad")
        if disponible(l.producto, ALMACEN_VENTA) < l.cantidad
    ]


def confirmar(pedido, usuario=None, fecha=None):
    if pedido.estado != E.BORRADOR:
        raise VentaError("Solo se confirman pedidos en borrador.")
    if not pedido.lineas.exists():
        raise VentaError("El pedido no tiene líneas.")
    pedido.estado = E.CONFIRMADO
    pedido.save(update_fields=["estado", "actualizado_en"])


def cancelar(pedido, usuario=None, fecha=None):
    if pedido.estado not in (E.BORRADOR, E.CONFIRMADO):
        raise VentaError("No se puede cancelar un pedido despachado.")
    pedido.estado = E.CANCELADO
    pedido.save(update_fields=["estado", "actualizado_en"])


@transaction.atomic
def despachar(pedido, usuario=None, fecha=None):
    if pedido.estado != E.CONFIRMADO:
        raise VentaError("Solo se despachan pedidos confirmados.")
    fecha = fecha or timezone.now()
    despacho = Despacho.objects.create(
        numero=siguiente_numero(Despacho, "DES-"), pedido=pedido, fecha=fecha,
        almacen=Almacen.por_tipo(Almacen.Tipo.TERMINADO), creado_por=usuario,
    )
    for linea in pedido.lineas.select_related("producto"):
        try:
            asignacion = asignar_fefo(linea.producto, linea.cantidad, ALMACEN_VENTA)
        except InventarioError as e:
            raise VentaError(str(e)) from e
        for lote, almacen, cantidad in asignacion:
            mov = registrar_movimiento(
                tipo=Movimiento.Tipo.SALIDA_VENTA, producto=linea.producto, cantidad=cantidad, lote=lote,
                origen=almacen, referencia=despacho.numero, usuario=usuario, fecha=fecha,
                notas=f"Pedido {pedido.numero} · {pedido.cliente.nombre}",
            )
            LineaDespacho.objects.create(despacho=despacho, linea_pedido=linea, lote=lote, cantidad=cantidad, movimiento=mov)
    pedido.estado = E.DESPACHADO
    pedido.save(update_fields=["estado", "actualizado_en"])
    return despacho
