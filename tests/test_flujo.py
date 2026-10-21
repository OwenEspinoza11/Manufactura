"""Pruebas del ciclo completo compra -> recepción -> producción (2 niveles) -> calidad -> venta."""
from decimal import Decimal as D

import pytest
from django.core.management import call_command

from apps.calidad import services as calidad
from apps.calidad.models import NoConformidad, ParametroCalidad
from apps.compras import services as compras
from apps.compras.models import LineaOrdenCompra, OrdenCompra
from apps.iiot.models import Alerta
from apps.iiot.services import registrar_lectura
from apps.inventario.models import Lote, Movimiento
from apps.inventario.services import InventarioError, saldo
from apps.inventario.trazabilidad import hacia_adelante, hacia_atras
from apps.kpi import services as kpi
from apps.maestros.models import Almacen, Cliente, Producto, Proveedor
from apps.produccion import services as produccion
from apps.ventas import services as ventas
from apps.ventas.models import LineaPedido, PedidoVenta

pytestmark = pytest.mark.django_db


@pytest.fixture
def maestros():
    call_command("cargar_datos_caso")
    return {p.codigo: p for p in Producto.objects.all()}


def comprar(p, lineas, proveedor="PRV-001", almacen="ALM-MP"):
    oc = OrdenCompra.objects.create(numero=compras.nuevo_numero_oc(), proveedor=Proveedor.objects.get(codigo=proveedor),
                                    almacen_destino=Almacen.objects.get(codigo=almacen))
    for codigo, cant in lineas:
        LineaOrdenCompra.objects.create(orden=oc, producto=p[codigo], cantidad=D(cant), precio_unitario=p[codigo].costo_estandar or D("1"))
    compras.confirmar(oc)
    compras.recibir(oc, {l.pk: {"cantidad": l.cantidad} for l in oc.lineas.all()})
    return oc


def fabricar(p, codigo, cantidad, producida=None):
    op = produccion.crear_orden(p[codigo], D(cantidad))
    produccion.confirmar(op)
    produccion.iniciar(op)
    for r in op.registros.all():
        produccion.iniciar_operacion(r)
        produccion.terminar_operacion(r)
    produccion.terminar(op, D(producida or cantidad))
    op.refresh_from_db()
    return op


def parametros(lote, etapa, **valores):
    return {ParametroCalidad.objects.get(producto=lote.producto, etapa=etapa, nombre=n).pk: D(str(v)) for n, v in valores.items()}


def test_ciclo_completo_desinfectante(maestros):
    p = maestros
    comprar(p, [("MP-AGUA", "500"), ("MP-QUAT", "10"), ("MP-SOLU", "5"), ("MP-FRLAV", "2"), ("MP-COLAZ", "1"),
                ("EMP-BOT1L", "300"), ("EMP-ETQ", "300"), ("EMP-CAJA4", "100")])
    assert saldo(p["MP-QUAT"]) == D("10")

    base = fabricar(p, "SE-BDES", "200")
    assert base.lote.estado == Lote.Estado.LIBERADO  # sin parámetros de calidad -> liberado
    assert saldo(p["MP-QUAT"]) == D("6")             # 2 L por cada 100 L de base

    pt = fabricar(p, "PT-DES1L", "200", producida="198")
    assert pt.lote.estado == Lote.Estado.CUARENTENA   # espera inspección final
    assert pt.costo_unitario > 0

    insp, nc = calidad.registrar_inspeccion(pt.lote, "FIN", parametros(pt.lote, "FIN", pH=7.0, Viscosidad=25, Densidad=1.0))
    assert nc is None
    pt.lote.refresh_from_db()
    assert pt.lote.estado == Lote.Estado.LIBERADO

    pedido = PedidoVenta.objects.create(numero=ventas.nuevo_numero(), cliente=Cliente.objects.first())
    LineaPedido.objects.create(pedido=pedido, producto=p["PT-DES1L"], cantidad=D("50"), precio_unitario=D("75"))
    ventas.confirmar(pedido)
    ventas.despachar(pedido)
    assert saldo(p["PT-DES1L"]) == D("148")

    # Trazabilidad: PT -> base -> amonio cuaternario comprado; base -> PT -> cliente
    atras = {n["lote"].producto.codigo for n in hacia_atras(pt.lote)}
    assert {"PT-DES1L", "SE-BDES", "MP-QUAT", "EMP-BOT1L"} <= atras
    assert any(n["tipo"] == "despacho" for n in hacia_adelante(base.lote))


