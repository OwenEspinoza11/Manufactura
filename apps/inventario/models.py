from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import Auditable
from apps.maestros.models import Almacen, Producto, Proveedor


class Lote(Auditable):
    class Estado(models.TextChoices):
        CUARENTENA = "CUA", "En cuarentena (pendiente de calidad)"
        LIBERADO = "LIB", "Liberado"
        RETRABAJO = "RET", "En retrabajo"
        RECHAZADO = "REC", "Rechazado (scrap)"

    class Origen(models.TextChoices):
        COMPRA = "COM", "Compra"
        PRODUCCION = "PRO", "Producción"
        AJUSTE = "AJU", "Ajuste / inventario inicial"

    codigo = models.CharField("código de lote", max_length=40, unique=True)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="lotes")
    origen = models.CharField(max_length=3, choices=Origen.choices)
    documento = models.CharField("documento origen", max_length=30, blank=True)
    proveedor = models.ForeignKey(Proveedor, null=True, blank=True, on_delete=models.PROTECT, related_name="lotes")
    lote_proveedor = models.CharField("lote del proveedor", max_length=40, blank=True)
    fecha = models.DateTimeField(default=timezone.now)
    vencimiento = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=3, choices=Estado.choices, default=Estado.LIBERADO)
    cantidad_inicial = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    costo_unitario = models.DecimalField("costo unitario (C$)", max_digits=14, decimal_places=4, default=0)

    class Meta:
        verbose_name = "lote"
        verbose_name_plural = "lotes"
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return self.codigo

    @property
    def disponible_para_uso(self):
        return self.estado == self.Estado.LIBERADO


class Movimiento(models.Model):
    """Libro mayor de inventario: los movimientos son inmutables; la existencia es su suma."""

    class Tipo(models.TextChoices):
        ENTRADA_COMPRA = "ECOM", "Entrada por compra"
        CONSUMO_PRODUCCION = "CPRO", "Consumo en producción"
        ENTRADA_PRODUCCION = "EPRO", "Entrada de producción"
        SALIDA_VENTA = "SVEN", "Salida por venta / despacho"
        SCRAP = "SCRP", "Traslado a scrap"
        TRANSFERENCIA = "TRAN", "Transferencia entre almacenes"
        AJUSTE_ENTRADA = "AJE", "Ajuste de entrada"
        AJUSTE_SALIDA = "AJS", "Ajuste de salida"

    fecha = models.DateTimeField(default=timezone.now, db_index=True)
    tipo = models.CharField(max_length=4, choices=Tipo.choices)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="movimientos")
    lote = models.ForeignKey(Lote, null=True, blank=True, on_delete=models.PROTECT, related_name="movimientos")
    almacen_origen = models.ForeignKey(Almacen, null=True, blank=True, on_delete=models.PROTECT, related_name="salidas")
    almacen_destino = models.ForeignKey(Almacen, null=True, blank=True, on_delete=models.PROTECT, related_name="entradas")
    cantidad = models.DecimalField(max_digits=14, decimal_places=3)
    costo_unitario = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    referencia = models.CharField("documento", max_length=40, db_index=True, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    notas = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "movimiento de inventario"
        verbose_name_plural = "movimientos de inventario"
        ordering = ["-fecha", "-id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name="movimiento_cantidad_positiva"),
            models.CheckConstraint(
                condition=models.Q(almacen_origen__isnull=False) | models.Q(almacen_destino__isnull=False),
                name="movimiento_con_almacen",
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.cantidad} {self.producto.codigo}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Los movimientos de inventario son inmutables: registre un movimiento de ajuste.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Los movimientos de inventario no se eliminan: registre un movimiento de ajuste.")

    @property
    def valor(self):
        return self.cantidad * self.costo_unitario
