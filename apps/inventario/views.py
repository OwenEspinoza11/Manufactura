from collections import OrderedDict
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from apps.maestros.models import Almacen, Producto

from . import services, trazabilidad
from .models import Lote, Movimiento


@login_required
def existencias(request):
    almacen = Almacen.objects.filter(pk=request.GET.get("almacen")).first() if request.GET.get("almacen") else None
    filas = services.existencias(almacen=almacen, incluir_scrap=bool(almacen))
    q = request.GET.get("q", "").strip().lower()
    if q:
        filas = [f for f in filas if q in f["producto"].codigo.lower() or q in f["producto"].nombre.lower()]
    grupos = OrderedDict()
    for f in filas:
        g = grupos.setdefault(f["producto"].pk, {"producto": f["producto"], "filas": [], "total": Decimal("0"), "valor": Decimal("0")})
        g["filas"].append(f)
        g["total"] += f["cantidad"]
        g["valor"] += f["valor"]
    return render(request, "inventario/existencias.html", {
        "grupos": grupos.values(),
        "valor_total": sum((g["valor"] for g in grupos.values()), Decimal("0")),
        "almacenes": Almacen.objects.all(),
        "almacen": almacen,
        "q": request.GET.get("q", ""),
        "alertas": services.alertas_stock_minimo(),
    })


@login_required
def kardex(request):
    movimientos = Movimiento.objects.select_related("producto__unidad", "lote", "almacen_origen", "almacen_destino", "usuario")
    producto = Producto.objects.filter(pk=request.GET.get("producto")).first() if request.GET.get("producto") else None
    if producto:
        movimientos = movimientos.filter(producto=producto)
    tipo = request.GET.get("tipo")
    if tipo:
        movimientos = movimientos.filter(tipo=tipo)
    pagina = Paginator(movimientos, 50).get_page(request.GET.get("page"))
    return render(request, "inventario/kardex.html", {
        "pagina": pagina, "productos": Producto.objects.all(), "producto": producto,
        "tipos": Movimiento.Tipo.choices, "tipo": tipo,
    })


@login_required
def lotes(request):
    qs = Lote.objects.select_related("producto__unidad", "proveedor")
    estado = request.GET.get("estado")
    if estado:
        qs = qs.filter(estado=estado)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(codigo__icontains=q) | qs.filter(producto__nombre__icontains=q)
    return render(request, "inventario/lotes.html", {
        "lotes": qs[:300], "estados": Lote.Estado.choices, "estado": estado, "q": q,
    })


@login_required
def lote_detalle(request, pk):
    lote = get_object_or_404(Lote.objects.select_related("producto__unidad", "proveedor"), pk=pk)
    return render(request, "inventario/lote_detalle.html", {
        "lote": lote,
        "saldo": services.saldo(lote=lote),
        "ubicaciones": [f for f in services.existencias(producto=lote.producto, incluir_scrap=True) if f["lote"] == lote],
        "atras": trazabilidad.hacia_atras(lote),
        "adelante": trazabilidad.hacia_adelante(lote),
        "movimientos": lote.movimientos.select_related("almacen_origen", "almacen_destino", "usuario"),
        "inspecciones": lote.inspecciones.select_related("inspector"),
        "ncs": lote.no_conformidades.all(),
        "lecturas": lote.lecturas.select_related("sensor").order_by("-fecha")[:20],
    })
