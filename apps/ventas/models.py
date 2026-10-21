from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.core.models import Auditable
from apps.inventario.models import Lote, Movimiento
from apps.maestros.models import Almacen, Cliente, Producto


class PedidoVenta(Auditable):
    class Estado(models.TextChoices):
        BORRADOR = "BOR", "Borrador"
        CONFIRMADO = "CON", "Confirmado"
        DESPACHADO = "DES", "Despachado"
        CANCELADO = "CAN", "Cancelado"

    numero = models.CharField("número", max_length=20, unique=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="pedidos")
    fecha = models.DateField(default=timezone.localdate)
    fecha_entrega = models.DateField("fecha de entrega", null=True, blank=True)
    estado = models.CharField(max_length=3, choices=Estado.choices, default=Estado.BORRADOR)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = "pedido de venta"
        verbose_name_plural = "pedidos de venta"
        ordering = ["-numero"]

    def __str__(self):
        return self.numero

    @property
    def total(self):
        return sum((l.subtotal for l in self.lineas.all()), Decimal("0"))


class LineaPedido(models.Model):
    pedido = models.ForeignKey(PedidoVenta, on_delete=models.CASCADE, related_name="lineas")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=14, decimal_places=3)
    precio_unitario = models.DecimalField("precio unitario (C$)", max_digits=12, decimal_places=2)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(cantidad__gt=0), name="linea_pedido_cantidad_positiva")]

    @property
    def subtotal(self):
        return (self.cantidad * self.precio_unitario).quantize(Decimal("0.01"))


class Despacho(Auditable):
    numero = models.CharField("número", max_length=20, unique=True)
    pedido = models.ForeignKey(PedidoVenta, on_delete=models.PROTECT, related_name="despachos")
    fecha = models.DateTimeField(default=timezone.now)
    almacen = models.ForeignKey(Almacen, on_delete=models.PROTECT)

    class Meta:
        verbose_name = "despacho"
        verbose_name_plural = "despachos"
        ordering = ["-fecha"]

    def __str__(self):
        return self.numero


class LineaDespacho(models.Model):
    despacho = models.ForeignKey(Despacho, on_delete=models.CASCADE, related_name="lineas")
    linea_pedido = models.ForeignKey(LineaPedido, on_delete=models.PROTECT, related_name="despachos")
    lote = models.ForeignKey(Lote, on_delete=models.PROTECT, related_name="despachos")
    cantidad = models.DecimalField(max_digits=14, decimal_places=3)
    movimiento = models.OneToOneField(Movimiento, on_delete=models.PROTECT, related_name="linea_despacho")
