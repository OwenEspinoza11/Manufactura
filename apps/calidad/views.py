from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.permisos import requiere_modulo
from apps.inventario.models import Lote

from . import services
from .models import Inspeccion, NoConformidad, ParametroCalidad


@login_required
def inspecciones(request):
    return render(request, "calidad/inspecciones.html", {
        "inspecciones": Inspeccion.objects.select_related("lote__producto", "inspector")[:200],
        "pendientes": Lote.objects.filter(estado__in=[Lote.Estado.CUARENTENA, Lote.Estado.RETRABAJO])
                      .exclude(orden_produccion__estado="PRO").select_related("producto"),
    })


@requiere_modulo("calidad")
def nueva_inspeccion(request):
    lote = get_object_or_404(Lote, pk=request.GET.get("lote") or request.POST.get("lote")) if (request.GET.get("lote") or request.POST.get("lote")) else None
    etapas_disponibles = []
    if lote:
        etapas_disponibles = [(e, l) for e, l in ParametroCalidad.Etapa.choices
                              if ParametroCalidad.objects.filter(producto=lote.producto, etapa=e, activo=True).exists()]
    etapa = request.GET.get("etapa") or request.POST.get("etapa") or (etapas_disponibles[-1][0] if etapas_disponibles else None)
    parametros = list(services.parametros_para(lote, etapa)) if lote and etapa else []

    if request.method == "POST" and lote:
        try:
            valores = {p.pk: Decimal(request.POST[f"p_{p.pk}"]) for p in parametros if request.POST.get(f"p_{p.pk}")}
            inspeccion, nc = services.registrar_inspeccion(lote, etapa, valores, request.user,
                                                           observaciones=request.POST.get("observaciones", ""))
            if nc:
                messages.warning(request, f"Inspección {inspeccion.numero} RECHAZADA. Se abrió la no conformidad {nc.numero}.")
                return redirect("nc_detalle", pk=nc.pk)
            messages.success(request, f"Inspección {inspeccion.numero} aprobada. Lote {lote} liberado.")
            return redirect("inspecciones")
        except (services.CalidadError, InvalidOperation) as e:
            messages.error(request, str(e) or "Valor inválido.")

    return render(request, "calidad/inspeccion_form.html", {
        "lote": lote, "etapa": etapa, "etapas": etapas_disponibles, "parametros": parametros,
        "lotes": Lote.objects.exclude(estado=Lote.Estado.RECHAZADO).select_related("producto")
                 .filter(producto__parametros_calidad__activo=True).distinct()[:200],
    })


@login_required
def inspeccion_detalle(request, pk):
    inspeccion = get_object_or_404(Inspeccion.objects.select_related("lote__producto", "inspector", "orden"), pk=pk)
    return render(request, "calidad/inspeccion_detalle.html", {
        "i": inspeccion, "resultados": inspeccion.resultados.select_related("parametro"),
    })


@login_required
def no_conformidades(request):
    return render(request, "calidad/nc_lista.html", {
        "ncs": NoConformidad.objects.select_related("lote__producto", "inspeccion"),
    })


@login_required
def nc_detalle(request, pk):
    nc = get_object_or_404(NoConformidad.objects.select_related("lote__producto", "inspeccion", "responsable_disposicion"), pk=pk)
    return render(request, "calidad/nc_detalle.html", {
        "nc": nc, "disposiciones": NoConformidad.Disposicion.choices,
        "resultados": nc.inspeccion.resultados.select_related("parametro") if nc.inspeccion else [],
    })


@require_POST
@requiere_modulo("calidad")
def nc_disponer(request, pk):
    nc = get_object_or_404(NoConformidad.objects.select_related("lote"), pk=pk)
    try:
        services.disponer(nc, request.POST.get("disposicion"), request.user,
                          comentario=request.POST.get("comentario", "").strip(),
                          causa_raiz=request.POST.get("causa_raiz", "").strip())
        messages.success(request, f"{nc.numero}: disposición '{nc.get_disposicion_display()}' aplicada.")
    except services.CalidadError as e:
        messages.error(request, str(e))
    return redirect("nc_detalle", pk=pk)
