"""Observer: cuando llega una lectura fuera de rango se genera una alerta para el MES."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Alerta, Lectura


@receiver(post_save, sender=Lectura)
def generar_alerta(sender, instance, created, **kwargs):
    if not created or not instance.fuera_rango:
        return
    s = instance.sensor
    limites = f"[{s.minimo if s.minimo is not None else '-∞'} – {s.maximo if s.maximo is not None else '∞'}]"
    Alerta.objects.create(
        sensor=s, lectura=instance, orden=instance.orden, fecha=instance.fecha,
        mensaje=f"{s.nombre}: {instance.valor:.2f} {s.unidad} fuera de rango {limites}"
                + (f" durante {instance.orden.numero}" if instance.orden else ""),
    )
