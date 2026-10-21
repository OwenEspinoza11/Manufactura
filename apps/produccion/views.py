from decimal import Decimal, InvalidOperation

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.permisos import requiere_modulo
from apps.ingenieria.models import BOM
from apps.maestros.models import Producto

from . import services
from .models import OrdenProduccion, RegistroOperacion


class NuevaOrdenForm(forms.Form):
    producto = forms.ModelChoiceField(queryset=Producto.objects.none())
    cantidad = forms.DecimalField(min_value=Decimal("0.001"), max_digits=14, decimal_places=3)
    fecha_planificada = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), required=False)
    notas = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        con_bom = BOM.objects.filter(activa=True).values("producto")
        self.fields["producto"].queryset = Producto.objects.filter(pk__in=con_bom, activo=True).select_related("unidad")


class ConsumoAdicionalForm(forms.Form):
    componente = forms.ModelChoiceField(queryset=Producto.objects.filter(
        activo=True, tipo__in=[Producto.Tipo.MATERIA_PRIMA, Producto.Tipo.EMPAQUE, Producto.Tipo.SEMIELABORADO]))
    cantidad = forms.DecimalField(min_value=Decimal("0.001"), max_digits=14, decimal_places=3)
    motivo = forms.CharField(max_length=200)


@login_required
def lista(request):
    ordenes = OrdenProduccion.objects.select_related("producto__unidad", "lote")
    estado = request.GET.get("estado")
    if estado:
        ordenes = ordenes.filter(estado=estado)
    return render(request, "produccion/lista.html", {"ordenes": ordenes, "estados": OrdenProduccion.Estado.choices, "estado": estado})


@requiere_modulo("produccion")
def nueva(request):
    form = NuevaOrdenForm(request.POST or None, initial={"producto": request.GET.get("producto")})
    if request.method == "POST" and form.is_valid():
        try:
            op = services.crear_orden(form.cleaned_data["producto"], form.cleaned_data["cantidad"], request.user,
                                      form.cleaned_data["fecha_planificada"], form.cleaned_data["notas"])
            messages.success(request, f"Orden {op.numero} creada en borrador.")
            return redirect("op_detalle", pk=op.pk)
        except services.ProduccionError as e:
            messages.error(request, str(e))
    return render(request, "produccion/form.html", {"form": form})


@login_required
def detalle(request, pk):
    op = get_object_or_404(OrdenProduccion.objects.select_related("producto__unidad", "bom", "ruta", "lote", "almacen_destino"), pk=pk)
    contexto = {
        "op": op,
        "registros": op.registros.select_related("operacion__centro", "operador"),
        "consumos": op.consumos.select_related("componente__unidad", "lote"),
        "form_consumo": ConsumoAdicionalForm(),
        "inspecciones": op.lote.inspecciones.all() if op.lote else [],
        "lecturas": op.lecturas.select_related("sensor").order_by("-fecha")[:15],
        "alertas": op.alertas.select_related("sensor")[:10],
    }
    if op.estado in (OrdenProduccion.Estado.BORRADOR, OrdenProduccion.Estado.CONFIRMADA):
        contexto["requerimientos"] = services.requerimientos(op)
    return render(request, "produccion/detalle.html", contexto)


ACCIONES = {"confirmar": services.confirmar, "iniciar": services.iniciar, "cancelar": services.cancelar}


@require_POST
@requiere_modulo("produccion")
def accion(request, pk, accion):
    op = get_object_or_404(OrdenProduccion, pk=pk)
    try:
        ACCIONES[accion](op, request.user)
        op.refresh_from_db()
        messages.success(request, f"Orden {op.numero}: {op.get_estado_display().lower()}.")
    except services.ProduccionError as e:
        messages.error(request, str(e))
    return redirect("op_detalle", pk=pk)


@require_POST
@requiere_modulo("produccion")
def terminar(request, pk):
    op = get_object_or_404(OrdenProduccion, pk=pk)
    try:
        services.terminar(op, Decimal(request.POST.get("cantidad") or 0), request.user)
        messages.success(request, f"Orden {op.numero} terminada. Lote {op.lote} ingresó a inventario (pendiente de calidad si aplica).")
    except (services.ProduccionError, InvalidOperation) as e:
        messages.error(request, str(e) or "Cantidad inválida.")
    return redirect("op_detalle", pk=pk)


@require_POST
@requiere_modulo("produccion")
def consumo_adicional(request, pk):
    op = get_object_or_404(OrdenProduccion, pk=pk)
    form = ConsumoAdicionalForm(request.POST)
    if form.is_valid():
        try:
            services.consumo_adicional(op, form.cleaned_data["componente"], form.cleaned_data["cantidad"],
                                       request.user, form.cleaned_data["motivo"])
            messages.success(request, "Consumo adicional registrado y costeado.")
        except services.ProduccionError as e:
            messages.error(request, str(e))
    else:
        messages.error(request, "Revise los datos del consumo adicional.")
    return redirect("op_detalle", pk=pk)


@require_POST
@requiere_modulo("produccion")
def operacion(request, pk, accion):
    registro = get_object_or_404(RegistroOperacion.objects.select_related("orden", "operacion"), pk=pk)
    try:
        if accion == "iniciar":
            services.iniciar_operacion(registro, request.user)
        else:
            services.terminar_operacion(registro, request.user, paro_min=Decimal(request.POST.get("paro") or 0),
                                        motivo_paro=request.POST.get("motivo", "").strip())
        messages.success(request, f"{registro.operacion}: {registro.get_estado_display().lower()}.")
    except (services.ProduccionError, InvalidOperation) as e:
        messages.error(request, str(e) or "Dato inválido.")
    return redirect("op_detalle", pk=registro.orden_id)
