"""Servicios de inventario (capa de servicio sobre el libro mayor de movimientos)."""
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.core.models import siguiente_numero
from apps.maestros.models import Almacen, Producto

from .models import Lote, Movimiento

CERO = Decimal("0")
TIPOS_ALMACEN_CONSUMO = [Almacen.Tipo.MATERIA_PRIMA, Almacen.Tipo.ACOPIO, Almacen.Tipo.PROCESO]


class InventarioError(Exception):
    pass


def _suma(qs):
    return qs.aggregate(t=Sum("cantidad"))["t"] or CERO


def saldo(producto=None, lote=None, almacen=None, hasta=None):
    """Existencia = entradas - salidas. Sin almacén, suma todos excepto scrap."""
    qs = Movimiento.objects.all()
    if producto is not None:
        qs = qs.filter(producto=producto)
    if lote is not None:
        qs = qs.filter(lote=lote)
    if hasta is not None:
        qs = qs.filter(fecha__lte=hasta)
    if almacen is not None:
        return _suma(qs.filter(almacen_destino=almacen)) - _suma(qs.filter(almacen_origen=almacen))
    entradas = qs.filter(almacen_destino__isnull=False).exclude(almacen_destino__tipo=Almacen.Tipo.SCRAP)
    salidas = qs.filter(almacen_origen__isnull=False).exclude(almacen_origen__tipo=Almacen.Tipo.SCRAP)
    return _suma(entradas) - _suma(salidas)


def existencias(producto=None, almacen=None, incluir_scrap=False, hasta=None):
    """Existencias agregadas por (producto, lote, almacén). Devuelve filas con objetos ya cargados."""
    qs = Movimiento.objects.all()
    if producto is not None:
        qs = qs.filter(producto=producto)
    if hasta is not None:
        qs = qs.filter(fecha__lte=hasta)
    saldos = defaultdict(lambda: CERO)
    for f in qs.filter(almacen_destino__isnull=False).values("producto", "lote", "almacen_destino").annotate(q=Sum("cantidad")):
        saldos[(f["producto"], f["lote"], f["almacen_destino"])] += f["q"]
    for f in qs.filter(almacen_origen__isnull=False).values("producto", "lote", "almacen_origen").annotate(q=Sum("cantidad")):
        saldos[(f["producto"], f["lote"], f["almacen_origen"])] -= f["q"]

    claves = [k for k, v in saldos.items() if v > 0]
    productos = Producto.objects.select_related("unidad").in_bulk({k[0] for k in claves})
    lotes = Lote.objects.in_bulk({k[1] for k in claves if k[1]})
    almacenes = Almacen.objects.in_bulk({k[2] for k in claves})
    filas = []
    for p, l, a in claves:
        alm = almacenes[a]
        if almacen is not None and alm.pk != almacen.pk:
            continue
        if not incluir_scrap and alm.tipo == Almacen.Tipo.SCRAP:
            continue
        lote = lotes.get(l)
        cantidad = saldos[(p, l, a)]
        filas.append({
            "producto": productos[p],
            "lote": lote,
            "almacen": alm,
            "cantidad": cantidad,
            "valor": cantidad * (lote.costo_unitario if lote else productos[p].costo_estandar),
        })
    filas.sort(key=lambda f: (f["producto"].codigo, f["lote"].codigo if f["lote"] else "", f["almacen"].codigo))
    return filas


def valor_inventario(tipos_almacen, hasta=None):
    return sum((f["valor"] for f in existencias(hasta=hasta) if f["almacen"].tipo in tipos_almacen), CERO)


def lotes_disponibles(producto, tipos_almacen, solo_liberados=True):
    """Lotes con saldo, ordenados FEFO (primero en vencer, primero en salir; luego más antiguo)."""
    filas = [
        f for f in existencias(producto=producto)
        if f["almacen"].tipo in tipos_almacen and f["lote"] is not None
        and (not solo_liberados or f["lote"].estado == Lote.Estado.LIBERADO)
    ]
    filas.sort(key=lambda f: (f["lote"].vencimiento is None, f["lote"].vencimiento or timezone.now().date(), f["lote"].fecha))
    return filas


def disponible(producto, tipos_almacen, solo_liberados=True):
    return sum((f["cantidad"] for f in lotes_disponibles(producto, tipos_almacen, solo_liberados)), CERO)


def asignar_fefo(producto, cantidad, tipos_almacen, solo_liberados=True):
    """Reparte `cantidad` entre los lotes disponibles en orden FEFO. Devuelve [(lote, almacén, cantidad)]."""
    pendiente = Decimal(cantidad)
    asignacion = []
    for f in lotes_disponibles(producto, tipos_almacen, solo_liberados):
        if pendiente <= 0:
            break
        toma = min(pendiente, f["cantidad"])
        asignacion.append((f["lote"], f["almacen"], toma))
        pendiente -= toma
    if pendiente > 0:
        raise InventarioError(
            f"Stock liberado insuficiente de {producto}: faltan {pendiente.normalize()} {producto.unidad}."
        )
    return asignacion


@transaction.atomic
def registrar_movimiento(*, tipo, producto, cantidad, lote=None, origen=None, destino=None,
                         costo_unitario=None, referencia="", usuario=None, fecha=None, notas=""):
    cantidad = Decimal(cantidad)
    if cantidad <= 0:
        raise InventarioError("La cantidad del movimiento debe ser mayor que cero.")
    if lote is not None and lote.producto_id != producto.pk:
        raise InventarioError(f"El lote {lote} no corresponde al producto {producto}.")
    if origen is not None:
        # Bloqueo pesimista del producto para que dos salidas simultáneas no dejen saldo negativo
        Producto.objects.select_for_update().filter(pk=producto.pk).first()
        existente = saldo(producto=producto, lote=lote, almacen=origen)
        if existente < cantidad:
            raise InventarioError(
                f"Saldo insuficiente de {producto.codigo} lote {lote or '-'} en {origen.codigo}: "
                f"hay {existente.normalize()}, se requieren {cantidad.normalize()}."
            )
    if costo_unitario is None:
        costo_unitario = lote.costo_unitario if lote else producto.costo_estandar
    return Movimiento.objects.create(
        tipo=tipo, producto=producto, lote=lote, almacen_origen=origen, almacen_destino=destino,
        cantidad=cantidad, costo_unitario=costo_unitario, referencia=referencia, usuario=usuario,
        fecha=fecha or timezone.now(), notas=notas,
    )


def generar_codigo_lote(producto, fecha=None):
    fecha = fecha or timezone.now()
    prefijo = f"{producto.codigo}-{timezone.localtime(fecha):%y%m%d}-"
    return siguiente_numero(Lote, prefijo, campo="codigo", ancho=2)


def alertas_stock_minimo():
    """RF-12: productos activos con existencia utilizable por debajo de su stock mínimo."""
    totales = defaultdict(lambda: CERO)
    for f in existencias():
        totales[f["producto"].pk] += f["cantidad"]
    alertas = []
    for p in Producto.objects.filter(activo=True, stock_minimo__gt=0).select_related("unidad"):
        if totales[p.pk] < p.stock_minimo:
            alertas.append({"producto": p, "existencia": totales[p.pk], "minimo": p.stock_minimo})
    return alertas
