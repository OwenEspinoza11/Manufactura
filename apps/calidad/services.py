"""Control de calidad por lote.

Inspección aprobada  -> libera el lote (y cierra la NC si venía de retrabajo).
Inspección rechazada -> abre una No Conformidad automáticamente.
La disposición de la NC usa el patrón Strategy: cada disposición sabe qué hacer con el lote y el inventario.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.core.models import siguiente_numero
from apps.inventario.models import Lote, Movimiento
from apps.inventario.services import existencias, registrar_movimiento, saldo
from apps.maestros.models import Almacen

from .models import Inspeccion, NoConformidad, ParametroCalidad, ResultadoInspeccion


class CalidadError(Exception):
    pass


def parametros_para(lote, etapa):
    return ParametroCalidad.objects.filter(producto=lote.producto, etapa=etapa, activo=True)


@transaction.atomic
def registrar_inspeccion(lote, etapa, valores, inspector=None, fecha=None, observaciones=""):
    """`valores`: {parametro_id: Decimal}. Devuelve (inspeccion, no_conformidad | None)."""
    if lote.estado == Lote.Estado.RECHAZADO:
        raise CalidadError("El lote está rechazado; no admite nuevas inspecciones.")
    orden = getattr(lote, "orden_produccion", None) if lote.origen == Lote.Origen.PRODUCCION else None
    if orden is not None and orden.estado != orden.Estado.TERMINADA:
        raise CalidadError(f"La orden {orden.numero} aún no termina; el lote se inspecciona al cerrarla.")
    parametros = list(parametros_para(lote, etapa))
    if not parametros:
        raise CalidadError("El producto no tiene parámetros de calidad para esa etapa.")
    faltan = [p.nombre for p in parametros if valores.get(p.pk) is None]
    if faltan:
        raise CalidadError(f"Faltan valores para: {', '.join(faltan)}.")
    fecha = fecha or timezone.now()
    inspeccion = Inspeccion(
        numero=siguiente_numero(Inspeccion, "QC-"), lote=lote, etapa=etapa, orden=orden, fecha=fecha,
        inspector=inspector, observaciones=observaciones, creado_por=inspector,
    )
    resultados = [ResultadoInspeccion(parametro=p, valor=Decimal(valores[p.pk]), conforme=p.es_conforme(Decimal(valores[p.pk])))
                  for p in parametros]
    inspeccion.resultado = Inspeccion.Resultado.APROBADO if all(r.conforme for r in resultados) else Inspeccion.Resultado.RECHAZADO
    inspeccion.save()
    for r in resultados:
        r.inspeccion = inspeccion
    ResultadoInspeccion.objects.bulk_create(resultados)

    nc = None
    if inspeccion.resultado == Inspeccion.Resultado.APROBADO:
        if lote.estado in (Lote.Estado.CUARENTENA, Lote.Estado.RETRABAJO):
            lote.estado = Lote.Estado.LIBERADO
            lote.save(update_fields=["estado", "actualizado_en"])
        for pendiente in lote.no_conformidades.filter(estado=NoConformidad.Estado.EN_RETRABAJO):
            pendiente.estado = NoConformidad.Estado.CERRADA
            pendiente.fecha_cierre = fecha
            pendiente.comentario_disposicion += f"\nRetrabajo verificado con la inspección {inspeccion.numero}."
            pendiente.save()
    else:
        fuera = [f"{r.parametro.nombre} = {r.valor.normalize()} (esperado {r.parametro.rango})" for r in resultados if not r.conforme]
        lote.estado = Lote.Estado.CUARENTENA
        lote.save(update_fields=["estado", "actualizado_en"])
        nc = NoConformidad.objects.create(
            numero=siguiente_numero(NoConformidad, "NC-"), inspeccion=inspeccion, lote=lote,
            descripcion="Fuera de especificación: " + "; ".join(fuera), cantidad_afectada=saldo(lote=lote),
            creado_por=inspector,
        )
    return inspeccion, nc


# --- Strategy: disposición de no conformidades ------------------------------------------

class Disposicion:
    codigo = None

    def aplicar(self, nc, usuario, fecha):
        raise NotImplementedError


class DisposicionScrap(Disposicion):
    codigo = NoConformidad.Disposicion.SCRAP

    def aplicar(self, nc, usuario, fecha):
        destino = Almacen.por_tipo(Almacen.Tipo.SCRAP)
        total = Decimal("0")
        for fila in existencias(producto=nc.lote.producto):
            if fila["lote"] == nc.lote:
                registrar_movimiento(
                    tipo=Movimiento.Tipo.SCRAP, producto=nc.lote.producto, cantidad=fila["cantidad"], lote=nc.lote,
                    origen=fila["almacen"], destino=destino, referencia=nc.numero, usuario=usuario, fecha=fecha,
                )
                total += fila["cantidad"]
        nc.lote.estado = Lote.Estado.RECHAZADO
        nc.cantidad_scrap = total
        nc.estado = NoConformidad.Estado.CERRADA
        nc.fecha_cierre = fecha


class DisposicionRetrabajo(Disposicion):
    codigo = NoConformidad.Disposicion.RETRABAJO

    def aplicar(self, nc, usuario, fecha):
        # El lote queda retenido hasta que una nueva inspección lo apruebe (cierra la NC automáticamente)
        nc.lote.estado = Lote.Estado.RETRABAJO
        nc.estado = NoConformidad.Estado.EN_RETRABAJO


class DisposicionLiberacion(Disposicion):
    codigo = NoConformidad.Disposicion.LIBERACION

    def aplicar(self, nc, usuario, fecha):
        nc.lote.estado = Lote.Estado.LIBERADO
        nc.estado = NoConformidad.Estado.CERRADA
        nc.fecha_cierre = fecha


ESTRATEGIAS = {e.codigo: e() for e in (DisposicionScrap, DisposicionRetrabajo, DisposicionLiberacion)}


@transaction.atomic
def disponer(nc, disposicion, usuario=None, comentario="", causa_raiz="", fecha=None):
    if nc.estado != NoConformidad.Estado.ABIERTA:
        raise CalidadError("Solo se dispone una no conformidad abierta.")
    estrategia = ESTRATEGIAS.get(disposicion)
    if not estrategia:
        raise CalidadError("Disposición no válida.")
    if not comentario:
        raise CalidadError("Justifique la disposición.")
    fecha = fecha or timezone.now()
    estrategia.aplicar(nc, usuario, fecha)
    nc.disposicion = disposicion
    nc.fecha_disposicion = fecha
    nc.responsable_disposicion = usuario
    nc.comentario_disposicion = comentario
    if causa_raiz:
        nc.causa_raiz = causa_raiz
    nc.lote.save(update_fields=["estado", "actualizado_en"])
    nc.save()
    return nc
