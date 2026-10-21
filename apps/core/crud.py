"""CRUD genérico para catálogos (datos maestros).

Un `Catalogo` describe un modelo (columnas, campos editables, permisos) y genera
sus vistas de lista / alta / edición reutilizando dos plantillas comunes.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.forms import modelform_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path

from .permisos import puede, requiere_modulo


def _valor(obj, atributo):
    display = getattr(obj, f"get_{atributo}_display", None)
    if display:
        return display()
    valor = obj
    for parte in atributo.split("."):
        valor = getattr(valor, parte, None)
        if valor is None:
            return ""
    return valor() if callable(valor) else valor


class Catalogo:
    def __init__(self, modelo, slug, columnas, campos, modulo="maestros", busqueda=("codigo", "nombre"), widgets=None):
        self.modelo = modelo
        self.slug = slug
        self.columnas = columnas  # [(etiqueta, atributo), ...]
        self.campos = campos
        self.modulo = modulo
        self.busqueda = busqueda
        self.form_class = modelform_factory(modelo, fields=campos, widgets=widgets or {})

    @property
    def titulo(self):
        return self.modelo._meta.verbose_name_plural.capitalize()

    def lista(self, request):
        qs = self.modelo.objects.all()
        q = request.GET.get("q", "").strip()
        if q:
            filtro = Q()
            for campo in self.busqueda:
                filtro |= Q(**{f"{campo}__icontains": q})
            qs = qs.filter(filtro)
        filas = [(obj.pk, [_valor(obj, a) for _, a in self.columnas]) for obj in qs[:500]]
        return render(request, "core/lista.html", {
            "cat": self,
            "encabezados": [e for e, _ in self.columnas],
            "filas": filas,
            "q": q,
            "editable": puede(request.user, self.modulo),
        })

    def formulario(self, request, pk=None):
        obj = get_object_or_404(self.modelo, pk=pk) if pk else None
        form = self.form_class(request.POST or None, instance=obj)
        if request.method == "POST" and form.is_valid():
            nuevo = form.save(commit=False)
            if hasattr(nuevo, "creado_por_id") and not nuevo.creado_por_id:
                nuevo.creado_por = request.user
            nuevo.save()
            messages.success(request, f"{self.modelo._meta.verbose_name.capitalize()} guardado: {nuevo}")
            return redirect(f"{self.slug}_lista")
        return render(request, "core/form.html", {"cat": self, "form": form, "obj": obj})

    def urls(self):
        return [
            path(f"{self.slug}/", login_required(self.lista), name=f"{self.slug}_lista"),
            path(f"{self.slug}/nuevo/", requiere_modulo(self.modulo)(self.formulario), name=f"{self.slug}_nuevo"),
            path(f"{self.slug}/<int:pk>/", requiere_modulo(self.modulo)(self.formulario), name=f"{self.slug}_editar"),
        ]
