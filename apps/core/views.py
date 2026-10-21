from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.calidad.models import NoConformidad
from apps.iiot.models import Alerta
from apps.inventario.models import Lote
from apps.inventario.services import alertas_stock_minimo
from apps.kpi import services as kpi
from apps.produccion.models import OrdenProduccion


@login_required
def inicio(request):
    return render(request, "core/inicio.html", {
        **kpi.resumen(),
        "semanal": kpi.produccion_semanal(),
        "en_proceso": OrdenProduccion.objects.filter(estado=OrdenProduccion.Estado.EN_PROCESO).select_related("producto", "lote"),
        "cuarentena": Lote.objects.filter(estado__in=[Lote.Estado.CUARENTENA, Lote.Estado.RETRABAJO])
                      .exclude(orden_produccion__estado=OrdenProduccion.Estado.EN_PROCESO).select_related("producto")[:10],
        "ncs": NoConformidad.objects.exclude(estado=NoConformidad.Estado.CERRADA).select_related("lote__producto")[:10],
        "stock_bajo": alertas_stock_minimo(),
        "alertas_iiot": Alerta.objects.filter(atendida=False).select_related("sensor")[:5],
        "alertas_iiot_total": Alerta.objects.filter(atendida=False).count(),
    })


@login_required
def arquitectura(request):
    return render(request, "core/arquitectura.html")
