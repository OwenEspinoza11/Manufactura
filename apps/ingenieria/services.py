"""Servicios de ingeniería de producto.

La BOM multinivel se modela con el patrón Composite: cada `NodoBOM` es una hoja
(materia prima / empaque) o un compuesto (semielaborado con su propia BOM), y ambos
responden igual a `costo_total` y `recorrer()`.
"""
from dataclasses import dataclass, field
from decimal import Decimal

from .models import BOM, Ruta

DOS = Decimal("0.01")


def bom_activa(producto):
    return BOM.objects.filter(producto=producto, activa=True).prefetch_related("lineas__componente").order_by("-version").first()


def ruta_activa(producto):
    return Ruta.objects.filter(producto=producto, activa=True).prefetch_related("operaciones__centro").order_by("-version").first()


def costo_conversion_unitario(producto):
    ruta = ruta_activa(producto)
    if not ruta:
        return Decimal("0")
    total = sum((op.tiempo_estandar_min / 60 * op.centro.costo_hora for op in ruta.operaciones.all()), Decimal("0"))
    return total / ruta.cantidad_lote


def costo_estandar(producto, _visitados=None):
    """Costo estándar unitario: materiales (recursivo por niveles) + conversión según la ruta."""
    visitados = _visitados or set()
    if producto.pk in visitados:
        raise ValueError(f"Ciclo detectado en la BOM de {producto}")
    bom = bom_activa(producto)
    if not bom:
        return producto.costo_estandar
    visitados = visitados | {producto.pk}
    materiales = sum(
        (linea.cantidad_para(1) * costo_estandar(linea.componente, visitados) for linea in bom.lineas.all()),
        Decimal("0"),
    )
    return materiales + costo_conversion_unitario(producto)


@dataclass
class NodoBOM:
    producto: object
    cantidad: Decimal
    nivel: int
    hijos: list = field(default_factory=list)

    @property
    def es_compuesto(self):
        return bool(self.hijos)

    @property
    def costo_unitario(self):
        if self.es_compuesto:
            return sum((h.costo_total for h in self.hijos), Decimal("0")) / self.cantidad + costo_conversion_unitario(self.producto)
        return self.producto.costo_estandar

    @property
    def costo_total(self):
        return (self.costo_unitario * self.cantidad).quantize(DOS)

    def recorrer(self):
        yield self
        for hijo in self.hijos:
            yield from hijo.recorrer()


def explotar(producto, cantidad, nivel=0, _visitados=frozenset()):
    """Explosión recursiva de la BOM para `cantidad` unidades del producto."""
    if producto.pk in _visitados:
        raise ValueError(f"Ciclo detectado en la BOM de {producto}")
    nodo = NodoBOM(producto=producto, cantidad=Decimal(cantidad), nivel=nivel)
    bom = bom_activa(producto)
    if bom:
        for linea in bom.lineas.all():
            nodo.hijos.append(
                explotar(linea.componente, linea.cantidad_para(cantidad), nivel + 1, _visitados | {producto.pk})
            )
    return nodo
