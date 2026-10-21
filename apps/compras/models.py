from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.core.models import Auditable
from apps.inventario.models import Lote, Movimiento
from apps.maestros.models import Almacen, Producto, Proveedor


class OrdenCompra(Auditable):
    class Estado(models.TextChoices):
        BORRADOR = "BOR", "Borrador"
        CONFIRMADA = "CON", "Confirmada"
        PARCIAL = "PAR", "Recibida parcialmente"
        RECIBIDA = "REC", "Recibida"
        CANCELADA = "CAN", "Cancelada"

    numero = models.CharField("número", max_length=20, unique=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name="ordenes")
    fecha = models.DateField(default=timezone.localdate)
    fecha_esperada = models.DateField("fecha esperada", null=True, blank=True)
    almacen_destino = models.ForeignKey(Almacen, on_delete=models.PROTECT, verbose_name="almacén destino")
    estado = models.CharField(max_length=3, choices=Estado.choices, default=Estado.BORRADOR)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = "orden de compra"
        verbose_name_plural = "órdenes de compra"
        ordering = ["-numero"]

    def __str__(self):
        return self.numero

    @property
    def total(self):
        return sum((l.subtotal for l in self.lineas.all()), Decimal("0"))


class LineaOrdenCompra(models.Model):
    orden = models.ForeignKey(OrdenCompra, on_delete=models.CASCADE, related_name="lineas")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=14, decimal_places=3)
    precio_unitario = models.DecimalField("precio unitario (C$)", max_digits=12, decimal_places=4)
    cantidad_recibida = models.DecimalField(max_digits=14, decimal_places=3, default=0)

    class Meta:
        verbose_name = "línea de compra"
        constraints = [models.CheckConstraint(condition=models.Q(cantidad__gt=0), name="linea_oc_cantidad_positiva")]

    @property
    def subtotal(self):
        return (self.cantidad * self.precio_unitario).quantize(Decimal("0.01"))

    @property
    def pendiente(self):
        return max(self.cantidad - self.cantidad_recibida, Decimal("0"))


class Recepcion(Auditable):
    numero = models.CharField("número", max_length=20, unique=True)
    orden = models.ForeignKey(OrdenCompra, on_delete=models.PROTECT, related_name="recepciones")
    fecha = models.DateTimeField(default=timezone.now)
    almacen = models.ForeignKey(Almacen, on_delete=models.PROTECT)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = "recepción"
        verbose_name_plural = "recepciones"
        ordering = ["-fecha"]

    def __str__(self):
        return self.numero


class LineaRecepcion(models.Model):
    recepcion = models.ForeignKey(Recepcion, on_delete=models.CASCADE, related_name="lineas")
    linea_orden = models.ForeignKey(LineaOrdenCompra, on_delete=models.PROTECT, related_name="recepciones")
    lote = models.ForeignKey(Lote, on_delete=models.PROTECT, related_name="recepciones")
    cantidad = models.DecimalField(max_digits=14, decimal_places=3)
    movimiento = models.OneToOneField(Movimiento, on_delete=models.PROTECT, related_name="linea_recepcion")
