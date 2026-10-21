"""Ejecución de manufactura (MES básico).

Máquina de estados de la orden:  Borrador -> Confirmada -> En proceso -> Terminada
                                     \\-----------\\-> Cancelada
Cada transición es una función atómica (Unit of Work): si algo falla, no queda nada a medias.
"""
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.core.models import siguiente_numero
from apps.ingenieria.services import bom_activa, ruta_activa
from apps.inventario.models import Lote, Movimiento
from apps.inventario.services import (
    TIPOS_ALMACEN_CONSUMO, InventarioError, asignar_fefo, disponible, generar_codigo_lote, registrar_movimiento,
)
from apps.maestros.models import Almacen, Producto

from .models import ConsumoOP, OrdenProduccion, RegistroOperacion

E = OrdenProduccion.Estado


class ProduccionError(Exception):
    pass


def _exigir_estado(op, *estados):
    if op.estado not in estados:
        permitidos = ", ".join(OrdenProduccion.Estado(e).label for e in estados)
        raise ProduccionError(f"La orden {op.numero} está {op.get_estado_display().lower()}; se requiere: {permitidos}.")


def crear_orden(producto, cantidad, usuario=None, fecha_planificada=None, notas=""):
    bom, ruta = bom_activa(producto), ruta_activa(producto)
    if not bom or not ruta:
        raise ProduccionError(f"{producto} no tiene BOM y ruta activas.")
    tipo_destino = Almacen.Tipo.TERMINADO if producto.tipo == Producto.Tipo.TERMINADO else Almacen.Tipo.PROCESO
    fecha_planificada = fecha_planificada or timezone.localdate()
    return OrdenProduccion.objects.create(
        numero=siguiente_numero(OrdenProduccion, f"OP-{fecha_planificada.year}-"),
        producto=producto, bom=bom, ruta=ruta, cantidad_planificada=Decimal(cantidad),
        fecha_planificada=fecha_planificada, almacen_destino=Almacen.por_tipo(tipo_destino),
        responsable=usuario, creado_por=usuario, notas=notas,
    )


def requerimientos(op):
    filas = []
    for linea in op.bom.lineas.select_related("componente__unidad"):
        requerido = linea.cantidad_para(op.cantidad_planificada)
        hay = disponible(linea.componente, TIPOS_ALMACEN_CONSUMO)
        filas.append({"componente": linea.componente, "requerido": requerido, "disponible": hay,
                      "faltante": max(requerido - hay, Decimal("0"))})
    return filas


def confirmar(op, usuario=None, fecha=None):
    _exigir_estado(op, E.BORRADOR)
    op.estado = E.CONFIRMADA
    op.save(update_fields=["estado", "actualizado_en"])


def cancelar(op, usuario=None, fecha=None):
    _exigir_estado(op, E.BORRADOR, E.CONFIRMADA)
    op.estado = E.CANCELADA
    op.save(update_fields=["estado", "actualizado_en"])


def _consumir(op, componente, cantidad, usuario, fecha, adicional=False, motivo=""):
    try:
        asignacion = asignar_fefo(componente, cantidad, TIPOS_ALMACEN_CONSUMO)
    except InventarioError as e:
        raise ProduccionError(str(e)) from e
    costo = Decimal("0")
    for lote, almacen, cant in asignacion:
        mov = registrar_movimiento(
            tipo=Movimiento.Tipo.CONSUMO_PRODUCCION, producto=componente, cantidad=cant, lote=lote,
            origen=almacen, referencia=op.numero, usuario=usuario, fecha=fecha, notas=motivo,
        )
        consumo = ConsumoOP.objects.create(
            orden=op, componente=componente, lote=lote, cantidad=cant, costo_unitario=lote.costo_unitario,
            adicional=adicional, motivo=motivo, fecha=fecha, movimiento=mov,
        )
        costo += consumo.costo
    return costo


@transaction.atomic
def iniciar(op, usuario=None, fecha=None):
    """Emite los materiales por lote (FEFO), crea el lote a producir y las órdenes de trabajo por operación."""
    _exigir_estado(op, E.CONFIRMADA)
    fecha = fecha or timezone.now()
    faltantes = [r for r in requerimientos(op) if r["faltante"] > 0]
    if faltantes:
        detalle = "; ".join(f"{r['componente'].codigo} faltan {r['faltante'].normalize()} {r['componente'].unidad}" for r in faltantes)
        raise ProduccionError(f"Material liberado insuficiente: {detalle}.")
    costo = Decimal("0")
    for linea in op.bom.lineas.select_related("componente"):
        costo += _consumir(op, linea.componente, linea.cantidad_para(op.cantidad_planificada), usuario, fecha)
    producto = op.producto
    op.lote = Lote.objects.create(
        codigo=generar_codigo_lote(producto, fecha), producto=producto, origen=Lote.Origen.PRODUCCION,
        documento=op.numero, fecha=fecha, estado=Lote.Estado.CUARENTENA, creado_por=usuario,
        vencimiento=(timezone.localtime(fecha) + timedelta(days=producto.vida_util_dias)).date() if producto.vida_util_dias else None,
    )
    RegistroOperacion.objects.bulk_create(
        RegistroOperacion(orden=op, operacion=operacion) for operacion in op.ruta.operaciones.all()
    )
    op.costo_material = costo
    op.estado = E.EN_PROCESO
    op.fecha_inicio = fecha
    op.save()
    return op


