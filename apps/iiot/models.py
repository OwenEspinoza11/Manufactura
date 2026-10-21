from django.db import models
from django.utils import timezone

from apps.inventario.models import Lote
from apps.maestros.models import CentroTrabajo
from apps.produccion.models import OrdenProduccion


class Dispositivo(models.Model):
    codigo = models.CharField("código", max_length=20, unique=True)
    nombre = models.CharField(max_length=80)
    descripcion = models.CharField("descripción", max_length=200, blank=True)
    centro = models.ForeignKey(CentroTrabajo, null=True, blank=True, on_delete=models.PROTECT, related_name="dispositivos")
    activo = models.BooleanField(default=True)
    ultima_conexion = models.DateTimeField("última conexión", null=True, blank=True)

    class Meta:
        verbose_name = "dispositivo IIoT"
        verbose_name_plural = "dispositivos IIoT"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"


class Sensor(models.Model):
    class Tipo(models.TextChoices):
        NIVEL = "NIV", "Nivel de tanque"
        CONTEO = "CON", "Conteo de envasado"
        TEMPERATURA = "TEM", "Temperatura"
        PH = "PH", "pH"

    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name="sensores")
    codigo = models.CharField("código", max_length=30, unique=True)
    nombre = models.CharField(max_length=80)
    tipo = models.CharField(max_length=3, choices=Tipo.choices)
    unidad = models.CharField(max_length=20)
    topico = models.CharField("tópico MQTT", max_length=120, unique=True)
    minimo = models.FloatField("límite inferior", null=True, blank=True)
    maximo = models.FloatField("límite superior", null=True, blank=True)

    class Meta:
        verbose_name = "sensor"
        verbose_name_plural = "sensores"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} ({self.unidad})"

    def fuera_de_rango(self, valor):
        return (self.minimo is not None and valor < self.minimo) or (self.maximo is not None and valor > self.maximo)


class Lectura(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name="lecturas")
    fecha = models.DateTimeField(default=timezone.now)
    valor = models.FloatField()
    fuera_rango = models.BooleanField(default=False)
    orden = models.ForeignKey(OrdenProduccion, null=True, blank=True, on_delete=models.SET_NULL, related_name="lecturas")
    lote = models.ForeignKey(Lote, null=True, blank=True, on_delete=models.SET_NULL, related_name="lecturas")

    class Meta:
        verbose_name = "lectura"
        verbose_name_plural = "lecturas"
        ordering = ["-fecha"]
        indexes = [models.Index(fields=["sensor", "-fecha"])]


class Alerta(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name="alertas")
    lectura = models.OneToOneField(Lectura, on_delete=models.CASCADE, related_name="alerta")
    orden = models.ForeignKey(OrdenProduccion, null=True, blank=True, on_delete=models.SET_NULL, related_name="alertas")
    fecha = models.DateTimeField(default=timezone.now)
    mensaje = models.CharField(max_length=200)
    atendida = models.BooleanField(default=False)

    class Meta:
        verbose_name = "alerta"
        verbose_name_plural = "alertas"
        ordering = ["atendida", "-fecha"]
