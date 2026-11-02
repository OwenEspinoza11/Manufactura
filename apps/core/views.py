from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.calidad.models import Inspeccion, NoConformidad
from apps.compras.models import OrdenCompra
from apps.iiot.models import Alerta
from apps.inventario.models import Lote
from apps.inventario.services import alertas_stock_minimo
from apps.kpi import services as kpi
from apps.maestros.models import Producto
from apps.produccion.models import OrdenProduccion
from apps.ventas.models import PedidoVenta


def _saludo():
    hora = timezone.localtime().hour
    return "Buenos días" if hora < 12 else "Buenas tardes" if hora < 19 else "Buenas noches"


@login_required
def inicio(request):
    en_proceso = (OrdenProduccion.objects.filter(estado=OrdenProduccion.Estado.EN_PROCESO)
                  .select_related("producto", "lote")
                  .annotate(ops=Count("registros"), hechas=Count("registros", filter=Q(registros__estado="TER"))))
    por_inspeccionar = Lote.objects.filter(estado__in=[Lote.Estado.CUARENTENA, Lote.Estado.RETRABAJO]).exclude(
        orden_produccion__estado=OrdenProduccion.Estado.EN_PROCESO)
    pendientes = [
        {"icono": "bi-box-arrow-in-down", "tono": "t-info", "texto": "Compras por recibir", "detalle": "órdenes confirmadas",
         "n": OrdenCompra.objects.filter(estado__in=["CON", "PAR"]).count(), "url": "oc_lista", "filtro": "?estado=CON"},
        {"icono": "bi-clipboard2-check", "tono": "t-warn", "texto": "Lotes por inspeccionar", "detalle": "en cuarentena o retrabajo",
         "n": por_inspeccionar.count(), "url": "inspecciones", "filtro": ""},
        {"icono": "bi-play-circle", "tono": "t-brand", "texto": "Órdenes por iniciar", "detalle": "borrador o confirmadas",
         "n": OrdenProduccion.objects.filter(estado__in=["BOR", "CON"]).count(), "url": "op_lista", "filtro": "?estado=CON"},
        {"icono": "bi-truck", "tono": "t-lav", "texto": "Pedidos por despachar", "detalle": "borrador o confirmados",
         "n": PedidoVenta.objects.filter(estado__in=["BOR", "CON"]).count(), "url": "pv_lista", "filtro": "?estado=CON"},
        {"icono": "bi-exclamation-octagon", "tono": "t-bad", "texto": "No conformidades abiertas", "detalle": "requieren disposición",
         "n": NoConformidad.objects.exclude(estado=NoConformidad.Estado.CERRADA).count(), "url": "nc_lista", "filtro": ""},
    ]
    return render(request, "core/inicio.html", {
        **kpi.resumen(),
        "saludo": _saludo(),
        "semanal": kpi.produccion_semanal(),
        "en_proceso": en_proceso,
        "pendientes": pendientes,
        "stock_bajo": alertas_stock_minimo(),
        "alertas_iiot": Alerta.objects.filter(atendida=False).select_related("sensor", "orden")[:5],
    })


@login_required
def buscar(request):
    """Búsqueda global por número de documento, código de lote o producto."""
    q = request.GET.get("q", "").strip()
    resultados = []
    if q:
        fuentes = [
            ("Lote", Lote.objects.filter(codigo__icontains=q).select_related("producto"), "lote_detalle", lambda o: o.producto.nombre),
            ("Orden de compra", OrdenCompra.objects.filter(numero__icontains=q).select_related("proveedor"), "oc_detalle", lambda o: o.proveedor.nombre),
            ("Orden de producción", OrdenProduccion.objects.filter(numero__icontains=q).select_related("producto"), "op_detalle", lambda o: o.producto.nombre),
            ("Pedido de venta", PedidoVenta.objects.filter(numero__icontains=q).select_related("cliente"), "pv_detalle", lambda o: o.cliente.nombre),
            ("No conformidad", NoConformidad.objects.filter(numero__icontains=q).select_related("lote"), "nc_detalle", lambda o: o.lote.codigo),
            ("Inspección", Inspeccion.objects.filter(numero__icontains=q).select_related("lote"), "inspeccion_detalle", lambda o: o.lote.codigo),
        ]
        for tipo, qs, ruta, detalle in fuentes:
            for o in qs[:20]:
                resultados.append({"tipo": tipo, "obj": o, "ruta": ruta, "detalle": detalle(o)})
        for p in Producto.objects.filter(Q(codigo__icontains=q) | Q(nombre__icontains=q))[:20]:
            resultados.append({"tipo": "Producto", "obj": p, "ruta": "productos_editar", "detalle": p.get_tipo_display()})
        if len(resultados) == 1:
            r = resultados[0]
            return redirect(r["ruta"], pk=r["obj"].pk)
    return render(request, "core/buscar.html", {"q": q, "resultados": resultados})
