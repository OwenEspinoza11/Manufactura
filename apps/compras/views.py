from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from apps.core.permisos import requiere_modulo

from . import services
from .forms import LineasCompraFormSet, OrdenCompraForm
from .models import OrdenCompra


@login_required
def lista(request):
    ordenes = OrdenCompra.objects.select_related("proveedor").prefetch_related("lineas")
    estado = request.GET.get("estado")
    if estado:
        ordenes = ordenes.filter(estado=estado)
    return render(request, "compras/lista.html", {"ordenes": ordenes, "estados": OrdenCompra.Estado.choices, "estado": estado})


@requiere_modulo("compras")
def nueva(request):
    form = OrdenCompraForm(request.POST or None)
    formset = LineasCompraFormSet(request.POST or None)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            orden = form.save(commit=False)
            orden.numero = services.nuevo_numero_oc()
            orden.creado_por = request.user
            orden.save()
            formset.instance = orden
            formset.save()
        messages.success(request, f"Orden {orden.numero} creada en borrador.")
        return redirect("oc_detalle", pk=orden.pk)
    return render(request, "compras/form.html", {"form": form, "formset": formset})


@login_required
def detalle(request, pk):
    orden = get_object_or_404(OrdenCompra.objects.select_related("proveedor", "almacen_destino"), pk=pk)
    return render(request, "compras/detalle.html", {
        "orden": orden,
        "lineas": orden.lineas.select_related("producto__unidad"),
        "recepciones": orden.recepciones.prefetch_related("lineas__lote", "lineas__linea_orden__producto"),
    })


@require_POST
@requiere_modulo("compras")
def accion(request, pk, accion):
    orden = get_object_or_404(OrdenCompra, pk=pk)
    try:
        {"confirmar": services.confirmar, "cancelar": services.cancelar}[accion](orden, request.user)
        messages.success(request, f"Orden {orden.numero}: {orden.get_estado_display().lower()}.")
    except services.CompraError as e:
        messages.error(request, str(e))
    return redirect("oc_detalle", pk=pk)


@requiere_modulo("recepcion")
def recibir(request, pk):
    orden = get_object_or_404(OrdenCompra.objects.select_related("proveedor", "almacen_destino"), pk=pk)
    lineas = list(orden.lineas.select_related("producto__unidad"))
    if request.method == "POST":
        cantidades = {}
        try:
            for l in lineas:
                cantidades[l.pk] = {
                    "cantidad": Decimal(request.POST.get(f"cant_{l.pk}") or 0),
                    "lote_proveedor": request.POST.get(f"lote_{l.pk}", "").strip(),
                    "vencimiento": parse_date(request.POST.get(f"venc_{l.pk}") or ""),
                }
            recepcion = services.recibir(orden, cantidades, usuario=request.user, notas=request.POST.get("notas", ""))
            messages.success(request, f"Recepción {recepcion.numero} registrada: lotes creados e inventario actualizado.")
            return redirect("oc_detalle", pk=pk)
        except (services.CompraError, InvalidOperation) as e:
            messages.error(request, str(e) or "Cantidad inválida.")
    return render(request, "compras/recibir.html", {"orden": orden, "lineas": lineas})
