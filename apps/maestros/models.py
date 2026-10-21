from django.db import models

from apps.core.models import Auditable


class UnidadMedida(models.Model):
    codigo = models.CharField("código", max_length=10, unique=True)
    nombre = models.CharField(max_length=40)

    class Meta:
        verbose_name = "unidad de medida"
        verbose_name_plural = "unidades de medida"
        ordering = ["codigo"]

    def __str__(self):
        return self.codigo


class Producto(Auditable):
    class Tipo(models.TextChoices):
        MATERIA_PRIMA = "MP", "Materia prima"
        EMPAQUE = "EMP", "Material de empaque"
        SEMIELABORADO = "SE", "Semielaborado"
        TERMINADO = "PT", "Producto terminado"

    class Linea(models.TextChoices):
        DESINFECTANTES = "DESINF", "Desinfectantes"
        ECO = "ECO", "Línea ECO (aceite reciclado)"
        GENERAL = "GEN", "General"

    codigo = models.CharField("código", max_length=20, unique=True)
    nombre = models.CharField(max_length=120)
    tipo = models.CharField(max_length=3, choices=Tipo.choices)
    linea = models.CharField("línea", max_length=6, choices=Linea.choices, default=Linea.GENERAL)
    unidad = models.ForeignKey(UnidadMedida, on_delete=models.PROTECT)
    costo_estandar = models.DecimalField("costo estándar (C$)", max_digits=12, decimal_places=4, default=0,
                                         help_text="Para MP/empaque: precio de referencia. Para SE/PT se calcula desde la BOM.")
    precio_venta = models.DecimalField("precio de venta (C$)", max_digits=12, decimal_places=2, default=0)
    stock_minimo = models.DecimalField("stock mínimo", max_digits=14, decimal_places=3, default=0)
    vida_util_dias = models.PositiveIntegerField("vida útil (días)", null=True, blank=True)
    es_reciclado = models.BooleanField("insumo reciclado", default=False,
                                       help_text="Marca insumos recuperados (p. ej. aceite de cocina usado) para el KPI de sostenibilidad.")
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"

    @property
    def es_fabricado(self):
        return self.tipo in (self.Tipo.SEMIELABORADO, self.Tipo.TERMINADO)


class Almacen(models.Model):
    class Tipo(models.TextChoices):
        MATERIA_PRIMA = "MP", "Materias primas y empaque"
        ACOPIO = "ACO", "Acopio de aceite usado"
        PROCESO = "PP", "Semielaborados / en proceso"
        TERMINADO = "PT", "Producto terminado"
        SCRAP = "SCR", "Scrap / mermas"

    codigo = models.CharField("código", max_length=10, unique=True)
    nombre = models.CharField(max_length=80)
    ubicacion = models.CharField("ubicación", max_length=120, blank=True)
    tipo = models.CharField(max_length=3, choices=Tipo.choices)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "almacén"
        verbose_name_plural = "almacenes"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"

    @classmethod
    def por_tipo(cls, tipo):
        return cls.objects.filter(tipo=tipo, activo=True).order_by("codigo").first()


class Proveedor(Auditable):
    class Tipo(models.TextChoices):
        QUIMICOS = "QUI", "Químicos"
        EMPAQUE = "EMP", "Envases y empaque"
        ACOPIO = "ACO", "Acopio de aceite usado"

    codigo = models.CharField("código", max_length=10, unique=True)
    nombre = models.CharField(max_length=120)
    ruc = models.CharField("RUC", max_length=20, blank=True)
    tipo = models.CharField(max_length=3, choices=Tipo.choices)
    contacto = models.CharField(max_length=80, blank=True)
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.CharField("dirección", max_length=200, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "proveedor"
        verbose_name_plural = "proveedores"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"


class Cliente(Auditable):
    class Tipo(models.TextChoices):
        DISTRIBUIDOR = "DIS", "Distribuidor"
        NEGOCIO = "NEG", "Negocio / comercio"
        HOGAR = "HOG", "Hogar"

    codigo = models.CharField("código", max_length=10, unique=True)
    nombre = models.CharField(max_length=120)
    ruc = models.CharField("RUC / cédula", max_length=20, blank=True)
    tipo = models.CharField(max_length=3, choices=Tipo.choices)
    contacto = models.CharField(max_length=80, blank=True)
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.CharField("dirección", max_length=200, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"


class CentroTrabajo(models.Model):
    codigo = models.CharField("código", max_length=10, unique=True)
    nombre = models.CharField(max_length=80)
    descripcion = models.CharField("descripción", max_length=200, blank=True)
    capacidad = models.CharField(max_length=60, blank=True, help_text="Ej. 500 L por lote")
    costo_hora = models.DecimalField("costo por hora (C$)", max_digits=10, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "centro de trabajo"
        verbose_name_plural = "centros de trabajo"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"
