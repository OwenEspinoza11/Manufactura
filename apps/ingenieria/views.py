from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import BOM, Ruta
from .services import costo_estandar, explotar


@login_required
def bom_lista(request):
    boms = BOM.objects.select_related("producto", "producto__unidad").prefetch_related("lineas")
    rutas = Ruta.objects.select_related("producto").prefetch_related("operaciones__centro")
    return render(request, "ingenieria/bom_lista.html", {"boms": boms, "rutas": rutas})


@login_required
def bom_detalle(request, pk):
    bom = get_object_or_404(BOM.objects.select_related("producto__unidad"), pk=pk)
    try:
        cantidad = Decimal(request.GET.get("cantidad") or bom.cantidad_base)
    except InvalidOperation:
        cantidad = bom.cantidad_base
    arbol = explotar(bom.producto, cantidad)
    ruta = bom.producto.rutas.filter(activa=True).prefetch_related("operaciones__centro").first()
    operaciones = [(op, op.tiempo_para(cantidad)) for op in ruta.operaciones.all()] if ruta else []
    return render(request, "ingenieria/bom_detalle.html", {
        "bom": bom,
        "cantidad": cantidad,
        "nodos": list(arbol.recorrer()),
        "arbol": arbol,
        "ruta": ruta,
        "operaciones": operaciones,
        "tiempo_total": sum((t for _, t in operaciones), Decimal("0")),
        "costo_unitario": costo_estandar(bom.producto),
    })
