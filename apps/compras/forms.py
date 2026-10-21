from django import forms
from django.forms import inlineformset_factory

from apps.maestros.models import Producto

from .models import LineaOrdenCompra, OrdenCompra


class OrdenCompraForm(forms.ModelForm):
    class Meta:
        model = OrdenCompra
        fields = ["proveedor", "fecha", "fecha_esperada", "almacen_destino", "notas"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "fecha_esperada": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notas": forms.Textarea(attrs={"rows": 2}),
        }


class LineaCompraForm(forms.ModelForm):
    class Meta:
        model = LineaOrdenCompra
        fields = ["producto", "cantidad", "precio_unitario"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["producto"].queryset = Producto.objects.filter(
            activo=True, tipo__in=[Producto.Tipo.MATERIA_PRIMA, Producto.Tipo.EMPAQUE]
        ).select_related("unidad")


LineasCompraFormSet = inlineformset_factory(
    OrdenCompra, LineaOrdenCompra, form=LineaCompraForm, extra=5, can_delete=True, min_num=1, validate_min=True
)
