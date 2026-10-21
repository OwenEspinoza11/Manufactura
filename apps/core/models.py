from django.conf import settings
from django.db import models


class Auditable(models.Model):
    """Base de auditoría (RNF-04): toda entidad guarda cuándo y quién la creó."""

    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="creado por",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    class Meta:
        abstract = True


def siguiente_numero(modelo, prefijo, campo="numero", ancho=4):
    """Genera correlativos legibles: OC-0001, OP-2026-0001, NC-0001..."""
    ultimo = (
        modelo.objects.filter(**{f"{campo}__startswith": prefijo})
        .order_by(f"-{campo}")
        .values_list(campo, flat=True)
        .first()
    )
    n = int(ultimo[len(prefijo):]) + 1 if ultimo else 1
    return f"{prefijo}{n:0{ancho}d}"