def test_no_conformidad_scrap_y_kpi(maestros):
    p = maestros
    comprar(p, [("MP-ACUSA", "100")], proveedor="PRV-005", almacen="ALM-ACO")
    lote = Lote.objects.get(producto=p["MP-ACUSA"])
    assert lote.estado == Lote.Estado.CUARENTENA      # el aceite usado exige inspección de recepción

    with pytest.raises(produccion.ProduccionError):   # no se puede producir con material en cuarentena
        op = produccion.crear_orden(p["SE-ACFIL"], D("50"))
        produccion.confirmar(op)
        produccion.iniciar(op)

    _, nc = calidad.registrar_inspeccion(lote, "REC", parametros(lote, "REC", **{"Índice de acidez": 6.5, "Humedad e impurezas": 1}))
    assert nc is not None
    calidad.disponer(nc, NoConformidad.Disposicion.SCRAP, comentario="Aceite degradado")
    lote.refresh_from_db()
    assert lote.estado == Lote.Estado.RECHAZADO
    assert saldo(p["MP-ACUSA"]) == 0                   # salió del inventario utilizable
    assert saldo(p["MP-ACUSA"], almacen=Almacen.objects.get(codigo="ALM-SCR")) == D("100")
    assert kpi.sostenibilidad()["aceite_recuperado_l"] == D("100")


def test_libro_mayor_inmutable_y_sin_saldo_negativo(maestros):
    p = maestros
    comprar(p, [("MP-AGUA", "10")])
    mov = Movimiento.objects.first()
    with pytest.raises(ValueError):
        mov.cantidad = D("99")
        mov.save()
    with pytest.raises(ValueError):
        mov.delete()
    from apps.inventario.services import registrar_movimiento
    with pytest.raises(InventarioError):
        registrar_movimiento(tipo=Movimiento.Tipo.AJUSTE_SALIDA, producto=p["MP-AGUA"], cantidad=D("11"),
                             lote=mov.lote, origen=mov.almacen_destino)


def test_lectura_iiot_ligada_a_orden_y_alerta(maestros):
    p = maestros
    comprar(p, [("MP-AGUA", "500"), ("MP-QUAT", "10"), ("MP-SOLU", "5")])
    op = produccion.crear_orden(p["SE-BDES"], D("100"))
    produccion.confirmar(op)
    produccion.iniciar(op)
    regs = list(op.registros.all())
    produccion.iniciar_operacion(regs[0])
    produccion.terminar_operacion(regs[0])
    produccion.iniciar_operacion(regs[1])               # OP-20 Mezclado en TQ-01
    lectura = registrar_lectura(valor=12.5, sensor_codigo="TQ1-PH")
    assert lectura.orden == op and lectura.lote == op.lote
    assert lectura.fuera_rango and Alerta.objects.filter(lectura=lectura).exists()


def test_historial_completo_genera_kpi(db):
    call_command("cargar_datos_caso", historial=True)
    r = kpi.resumen()
    assert 0 < r["oee"]["oee"] <= 1
    assert 0 < r["yield"]["yield"] <= 1
    assert r["rotacion"]["costo_ventas"] > 0
    assert r["sostenibilidad"]["aceite_recuperado_l"] > 0
    assert NoConformidad.objects.filter(disposicion="SCR").exists()
    assert NoConformidad.objects.filter(disposicion="RET", estado="CER").exists()
    assert NoConformidad.objects.filter(disposicion="LIB").exists()
