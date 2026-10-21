from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import Auditable
from apps.ingenieria.models import BOM, Operacion, Ruta
from apps.inventario.models import Lote, Movimiento
from apps.maestros.models import Almacen, Producto


class OrdenProduccion(Auditable):
    class Estado(models.TextChoices):
        BORRADOR = "BOR", "Borrador"
        CONFIRMADA = "CON", "Confirmada"
        EN_PROCESO = "PRO", "En proceso"
        TERMINADA = "TER", "Terminada"
        CANCELADA = "CAN", "Cancelada"

    numero = models.CharField("número", max_length=20, unique=True)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="ordenes_produccion")
    bom = models.ForeignKey(BOM, on_delete=models.PROTECT, verbose_name="BOM")
    ruta = models.ForeignKey(Ruta, on_delete=models.PROTECT)
    cantidad_planificada = models.DecimalField(max_digits=14, decimal_places=3)
    cantidad_producida = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    fecha_planificada = models.DateField(default=timezone.localdate)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    almacen_destino = models.ForeignKey(Almacen, on_delete=models.PROTECT, verbose_name="almacén destino")
    lote = models.OneToOneField(Lote, null=True, blank=True, on_delete=models.PROTECT, related_name="orden_produccion")
    estado = models.CharField(max_length=3, choices=Estado.choices, default=Estado.BORRADOR)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    costo_material = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    costo_conversion = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = "orden de producción"
        verbose_name_plural = "órdenes de producción"
        ordering = ["-numero"]
        constraints = [models.CheckConstraint(condition=models.Q(cantidad_planificada__gt=0), name="op_cantidad_positiva")]

    def __str__(self):
        return self.numero

    @property
    def costo_total(self):
        return self.costo_material + self.costo_conversion

    @property
    def costo_unitario(self):
        return (self.costo_total / self.cantidad_producida).quantize(Decimal("0.0001")) if self.cantidad_producida else Decimal("0")

    @property
    def tiempo_ciclo_h(self):
        if self.fecha_inicio and self.fecha_fin:
            return Decimal((self.fecha_fin - self.fecha_inicio).total_seconds() / 3600).quantize(Decimal("0.01"))
        return None


class ConsumoOP(models.Model):
    """Consumo real de material por lote (base de la trazabilidad hacia atrás)."""

    orden = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE, related_name="consumos")
    componente = models.ForeignKey(Producto, on_delete=models.PROTECT)
    lote = models.ForeignKey(Lote, on_delete=models.PROTECT, related_name="consumos")
    cantidad = models.DecimalField(max_digits=14, decimal_places=3)
    costo_unitario = models.DecimalField(max_digits=14, decimal_places=4)
    adicional = models.BooleanField(default=False, help_text="Consumo fuera de fórmula (ajuste o retrabajo).")
    motivo = models.CharField(max_length=200, blank=True)
    fecha = models.DateTimeField(default=timezone.now)
    movimiento = models.OneToOneField(Movimiento, on_delete=models.PROTECT, related_name="consumo_op")

    class Meta:
        verbose_name = "consumo de orden"
        verbose_name_plural = "consumos de orden"
        ordering = ["componente__codigo"]

    @property
    def costo(self):
        return (self.cantidad * self.costo_unitario).quantize(Decimal("0.01"))


class RegistroOperacion(models.Model):
    """Orden de trabajo por operación de la ruta: tiempos reales y paros (insumo del OEE)."""

    class Estado(models.TextChoices):
        PENDIENTE = "PEN", "Pendiente"
        EN_PROCESO = "PRO", "En proceso"
        TERMINADA = "TER", "Terminada"

    orden = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE, related_name="registros")
    operacion = models.ForeignKey(Operacion, on_delete=models.PROTECT)
    estado = models.CharField(max_length=3, choices=Estado.choices, default=Estado.PENDIENTE)
    inicio = models.DateTimeField(null=True, blank=True)
    fin = models.DateTimeField(null=True, blank=True)
    operador = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    tiempo_paro_min = models.DecimalField("tiempo de paro (min)", max_digits=8, decimal_places=2, default=0)
    motivo_paro = models.CharField("motivo del paro", max_length=120, blank=True)

    class Meta:
        verbose_name = "registro de operación"
        verbose_name_plural = "registros de operación"
        ordering = ["operacion__secuencia"]

    @property
    def duracion_min(self):
        if self.inicio and self.fin:
            return Decimal((self.fin - self.inicio).total_seconds() / 60).quantize(Decimal("0.01"))
        return None

    @property
    def tiempo_estandar_min(self):
        return self.operacion.tiempo_para(self.orden.cantidad_planificada)
