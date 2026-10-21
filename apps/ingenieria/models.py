from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import Auditable
from apps.maestros.models import CentroTrabajo, Producto


class BOM(Auditable):
    """Lista de materiales versionada. Un componente con BOM propia forma el siguiente nivel."""

    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="boms")
    version = models.CharField("versión", max_length=10, default="1.0")
    cantidad_base = models.DecimalField("cantidad base del lote", max_digits=14, decimal_places=3,
                                        help_text="Cantidad del producto que rinde esta fórmula (en su UdM).")
    activa = models.BooleanField(default=True)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = "BOM"
        verbose_name_plural = "BOM (listas de materiales)"
        unique_together = [("producto", "version")]
        ordering = ["producto__codigo", "-version"]

    def __str__(self):
        return f"BOM {self.producto.codigo} v{self.version}"


class LineaBOM(models.Model):
    bom = models.ForeignKey(BOM, on_delete=models.CASCADE, related_name="lineas")
    secuencia = models.PositiveSmallIntegerField(default=10)
    componente = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="usado_en")
    cantidad = models.DecimalField(max_digits=14, decimal_places=4)
    merma_pct = models.DecimalField("merma %", max_digits=5, decimal_places=2, default=0)

    class Meta:
        verbose_name = "componente de BOM"
        verbose_name_plural = "componentes de BOM"
        ordering = ["secuencia", "id"]
        constraints = [models.CheckConstraint(condition=models.Q(cantidad__gt=0), name="linea_bom_cantidad_positiva")]

    def __str__(self):
        return f"{self.componente.codigo} × {self.cantidad}"

    def clean(self):
        if self.bom_id and self.componente_id == self.bom.producto_id:
            raise ValidationError("Un producto no puede ser componente de sí mismo.")

    def cantidad_para(self, cantidad_a_producir):
        """Cantidad requerida del componente para producir `cantidad_a_producir`, incluyendo merma."""
        factor = Decimal(cantidad_a_producir) / self.bom.cantidad_base
        return (self.cantidad * factor * (1 + self.merma_pct / 100)).quantize(Decimal("0.001"))


class Ruta(Auditable):
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="rutas")
    version = models.CharField("versión", max_length=10, default="1.0")
    cantidad_lote = models.DecimalField("cantidad de referencia", max_digits=14, decimal_places=3,
                                        help_text="Cantidad para la que aplican los tiempos estándar.")
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "ruta"
        verbose_name_plural = "rutas de fabricación"
        unique_together = [("producto", "version")]
        ordering = ["producto__codigo", "-version"]

    def __str__(self):
        return f"Ruta {self.producto.codigo} v{self.version}"


class Operacion(models.Model):
    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE, related_name="operaciones")
    secuencia = models.PositiveSmallIntegerField(default=10)
    codigo = models.CharField("código", max_length=10)
    nombre = models.CharField(max_length=80)
    descripcion = models.CharField("descripción", max_length=200, blank=True)
    centro = models.ForeignKey(CentroTrabajo, on_delete=models.PROTECT, related_name="operaciones")
    tiempo_estandar_min = models.DecimalField("tiempo estándar (min)", max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = "operación"
        verbose_name_plural = "operaciones"
        ordering = ["secuencia"]

    def __str__(self):
        return f"{self.codigo} {self.nombre}"

    def tiempo_para(self, cantidad):
        return (self.tiempo_estandar_min * Decimal(cantidad) / self.ruta.cantidad_lote).quantize(Decimal("0.01"))
