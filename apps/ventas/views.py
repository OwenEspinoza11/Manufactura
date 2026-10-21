from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.permisos import puede, requiere_modulo
from apps.maestros.models import Producto

from . import services
from .models import LineaPedido, PedidoVenta


class PedidoForm(forms.ModelForm):
    class Meta:
        model = PedidoVenta
        fields = ["cliente", "fecha", "fecha_entrega", "notas"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "fecha_entrega": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notas": forms.Textarea(attrs={"rows": 2}),
        }


class LineaPedidoForm(forms.ModelForm):
    precio_unitario = forms.DecimalField(required=False, max_digits=12, decimal_places=2,
                                         help_text="Vacío = precio de lista")

    class Meta:
        model = LineaPedido
        fields = ["producto", "cantidad", "precio_unitario"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["producto"].queryset = Producto.objects.filter(activo=True, tipo=Producto.Tipo.TERMINADO)

    def clean(self):
        datos = super().clean()
        if datos.get("producto") and datos.get("precio_unitario") in (None, ""):
            datos["precio_unitario"] = datos["producto"].precio_venta
            self.instance.precio_unitario = datos["precio_unitario"]
        return datos


LineasPedidoFormSet = inlineformset_factory(
    PedidoVenta, LineaPedido, form=LineaPedidoForm, extra=4, can_delete=True, min_num=1, validate_min=True
)


@login_required
def lista(request):
    pedidos = PedidoVenta.objects.select_related("cliente").prefetch_related("lineas")
    estado = request.GET.get("estado")
    if estado:
        pedidos = pedidos.filter(estado=estado)
    return render(request, "ventas/lista.html", {"pedidos": pedidos, "estados": PedidoVenta.Estado.choices, "estado": estado})


@requiere_modulo("ventas")
def nuevo(request):
    form = PedidoForm(request.POST or None)
    formset = LineasPedidoFormSet(request.POST or None)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            pedido = form.save(commit=False)
            pedido.numero = services.nuevo_numero()
            pedido.creado_por = request.user
            pedido.save()
            formset.instance = pedido
            formset.save()
        messages.success(request, f"Pedido {pedido.numero} creado.")
        return redirect("pv_detalle", pk=pedido.pk)
    return render(request, "ventas/form.html", {"form": form, "formset": formset})


@login_required
def detalle(request, pk):
    pedido = get_object_or_404(PedidoVenta.objects.select_related("cliente"), pk=pk)
    return render(request, "ventas/detalle.html", {
        "pedido": pedido,
        "lineas": pedido.lineas.select_related("producto__unidad"),
        "despachos": pedido.despachos.prefetch_related("lineas__lote", "lineas__linea_pedido__producto"),
        "faltantes": services.faltantes(pedido) if pedido.estado in (PedidoVenta.Estado.BORRADOR, PedidoVenta.Estado.CONFIRMADO) else [],
    })


@require_POST
@login_required
def accion(request, pk, accion):
    pedido = get_object_or_404(PedidoVenta, pk=pk)
    modulo = "despacho" if accion == "despachar" else "ventas"
    if not puede(request.user, modulo):
        messages.error(request, "Su rol no permite esta acción.")
        return redirect("pv_detalle", pk=pk)
    try:
        resultado = {"confirmar": services.confirmar, "cancelar": services.cancelar, "despachar": services.despachar}[accion](pedido, request.user)
        if accion == "despachar":
            messages.success(request, f"Despacho {resultado.numero} registrado: inventario descontado por lote.")
        else:
            messages.success(request, f"Pedido {pedido.numero}: {pedido.get_estado_display().lower()}.")
    except services.VentaError as e:
        messages.error(request, str(e))
    return redirect("pv_detalle", pk=pk)
