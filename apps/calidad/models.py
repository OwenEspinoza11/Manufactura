from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import Auditable
from apps.inventario.models import Lote
from apps.maestros.models import Producto
from apps.produccion.models import OrdenProduccion


class ParametroCalidad(models.Model):
    class Etapa(models.TextChoices):
        RECEPCION = "REC", "Recepción de material"
        PROCESO = "PRO", "En proceso"
        FINAL = "FIN", "Producto final"

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="parametros_calidad")
    etapa = models.CharField(max_length=3, choices=Etapa.choices)
    nombre = models.CharField(max_length=60)
    unidad = models.CharField(max_length=20, blank=True)
    minimo = models.DecimalField("mínimo", max_digits=10, decimal_places=3, null=True, blank=True)
    maximo = models.DecimalField("máximo", max_digits=10, decimal_places=3, null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "parámetro de calidad"
        verbose_name_plural = "parámetros de calidad"
        ordering = ["producto__codigo", "etapa", "nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.rango})"

    @property
    def rango(self):
        if self.minimo is not None and self.maximo is not None:
            return f"{self.minimo.normalize()}–{self.maximo.normalize()} {self.unidad}".strip()
        if self.minimo is not None:
            return f"≥ {self.minimo.normalize()} {self.unidad}".strip()
        if self.maximo is not None:
            return f"≤ {self.maximo.normalize()} {self.unidad}".strip()
        return "sin límite"

    def es_conforme(self, valor):
        return (self.minimo is None or valor >= self.minimo) and (self.maximo is None or valor <= self.maximo)


class Inspeccion(Auditable):
    class Resultado(models.TextChoices):
        APROBADO = "APR", "Aprobado"
        RECHAZADO = "REC", "Rechazado"

    numero = models.CharField("número", max_length=20, unique=True)
    lote = models.ForeignKey(Lote, on_delete=models.PROTECT, related_name="inspecciones")
    etapa = models.CharField(max_length=3, choices=ParametroCalidad.Etapa.choices)
    orden = models.ForeignKey(OrdenProduccion, null=True, blank=True, on_delete=models.PROTECT, related_name="inspecciones")
    fecha = models.DateTimeField(default=timezone.now)
    inspector = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    resultado = models.CharField(max_length=3, choices=Resultado.choices)
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "inspección"
        verbose_name_plural = "inspecciones"
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return self.numero


class ResultadoInspeccion(models.Model):
    inspeccion = models.ForeignKey(Inspeccion, on_delete=models.CASCADE, related_name="resultados")
    parametro = models.ForeignKey(ParametroCalidad, on_delete=models.PROTECT)
    valor = models.DecimalField(max_digits=10, decimal_places=3)
    conforme = models.BooleanField()

    class Meta:
        ordering = ["parametro__nombre"]


class NoConformidad(Auditable):
    class Estado(models.TextChoices):
        ABIERTA = "ABI", "Abierta"
        EN_RETRABAJO = "RET", "En retrabajo"
        CERRADA = "CER", "Cerrada"

    class Disposicion(models.TextChoices):
        SCRAP = "SCR", "Scrap (desecho)"
        RETRABAJO = "RET", "Retrabajo"
        LIBERACION = "LIB", "Liberación bajo concesión"

    numero = models.CharField("número", max_length=20, unique=True)
    inspeccion = models.ForeignKey(Inspeccion, null=True, blank=True, on_delete=models.PROTECT, related_name="no_conformidades")
    lote = models.ForeignKey(Lote, on_delete=models.PROTECT, related_name="no_conformidades")
    descripcion = models.TextField("descripción")
    cantidad_afectada = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    causa_raiz = models.TextField("causa raíz", blank=True)
    estado = models.CharField(max_length=3, choices=Estado.choices, default=Estado.ABIERTA)
    disposicion = models.CharField("disposición", max_length=3, choices=Disposicion.choices, blank=True)
    fecha_disposicion = models.DateTimeField(null=True, blank=True)
    responsable_disposicion = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    comentario_disposicion = models.TextField(blank=True)
    cantidad_scrap = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "no conformidad"
        verbose_name_plural = "no conformidades"
        ordering = ["-numero"]

    def __str__(self):
        return self.numero
