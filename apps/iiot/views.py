import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.core.permisos import requiere_modulo

from .models import Alerta, Dispositivo, Sensor
from .services import IIoTError, orden_activa_en, registrar_lectura


@login_required
def panel(request):
    sensores = []
    for s in Sensor.objects.select_related("dispositivo__centro"):
        sensores.append({"s": s, "ultima": s.lecturas.first(), "orden": orden_activa_en(s.dispositivo.centro)})
    return render(request, "iiot/panel.html", {
        "sensores": sensores,
        "dispositivos": Dispositivo.objects.select_related("centro"),
        "alertas": Alerta.objects.select_related("sensor", "orden").filter(atendida=False)[:20],
        "mqtt_prefijo": "blancosaromaticos/planta",
    })


@login_required
def serie(request, pk):
    sensor = get_object_or_404(Sensor, pk=pk)
    lecturas = list(sensor.lecturas.order_by("-fecha")[: int(request.GET.get("n", 60))])[::-1]
    return JsonResponse({
        "sensor": sensor.nombre, "unidad": sensor.unidad, "min": sensor.minimo, "max": sensor.maximo,
        "etiquetas": [timezone.localtime(l.fecha).strftime("%H:%M:%S") for l in lecturas],
        "valores": [round(l.valor, 3) for l in lecturas],
        "ultima": lecturas[-1].valor if lecturas else None,
        "orden": lecturas[-1].orden.numero if lecturas and lecturas[-1].orden else None,
    })


@csrf_exempt
@require_POST
def api_lecturas(request):
    """Endpoint de ingesta para el ESP32 (HTTP) o el puente MQTT. Requiere cabecera X-IIoT-Token."""
    if request.headers.get("X-IIoT-Token") != settings.IIOT_TOKEN:
        return JsonResponse({"error": "token inválido"}, status=401)
    try:
        datos = json.loads(request.body or b"{}")
        lotes = datos if isinstance(datos, list) else [datos]
        creadas = []
        for d in lotes:
            fecha = parse_datetime(d["fecha"]) if d.get("fecha") else None
            l = registrar_lectura(valor=d["valor"], topico=d.get("topico"), sensor_codigo=d.get("sensor"), fecha=fecha)
            creadas.append({"id": l.pk, "sensor": l.sensor.codigo, "fuera_rango": l.fuera_rango,
                            "orden": l.orden.numero if l.orden else None})
        return JsonResponse({"ok": True, "lecturas": creadas}, status=201)
    except (KeyError, ValueError, TypeError, IIoTError) as e:
        return JsonResponse({"error": str(e)}, status=400)


@require_POST
@requiere_modulo("iiot")
def atender_alerta(request, pk):
    Alerta.objects.filter(pk=pk).update(atendida=True)
    messages.success(request, "Alerta marcada como atendida.")
    return redirect(request.POST.get("siguiente") or "iiot_panel")


@require_POST
@requiere_modulo("iiot")
def atender_todas(request):
    n = Alerta.objects.filter(atendida=False).update(atendida=True)
    messages.success(request, f"{n} alertas marcadas como atendidas.")
    return redirect("iiot_panel")
