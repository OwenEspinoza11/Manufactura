"""Ciclo de compra: borrador -> confirmada -> recibida (parcial o total)."""
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.core.models import siguiente_numero
from apps.inventario.models import Lote, Movimiento
from apps.inventario.services import InventarioError, generar_codigo_lote, registrar_movimiento

from .models import LineaRecepcion, OrdenCompra, Recepcion


class CompraError(Exception):
    pass


def nuevo_numero_oc():
    return siguiente_numero(OrdenCompra, "OC-")


def confirmar(orden, usuario=None):
    if orden.estado != OrdenCompra.Estado.BORRADOR:
        raise CompraError("Solo se confirman órdenes en borrador.")
    if not orden.lineas.exists():
        raise CompraError("La orden no tiene líneas.")
    orden.estado = OrdenCompra.Estado.CONFIRMADA
    orden.save(update_fields=["estado", "actualizado_en"])


def cancelar(orden, usuario=None):
    if orden.estado not in (OrdenCompra.Estado.BORRADOR, OrdenCompra.Estado.CONFIRMADA):
        raise CompraError("No se puede cancelar una orden con recepciones.")
    orden.estado = OrdenCompra.Estado.CANCELADA
    orden.save(update_fields=["estado", "actualizado_en"])


def _requiere_inspeccion_recepcion(producto):
    from apps.calidad.models import ParametroCalidad  # import local: calidad depende de inventario, no al revés
    return ParametroCalidad.objects.filter(producto=producto, etapa=ParametroCalidad.Etapa.RECEPCION, activo=True).exists()


@transaction.atomic
def recibir(orden, cantidades, usuario=None, fecha=None, notas=""):
    """Registra una recepción.

    `cantidades`: {linea_id: {"cantidad": Decimal, "lote_proveedor": str, "vencimiento": date|None}}
    Cada línea recibida crea un lote (en cuarentena si el producto exige inspección de recepción)
    y un movimiento de entrada en el almacén destino.
    """
    if orden.estado not in (OrdenCompra.Estado.CONFIRMADA, OrdenCompra.Estado.PARCIAL):
        raise CompraError("Solo se reciben órdenes confirmadas.")
    fecha = fecha or timezone.now()
    recepcion = Recepcion.objects.create(
        numero=siguiente_numero(Recepcion, "REC-"), orden=orden, fecha=fecha,
        almacen=orden.almacen_destino, notas=notas, creado_por=usuario,
    )
    hubo = False
    for linea in orden.lineas.select_related("producto").select_for_update():
        datos = cantidades.get(linea.pk) or {}
        cantidad = Decimal(datos.get("cantidad") or 0)
        if cantidad <= 0:
            continue
        if cantidad > linea.pendiente:
            raise CompraError(f"{linea.producto.codigo}: se intenta recibir {cantidad} y solo quedan {linea.pendiente} pendientes.")
        producto = linea.producto
        vencimiento = datos.get("vencimiento")
        if not vencimiento and producto.vida_util_dias:
            vencimiento = (timezone.localtime(fecha) + timedelta(days=producto.vida_util_dias)).date()
        lote = Lote.objects.create(
            codigo=generar_codigo_lote(producto, fecha), producto=producto, origen=Lote.Origen.COMPRA,
            documento=orden.numero, proveedor=orden.proveedor, lote_proveedor=datos.get("lote_proveedor", ""),
            fecha=fecha, vencimiento=vencimiento, cantidad_inicial=cantidad, costo_unitario=linea.precio_unitario,
            estado=Lote.Estado.CUARENTENA if _requiere_inspeccion_recepcion(producto) else Lote.Estado.LIBERADO,
            creado_por=usuario,
        )
        try:
            mov = registrar_movimiento(
                tipo=Movimiento.Tipo.ENTRADA_COMPRA, producto=producto, cantidad=cantidad, lote=lote,
                destino=orden.almacen_destino, costo_unitario=linea.precio_unitario,
                referencia=recepcion.numero, usuario=usuario, fecha=fecha,
            )
        except InventarioError as e:
            raise CompraError(str(e)) from e
        LineaRecepcion.objects.create(recepcion=recepcion, linea_orden=linea, lote=lote, cantidad=cantidad, movimiento=mov)
        linea.cantidad_recibida += cantidad
        linea.save(update_fields=["cantidad_recibida"])
        hubo = True
    if not hubo:
        raise CompraError("Indique al menos una cantidad a recibir.")
    completa = all(l.pendiente == 0 for l in orden.lineas.all())
    orden.estado = OrdenCompra.Estado.RECIBIDA if completa else OrdenCompra.Estado.PARCIAL
    orden.save(update_fields=["estado", "actualizado_en"])
    return recepcion