@transaction.atomic
def consumo_adicional(op, componente, cantidad, usuario=None, motivo="", fecha=None):
    """Consumo fuera de fórmula (p. ej. ácido cítrico para corregir pH). Queda trazado y costeado.

    Se permite en una orden en proceso o en una orden terminada cuyo lote está en retrabajo;
    en el segundo caso se recalcula el costo unitario del lote.
    """
    en_retrabajo = op.estado == E.TERMINADA and op.lote and op.lote.estado == Lote.Estado.RETRABAJO
    if not en_retrabajo:
        _exigir_estado(op, E.EN_PROCESO)
    if not motivo:
        raise ProduccionError("Indique el motivo del consumo adicional.")
    op.costo_material += _consumir(op, componente, Decimal(cantidad), usuario, fecha or timezone.now(), True, motivo)
    op.save(update_fields=["costo_material", "actualizado_en"])
    if en_retrabajo:
        op.lote.costo_unitario = op.costo_total / op.cantidad_producida
        op.lote.save(update_fields=["costo_unitario", "actualizado_en"])


def iniciar_operacion(registro, usuario=None, fecha=None):
    _exigir_estado(registro.orden, E.EN_PROCESO)
    if registro.estado != RegistroOperacion.Estado.PENDIENTE:
        raise ProduccionError("La operación ya fue iniciada.")
    previas = registro.orden.registros.filter(operacion__secuencia__lt=registro.operacion.secuencia).exclude(
        estado=RegistroOperacion.Estado.TERMINADA)
    if previas.exists():
        raise ProduccionError("Debe terminar las operaciones anteriores de la ruta.")
    registro.estado = RegistroOperacion.Estado.EN_PROCESO
    registro.inicio = fecha or timezone.now()
    registro.operador = usuario
    registro.save()


def terminar_operacion(registro, usuario=None, fecha=None, paro_min=0, motivo_paro=""):
    if registro.estado != RegistroOperacion.Estado.EN_PROCESO:
        raise ProduccionError("La operación no está en proceso.")
    fin = fecha or timezone.now()
    paro = Decimal(paro_min or 0)
    duracion = Decimal((fin - registro.inicio).total_seconds() / 60)
    if paro < 0 or paro > duracion:
        raise ProduccionError(f"El paro ({paro} min) no puede superar la duración de la operación ({duracion:.1f} min).")
    if paro > 0 and not motivo_paro:
        raise ProduccionError("Indique el motivo del paro.")
    registro.estado = RegistroOperacion.Estado.TERMINADA
    registro.fin = fin
    registro.tiempo_paro_min = paro
    registro.motivo_paro = motivo_paro
    registro.save()


def _requiere_inspeccion(producto):
    from apps.calidad.models import ParametroCalidad
    return ParametroCalidad.objects.filter(
        producto=producto, activo=True, etapa__in=[ParametroCalidad.Etapa.PROCESO, ParametroCalidad.Etapa.FINAL]
    ).exists()


@transaction.atomic
def terminar(op, cantidad_producida, usuario=None, fecha=None):
    """Cierra la orden: costea (material + conversión), ingresa el lote al almacén y lo deja en cuarentena."""
    _exigir_estado(op, E.EN_PROCESO)
    cantidad = Decimal(cantidad_producida)
    if cantidad <= 0:
        raise ProduccionError("La cantidad producida debe ser mayor que cero.")
    registros = list(op.registros.select_related("operacion__centro"))
    if any(r.estado != RegistroOperacion.Estado.TERMINADA for r in registros):
        raise ProduccionError("Todas las operaciones de la ruta deben estar terminadas.")
    fecha = fecha or timezone.now()
    op.costo_conversion = sum(
        (r.duracion_min / 60 * r.operacion.centro.costo_hora for r in registros), Decimal("0")
    ).quantize(Decimal("0.01"))
    op.cantidad_producida = cantidad
    costo_unitario = (op.costo_material + op.costo_conversion) / cantidad

    lote = op.lote
    lote.cantidad_inicial = cantidad
    lote.costo_unitario = costo_unitario
    lote.estado = Lote.Estado.CUARENTENA if _requiere_inspeccion(op.producto) else Lote.Estado.LIBERADO
    lote.save()
    registrar_movimiento(
        tipo=Movimiento.Tipo.ENTRADA_PRODUCCION, producto=op.producto, cantidad=cantidad, lote=lote,
        destino=op.almacen_destino, costo_unitario=costo_unitario, referencia=op.numero, usuario=usuario, fecha=fecha,
    )
    op.estado = E.TERMINADA
    op.fecha_fin = fecha
    op.save()
    return op
