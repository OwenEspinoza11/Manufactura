"""Ingesta de telemetría (nivel 1-2 -> nivel 3).

Cada lectura se asocia a la orden de producción que está ejecutándose en el centro de
trabajo del dispositivo, y por ende al lote. Así el dato de planta queda trazado al ERP.
"""
from django.utils import timezone

from apps.produccion.models import OrdenProduccion, RegistroOperacion

from .models import Dispositivo, Lectura, Sensor


class IIoTError(Exception):
    pass


def orden_activa_en(centro):
    if centro is None:
        return None
    registro = (RegistroOperacion.objects.filter(estado=RegistroOperacion.Estado.EN_PROCESO, operacion__centro=centro)
                .select_related("orden__lote").order_by("-inicio").first())
    if registro:
        return registro.orden
    return (OrdenProduccion.objects.filter(estado=OrdenProduccion.Estado.EN_PROCESO, ruta__operaciones__centro=centro)
            .select_related("lote").order_by("-fecha_inicio").first())


def registrar_lectura(*, valor, topico=None, sensor_codigo=None, fecha=None):
    sensores = Sensor.objects.select_related("dispositivo__centro")
    sensor = sensores.filter(topico=topico).first() if topico else sensores.filter(codigo=sensor_codigo).first()
    if sensor is None:
        raise IIoTError(f"Sensor no registrado: {topico or sensor_codigo}")
    fecha = fecha or timezone.now()
    orden = orden_activa_en(sensor.dispositivo.centro)
    lectura = Lectura.objects.create(
        sensor=sensor, valor=float(valor), fecha=fecha, fuera_rango=sensor.fuera_de_rango(float(valor)),
        orden=orden, lote=orden.lote if orden else None,
    )
    Dispositivo.objects.filter(pk=sensor.dispositivo_id).update(ultima_conexion=fecha)
    return lectura
