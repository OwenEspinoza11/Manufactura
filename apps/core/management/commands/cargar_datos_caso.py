"""Carga los datos del caso Blancos Aromáticos.

  python manage.py cargar_datos_caso               -> solo datos maestros, BOM, rutas, calidad, IIoT y usuarios
  python manage.py cargar_datos_caso --historial   -> además, 6 semanas de operación simulada

El historial NO inserta filas "a mano": ejecuta los mismos servicios transaccionales que usa la
interfaz (compra -> recepción -> producción -> calidad -> venta), con fechas pasadas, para que los
KPI se calculen sobre transacciones reales del sistema.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.calidad import services as calidad
from apps.calidad.models import NoConformidad, ParametroCalidad
from apps.compras import services as compras
from apps.compras.models import LineaOrdenCompra, OrdenCompra
from apps.core.permisos import ROLES
from apps.iiot.models import Alerta, Dispositivo, Lectura, Sensor
from apps.ingenieria.models import BOM, LineaBOM, Operacion, Ruta
from apps.inventario.services import TIPOS_ALMACEN_CONSUMO, disponible
from apps.maestros.models import Almacen, CentroTrabajo, Cliente, Producto, Proveedor, UnidadMedida
from apps.produccion import services as produccion
from apps.ventas import services as ventas
from apps.ventas.models import LineaPedido, PedidoVenta

D = Decimal
CLAVE_DEMO = "Blancos2026!"

# (usuario, nombre, apellido, roles, superusuario)
EQUIPO = [
    ("bmorales", "Bricio", "Morales", ["Gerencia", "Administrador"], False),
    ("ddavila", "Dylan", "Davila", ["Administrador"], True),
    ("oespinoza", "Owen", "Espinoza", ["Compras", "Almacén"], False),
    ("kperyman", "Kevin", "Peryman", ["Producción"], False),
    ("asalazar", "Ashly", "Salazar", ["Calidad"], False),
    ("azamora", "Amaru", "Zamora", ["Gerencia", "Ventas"], False),
]

UNIDADES = [("L", "Litro"), ("kg", "Kilogramo"), ("und", "Unidad"), ("g", "Gramo")]

ALMACENES = [
    ("ALM-MP", "Bodega de materias primas y empaque", "MP", "Nave 1, estante A-D"),
    ("ALM-ACO", "Acopio de aceite de cocina usado", "ACO", "Patio trasero, bidones de 200 L"),
    ("ALM-PP", "Tanques de semielaborados", "PP", "Área de proceso"),
    ("ALM-PT", "Bodega de producto terminado", "PT", "Nave 2"),
    ("ALM-SCR", "Scrap y mermas", "SCR", "Zona de residuos controlados"),
]

CENTROS = [
    ("DOS-01", "Estación de dosificación y pesaje", "Balanza 150 kg", "120"),
    ("TQ-01", "Tanque mezclador T-01", "500 L, agitador 450 RPM", "180"),
    ("FIL-01", "Filtro / decantador de aceite", "200 L por ciclo", "90"),
    ("REA-01", "Reactor de saponificación R-01", "200 L con chaqueta térmica", "220"),
    ("ENV-01", "Línea de envasado por gravedad", "≈ 2 botellas/min", "200"),
    ("LAB-01", "Laboratorio de control de calidad", "pHmetro, viscosímetro", "150"),
]

# codigo, nombre, tipo, linea, udm, costo, precio, stock_min, vida_util, reciclado
PRODUCTOS = [
    ("MP-AGUA", "Agua tratada (ósmosis)", "MP", "GEN", "L", "0.60", "0", "300", None, False),
    ("MP-QUAT", "Cloruro de benzalconio 50% (amonio cuaternario)", "MP", "DESINF", "L", "185", "0", "10", 730, False),
    ("MP-SOLU", "Solubilizante / estabilizante (polisorbato 20)", "MP", "DESINF", "L", "140", "0", "5", 730, False),
    ("MP-FRLAV", "Fragancia lavanda", "MP", "DESINF", "L", "650", "0", "2", 365, False),
    ("MP-FRLIM", "Fragancia limón", "MP", "ECO", "L", "610", "0", "2", 365, False),
    ("MP-COLAZ", "Colorante azul cosmético", "MP", "DESINF", "L", "950", "0", "0.3", 730, False),
    ("MP-ACUSA", "Aceite de cocina usado (acopio)", "MP", "ECO", "L", "4.00", "0", "60", 60, True),
    ("MP-KOH", "Hidróxido de potasio (KOH) en escamas", "MP", "ECO", "kg", "95", "0", "10", 730, False),
    ("MP-ACCIT", "Ácido cítrico (ajuste de pH)", "MP", "GEN", "kg", "70", "0", "2", 730, False),
    ("EMP-BOT1L", "Botella PET 1 L con tapa", "EMP", "GEN", "und", "9.50", "0", "300", None, False),
    ("EMP-ETQ", "Etiqueta con código de lote", "EMP", "GEN", "und", "1.20", "0", "300", None, False),
    ("EMP-CAJA4", "Caja de cartón para 4 unidades", "EMP", "GEN", "und", "12", "0", "50", None, False),
    ("SE-BDES", "Base desinfectante", "SE", "DESINF", "L", "0", "0", "0", 180, False),
    ("SE-ACFIL", "Aceite vegetal filtrado", "SE", "ECO", "L", "0", "0", "0", 90, False),
    ("SE-BJAB", "Base jabonosa de aceite reciclado", "SE", "ECO", "L", "0", "0", "0", 180, False),
    ("PT-DES1L", "Desinfectante aromático lavanda 1 L", "PT", "DESINF", "und", "0", "75", "100", 365, False),
    ("PT-ECO1L", "Jabón líquido multiusos ECO 1 L", "PT", "ECO", "und", "0", "85", "60", 365, False),
]

PROVEEDORES = [
    ("PRV-001", "Distribuidora Química El Lago, S.A.", "QUI", "Marta López", "2295-1100"),
    ("PRV-002", "Esencias del Trópico", "QUI", "Julio Arana", "2278-4410"),
    ("PRV-003", "Envases Plásticos San Benito", "EMP", "Karla Ruiz", "2295-3321"),
    ("PRV-004", "Agua Pura La Concepción", "QUI", "Pedro Matus", "8840-1020"),
    ("PRV-005", "Red de acopio Fritangas de Tipitapa", "ACO", "Doña Rosa Téllez", "8712-5566"),
    ("PRV-006", "Restaurante El Mirador del Lago", "ACO", "Luis Cano", "8655-2010"),
]

CLIENTES = [
    ("CLI-001", "Distribuidora Hermanos Ruiz", "DIS", "Ernesto Ruiz", "8890-2233"),
    ("CLI-002", "Abarrotes Doña Carmen", "NEG", "Carmen Sevilla", "8765-4321"),
    ("CLI-003", "Hotel Brisas de Tipitapa", "NEG", "Gerencia de compras", "2295-7788"),
    ("CLI-004", "Ferretería y Limpieza El Ahorro", "NEG", "Sergio Pérez", "8456-9988"),
    ("CLI-005", "Distribuidora del Norte, S.A.", "DIS", "Ana Rivas", "2772-1144"),
    ("CLI-006", "Venta directa al hogar (mostrador)", "HOG", "", ""),
]

# producto: (cantidad_base, [(componente, cantidad, merma%)], notas)
BOMS = {
    "SE-BDES": ("100", [("MP-AGUA", "96.5", "0"), ("MP-QUAT", "2.0", "0"), ("MP-SOLU", "1.5", "0")],
                "Nivel 2 de la BOM de la Entrega 1. Cantidades de prueba: la Entrega 1 indicaba 'según formulación validada'."),
    "PT-DES1L": ("100", [("SE-BDES", "100", "0"), ("MP-FRLAV", "0.50", "0"), ("MP-COLAZ", "0.05", "0"),
                         ("EMP-BOT1L", "100", "0"), ("EMP-ETQ", "100", "0"), ("EMP-CAJA4", "25", "0")],
                 "Producto piloto (Entrega 1). Se agregan etiqueta con código de lote y caja de 4 unidades (TO-BE)."),
    "SE-ACFIL": ("100", [("MP-ACUSA", "100", "12")], "Merma de 12 % por sedimentos y agua retirados en la decantación."),
    "SE-BJAB": ("100", [("SE-ACFIL", "25", "0"), ("MP-KOH", "5.5", "0"), ("MP-AGUA", "70", "0")],
                "Saponificación en caliente del aceite filtrado con KOH (jabón potásico líquido)."),
    "PT-ECO1L": ("100", [("SE-BJAB", "99", "0"), ("MP-FRLIM", "0.6", "0"), ("EMP-BOT1L", "100", "0"),
                         ("EMP-ETQ", "100", "0"), ("EMP-CAJA4", "25", "0")],
                 "Segunda línea (ampliación de alcance Entrega 2): producto con aceite de cocina reciclado."),
}

# producto: (cantidad_lote, [(secuencia, codigo, nombre, descripcion, centro, minutos)])
RUTAS = {
    "SE-BDES": ("100", [
        (10, "OP-10", "Preparación y dosificación", "Preparar área, verificar materiales y dosificar componentes.", "DOS-01", "30"),
        (20, "OP-20", "Mezclado", "Incorporar y mezclar los componentes de la base hasta homogeneizar.", "TQ-01", "60"),
    ]),
    "PT-DES1L": ("100", [
        (30, "OP-30", "Ajuste y control", "Aromatizar, colorear, ajustar según formulación y verificar pH/viscosidad.", "TQ-01", "30"),
        (40, "OP-40", "Envasado y etiquetado", "Envasar, identificar lote y preparar producto para almacén.", "ENV-01", "60"),
    ]),
    "SE-ACFIL": ("100", [
        (10, "OP-10", "Filtrado y decantación", "Retirar sólidos y agua del aceite usado.", "FIL-01", "90"),
    ]),
    "SE-BJAB": ("100", [
        (10, "OP-10", "Preparación de solución alcalina", "Disolver KOH en agua tratada con EPP completo.", "DOS-01", "20"),
        (20, "OP-20", "Saponificación", "Reacción en caliente (70–85 °C) con agitación.", "REA-01", "90"),
        (30, "OP-30", "Dilución y reposo", "Diluir la pasta jabonosa y dejar reposar.", "REA-01", "40"),
    ]),
    "PT-ECO1L": ("100", [
        (10, "OP-10", "Aromatizado y ajuste de pH", "Incorporar fragancia y verificar pH.", "TQ-01", "25"),
        (20, "OP-20", "Envasado y etiquetado", "Envasar, etiquetar con código de lote y encajar.", "ENV-01", "60"),
    ]),
}

# producto, etapa, nombre, unidad, min, max
PARAMETROS = [
    ("MP-ACUSA", "REC", "Índice de acidez", "mg KOH/g", None, "4.0"),
    ("MP-ACUSA", "REC", "Humedad e impurezas", "%", None, "2.0"),
    ("PT-DES1L", "FIN", "pH", "", "6.5", "7.5"),
    ("PT-DES1L", "FIN", "Viscosidad", "cP", "10", "50"),
    ("PT-DES1L", "FIN", "Densidad", "g/mL", "0.990", "1.030"),
    ("SE-BJAB", "PRO", "pH", "", "9.0", "10.5"),
    ("SE-BJAB", "PRO", "Alcalinidad libre", "%", None, "0.10"),
    ("PT-ECO1L", "FIN", "pH", "", "9.0", "10.5"),
    ("PT-ECO1L", "FIN", "Viscosidad", "cP", "200", "800"),
]

PREFIJO_MQTT = "blancosaromaticos/planta"
# dispositivo, nombre, centro, [(codigo, nombre, tipo, unidad, topico, min, max)]
DISPOSITIVOS = [
    ("ESP32-T01", "ESP32 tanque mezclador T-01", "TQ-01", [
        ("TQ1-NIVEL", "Nivel tanque T-01 (HC-SR04)", "NIV", "%", "tanque1/nivel", 5, 95),
        ("TQ1-PH", "pH en tanque T-01", "PH", "pH", "tanque1/ph", 6.0, 11.0),
    ]),
    ("ESP32-R01", "ESP32 reactor de saponificación R-01", "REA-01", [
        ("REA1-TEMP", "Temperatura reactor R-01", "TEM", "°C", "reactor1/temperatura", 60, 88),
    ]),
    ("ESP32-ENV", "ESP32 línea de envasado (sensor IR)", "ENV-01", [
        ("ENV-CONTEO", "Conteo de botellas envasadas", "CON", "und", "envasado/conteo", None, None),
    ]),
]


class Command(BaseCommand):
    help = "Carga los datos del caso Blancos Aromáticos (maestros + historial opcional de 6 semanas)."

    def add_arguments(self, parser):
        parser.add_argument("--si-vacia", action="store_true", help="No hace nada si ya existen productos.")
        parser.add_argument("--historial", action="store_true", help="Genera 6 semanas de transacciones.")

    def handle(self, *args, **opciones):
        if opciones["si_vacia"] and Producto.objects.exists():
            self.stdout.write("La base ya tiene datos del caso; no se recarga.")
            return
        with transaction.atomic():
            self.maestros()
        self.stdout.write(self.style.SUCCESS("Datos maestros cargados."))
        if opciones["historial"]:
            with transaction.atomic():
                Historial(self.stdout).ejecutar()
            self.stdout.write(self.style.SUCCESS("Historial de 6 semanas generado."))

    def maestros(self):
        for rol in ROLES:
            Group.objects.get_or_create(name=rol)
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "", CLAVE_DEMO, first_name="Administrador")
        for usuario, nombre, apellido, roles, superusuario in EQUIPO:
            u, creado = User.objects.get_or_create(username=usuario, defaults={
                "first_name": nombre, "last_name": apellido, "is_staff": True, "is_superuser": superusuario})
            if creado:
                u.set_password(CLAVE_DEMO)
                u.save()
            u.groups.set(Group.objects.filter(name__in=roles))

        udm = {c: UnidadMedida.objects.update_or_create(codigo=c, defaults={"nombre": n})[0] for c, n in UNIDADES}
        for c, n, t, ubic in ALMACENES:
            Almacen.objects.update_or_create(codigo=c, defaults={"nombre": n, "tipo": t, "ubicacion": ubic})
        centros = {}
        for c, n, cap, costo in CENTROS:
            centros[c] = CentroTrabajo.objects.update_or_create(codigo=c, defaults={"nombre": n, "capacidad": cap, "costo_hora": D(costo)})[0]
        prod = {}
        for c, n, t, linea, u, costo, precio, minimo, vida, recic in PRODUCTOS:
            prod[c] = Producto.objects.update_or_create(codigo=c, defaults={
                "nombre": n, "tipo": t, "linea": linea, "unidad": udm[u], "costo_estandar": D(costo),
                "precio_venta": D(precio), "stock_minimo": D(minimo), "vida_util_dias": vida, "es_reciclado": recic})[0]
        for c, n, t, contacto, tel in PROVEEDORES:
            Proveedor.objects.update_or_create(codigo=c, defaults={"nombre": n, "tipo": t, "contacto": contacto, "telefono": tel,
                                                                    "direccion": "Tipitapa / Managua, Nicaragua"})
        for c, n, t, contacto, tel in CLIENTES:
            Cliente.objects.update_or_create(codigo=c, defaults={"nombre": n, "tipo": t, "contacto": contacto, "telefono": tel})

        for codigo, (base, lineas, notas) in BOMS.items():
            bom, _ = BOM.objects.update_or_create(producto=prod[codigo], version="1.0", defaults={"cantidad_base": D(base), "notas": notas})
            bom.lineas.all().delete()
            for i, (comp, cant, merma) in enumerate(lineas, start=1):
                LineaBOM.objects.create(bom=bom, secuencia=i * 10, componente=prod[comp], cantidad=D(cant), merma_pct=D(merma))
        for codigo, (cantidad, ops) in RUTAS.items():
            ruta, _ = Ruta.objects.update_or_create(producto=prod[codigo], version="1.0", defaults={"cantidad_lote": D(cantidad)})
            if not ruta.operaciones.exists():
                for sec, cod, nombre, desc, centro, minutos in ops:
                    Operacion.objects.create(ruta=ruta, secuencia=sec, codigo=cod, nombre=nombre, descripcion=desc,
                                             centro=centros[centro], tiempo_estandar_min=D(minutos))
        for p, etapa, nombre, unidad, mn, mx in PARAMETROS:
            ParametroCalidad.objects.update_or_create(producto=prod[p], etapa=etapa, nombre=nombre, defaults={
                "unidad": unidad, "minimo": D(mn) if mn else None, "maximo": D(mx) if mx else None})
        for codigo, nombre, centro, sensores in DISPOSITIVOS:
            disp, _ = Dispositivo.objects.update_or_create(codigo=codigo, defaults={"nombre": nombre, "centro": centros[centro]})
            for sc, sn, tipo, unidad, topico, mn, mx in sensores:
                Sensor.objects.update_or_create(codigo=sc, defaults={"dispositivo": disp, "nombre": sn, "tipo": tipo, "unidad": unidad,
                                                                     "topico": f"{PREFIJO_MQTT}/{topico}", "minimo": mn, "maximo": mx})


MOTIVOS_PARO = ["Falta de material en línea", "Ajuste del agitador", "Limpieza no programada",
                "Cambio de formato de envase", "Corte de energía", "Espera de resultado de laboratorio"]


class Historial:
    """Seis semanas de operación ejecutadas con los servicios del ERP (fechas pasadas)."""

    def __init__(self, stdout):
        self.out = stdout
        self.rng = random.Random(2026)
        self.ahora = timezone.now()
        hoy = timezone.localtime(self.ahora).replace(hour=0, minute=0, second=0, microsecond=0)
        self.base = hoy - timedelta(days=42)
        self.p = {p.codigo: p for p in Producto.objects.all()}
        self.u = {u.username: u for u in User.objects.all()}
        self.sensores = {s.codigo: s for s in Sensor.objects.select_related("dispositivo__centro")}
        self.param = {(p.producto.codigo, p.etapa, p.nombre): p for p in ParametroCalidad.objects.select_related("producto")}

    def t(self, dia, hora, minuto=0):
        return self.base + timedelta(days=dia, hours=hora, minutes=minuto)

    # --- compras --------------------------------------------------------------------
    def comprar(self, proveedor, lineas, dia, dia_recepcion=None, almacen="ALM-MP", recibir=True):
        oc = OrdenCompra.objects.create(
            numero=compras.nuevo_numero_oc(), proveedor=Proveedor.objects.get(codigo=proveedor),
            fecha=self.t(dia, 8).date(), fecha_esperada=self.t(dia_recepcion or dia + 1, 8).date(),
            almacen_destino=Almacen.objects.get(codigo=almacen), creado_por=self.u["oespinoza"],
        )
        for codigo, cantidad in lineas:
            precio = (self.p[codigo].costo_estandar * D(str(self.rng.uniform(0.96, 1.06)))).quantize(D("0.01"))
            LineaOrdenCompra.objects.create(orden=oc, producto=self.p[codigo], cantidad=D(str(cantidad)), precio_unitario=precio)
        compras.confirmar(oc)
        if recibir:
            rec = compras.recibir(oc, {l.pk: {"cantidad": l.cantidad, "lote_proveedor": f"P{self.rng.randint(1000, 9999)}"}
                                       for l in oc.lineas.all()},
                                  usuario=self.u["oespinoza"], fecha=self.t(dia_recepcion if dia_recepcion is not None else dia + 1, 9))
            return oc, [lr.lote for lr in rec.lineas.all()]
        return oc, []

    def acopio_aceite(self, proveedor, litros, dia, acidez, humedad):
        _, lotes = self.comprar(proveedor, [("MP-ACUSA", litros)], dia, dia, almacen="ALM-ACO")
        return self.inspeccionar(lotes[0], "REC", {"Índice de acidez": acidez, "Humedad e impurezas": humedad}, self.t(dia, 10))

    # --- calidad --------------------------------------------------------------------
    def inspeccionar(self, lote, etapa, valores, fecha, obs=""):
        cod = lote.producto.codigo
        datos = {self.param[(cod, etapa, n)].pk: D(str(v)) for n, v in valores.items()}
        return calidad.registrar_inspeccion(lote, etapa, datos, self.u["asalazar"], fecha=fecha, observaciones=obs)

    # --- producción -----------------------------------------------------------------
    def producir(self, codigo, cantidad, inicio, producida=None, lecturas=None, paro_forzado=None):
        producto = self.p[codigo]
        op = produccion.crear_orden(producto, D(str(cantidad)), self.u["kperyman"], fecha_planificada=inicio.date())
        produccion.confirmar(op)
        produccion.iniciar(op, self.u["kperyman"], fecha=inicio)
        momento = inicio + timedelta(minutes=10)
        for reg in op.registros.select_related("operacion__centro"):
            std = float(reg.tiempo_estandar_min)
            duracion = std * self.rng.uniform(0.98, 1.22)
            paro = 0
            motivo = ""
            if paro_forzado and paro_forzado[0] == reg.operacion.codigo:
                paro, motivo = paro_forzado[1], paro_forzado[2]
            elif self.rng.random() < 0.25:
                paro, motivo = self.rng.randint(5, 25), self.rng.choice(MOTIVOS_PARO)
            duracion += paro
            produccion.iniciar_operacion(reg, self.u["kperyman"], fecha=momento)
            fin = momento + timedelta(minutes=duracion)
            self.telemetria(op, reg.operacion.centro.codigo, momento, fin, cantidad, lecturas or {})
            produccion.terminar_operacion(reg, self.u["kperyman"], fecha=fin, paro_min=paro, motivo_paro=motivo)
            momento = fin + timedelta(minutes=self.rng.randint(5, 20))
        if producida is None:
            # Los semielaborados rinden lo planificado (la merma ya está en la BOM); en el envasado se pierden algunas unidades
            factor = self.rng.choice([1, 1, 0.995, 0.99, 0.985]) if producto.tipo == Producto.Tipo.TERMINADO else 1
            producida = (D(str(cantidad)) * D(str(factor))).quantize(D("1"))
        produccion.terminar(op, producida, self.u["kperyman"], fecha=momento)
        op.refresh_from_db()
        return op, momento

    def telemetria(self, op, centro, desde, hasta, cantidad, especiales):
        """Lecturas IIoT durante la operación, ligadas a la orden y a su lote."""
        es_eco = op.producto.linea == "ECO"
        pasos = 4
        for i in range(pasos):
            fecha = desde + (hasta - desde) * (i + 0.5) / pasos
            valores = {}
            if centro == "TQ-01":
                valores["TQ1-NIVEL"] = self.rng.uniform(35, 85)
                valores["TQ1-PH"] = self.rng.gauss(9.8 if es_eco else 7.0, 0.15)
            elif centro == "REA-01":
                valores["REA1-TEMP"] = self.rng.uniform(72, 82)
            elif centro == "ENV-01":
                valores["ENV-CONTEO"] = round(float(cantidad) * (i + 1) / pasos)
            for codigo, valor in valores.items():
                if (codigo, i) in especiales:
                    valor = especiales[(codigo, i)]
                s = self.sensores[codigo]
                Lectura.objects.create(sensor=s, fecha=fecha, valor=round(valor, 2), fuera_rango=s.fuera_de_rango(valor),
                                       orden=op, lote=op.lote)

    # --- ventas ---------------------------------------------------------------------
    def vender(self, cliente, lineas, fecha):
        lineas = [(c, q) for c, q in lineas if q > 0]
        if not lineas:
            return None
        pedido = PedidoVenta.objects.create(numero=ventas.nuevo_numero(), cliente=Cliente.objects.get(codigo=cliente),
                                            fecha=fecha.date(), fecha_entrega=fecha.date(), creado_por=self.u["azamora"])
        for codigo, cantidad in lineas:
            LineaPedido.objects.create(pedido=pedido, producto=self.p[codigo], cantidad=D(cantidad), precio_unitario=self.p[codigo].precio_venta)
        ventas.confirmar(pedido)
        ventas.despachar(pedido, self.u["azamora"], fecha=fecha)
        return pedido

    def stock_pt(self, codigo):
        return int(disponible(self.p[codigo], [Almacen.Tipo.TERMINADO]))

    # --- guion ----------------------------------------------------------------------
    def ejecutar(self):
        r = self.rng
        # Abastecimiento inicial
        self.comprar("PRV-001", [("MP-QUAT", 30), ("MP-SOLU", 20), ("MP-KOH", 60), ("MP-ACCIT", 5), ("MP-COLAZ", 1)], 0)
        self.comprar("PRV-002", [("MP-FRLAV", 8), ("MP-FRLIM", 8)], 0)
        self.comprar("PRV-003", [("EMP-BOT1L", 2500), ("EMP-ETQ", 2500), ("EMP-CAJA4", 650)], 0, 2)
        self.comprar("PRV-004", [("MP-AGUA", 4000)], 0)

        for semana in range(6):
            d = semana * 7
            # Acopio semanal de aceite usado con inspección de recepción
            self.acopio_aceite("PRV-005", r.choice([70, 80, 85, 90]), d + 1, round(r.uniform(1.6, 3.4), 2), round(r.uniform(0.4, 1.5), 2))
            if semana == 2:
                _, nc = self.acopio_aceite("PRV-006", 60, d + 1, 6.10, 2.8)
                calidad.disponer(nc, NoConformidad.Disposicion.SCRAP, self.u["asalazar"], fecha=self.t(d + 1, 11),
                                 comentario="Aceite degradado (acidez 6.1): no apto para saponificación. Se envía a gestor de residuos.",
                                 causa_raiz="Aceite reutilizado demasiadas veces por el generador; se capacita al proveedor.")

            # Línea DESINFECTANTE (producto piloto): base -> producto terminado
            base, fin = self.producir("SE-BDES", 200, self.t(d + 2, 7, 30))
            op_des, fin = self.producir("PT-DES1L", 200, fin + timedelta(minutes=30),
                                        paro_forzado=("OP-40", 35, "Cuello de botella en envasado manual") if semana == 0 else None)
            if semana == 1:
                _, nc = self.inspeccionar(op_des.lote, "FIN", {"pH": 7.9, "Viscosidad": 24, "Densidad": 1.004}, fin + timedelta(minutes=40))
                calidad.disponer(nc, NoConformidad.Disposicion.RETRABAJO, self.u["asalazar"], fecha=fin + timedelta(minutes=60),
                                 comentario="Ajustar pH con ácido cítrico y reinspeccionar.",
                                 causa_raiz="Dosificación de amonio cuaternario sin balanza calibrada.")
                produccion.consumo_adicional(op_des, self.p["MP-ACCIT"], D("0.30"), self.u["kperyman"],
                                             "Corrección de pH (retrabajo NC)", fecha=fin + timedelta(minutes=90))
                self.inspeccionar(op_des.lote, "FIN", {"pH": 7.2, "Viscosidad": 25, "Densidad": 1.003}, fin + timedelta(minutes=150), "Reinspección tras retrabajo")
            else:
                self.inspeccionar(op_des.lote, "FIN", {"pH": round(r.uniform(6.8, 7.3), 2), "Viscosidad": r.randint(18, 35),
                                                       "Densidad": round(r.uniform(0.998, 1.012), 3)}, fin + timedelta(minutes=40))

            # Línea ECO (aceite reciclado): aceite filtrado -> base jabonosa -> producto terminado
            if disponible(self.p["MP-ACUSA"], TIPOS_ALMACEN_CONSUMO) >= 56:
                self.producir("SE-ACFIL", 50, self.t(d + 2, 8))
            if disponible(self.p["SE-ACFIL"], TIPOS_ALMACEN_CONSUMO) >= D("37.5"):
                especiales = {("REA1-TEMP", 2): 92.4} if semana == 4 else {}
                op_bj, fin = self.producir("SE-BJAB", 150, self.t(d + 3, 7, 30), lecturas=especiales)
                if semana == 4:
                    _, nc = self.inspeccionar(op_bj.lote, "PRO", {"pH": 11.4, "Alcalinidad libre": 0.32}, fin + timedelta(minutes=30))
                    calidad.disponer(nc, NoConformidad.Disposicion.SCRAP, self.u["asalazar"], fecha=fin + timedelta(minutes=60),
                                     comentario="Exceso de álcali libre; riesgo para el usuario. No recuperable.",
                                     causa_raiz="Sobretemperatura en el reactor (92 °C, alerta IIoT) y exceso de KOH dosificado.")
                else:
                    self.inspeccionar(op_bj.lote, "PRO", {"pH": round(r.uniform(9.5, 10.2), 2), "Alcalinidad libre": round(r.uniform(0.02, 0.08), 2)},
                                      fin + timedelta(minutes=30))
            if disponible(self.p["SE-BJAB"], TIPOS_ALMACEN_CONSUMO) >= D("148.5"):
                op_eco, fin = self.producir("PT-ECO1L", 150, self.t(d + 4, 7, 30))
                if semana == 3:
                    _, nc = self.inspeccionar(op_eco.lote, "FIN", {"pH": 9.7, "Viscosidad": 180}, fin + timedelta(minutes=30))
                    calidad.disponer(nc, NoConformidad.Disposicion.LIBERACION, self.u["asalazar"], fecha=fin + timedelta(minutes=50),
                                     comentario="Viscosidad 10 % bajo el mínimo; no afecta desempeño de limpieza. Liberado bajo concesión de Gerencia.",
                                     causa_raiz="Agua de dilución a mayor temperatura.")
                else:
                    self.inspeccionar(op_eco.lote, "FIN", {"pH": round(r.uniform(9.4, 10.1), 2), "Viscosidad": r.randint(320, 650)}, fin + timedelta(minutes=30))

            # Ventas de la semana (FEFO, solo lotes liberados)
            for dia, hora in ((d + 4, 15), (d + 5, 10), (d + 6, 11)):
                cliente = r.choice(["CLI-001", "CLI-002", "CLI-003", "CLI-004", "CLI-005", "CLI-006"])
                des = min(self.stock_pt("PT-DES1L"), r.choice([40, 60, 80]))
                eco = min(self.stock_pt("PT-ECO1L"), r.choice([20, 40, 48]))
                self.vender(cliente, [("PT-DES1L", des), ("PT-ECO1L", eco)], self.t(dia, hora))

        self.estado_para_demo()
        Alerta.objects.filter(fecha__lt=self.ahora - timedelta(hours=1)).update(atendida=True)

    def estado_para_demo(self):
        """Deja operaciones abiertas para la demostración en vivo."""
        hoy = 42
        # Abastecimiento de químicos (los de la línea desinfectante quedan bajo mínimo tras 6 semanas)
        self.comprar("PRV-001", [("MP-QUAT", 20), ("MP-SOLU", 10), ("MP-KOH", 40)], hoy - 1, recibir=False)
        # Acopio de hoy, pendiente de recepción e inspección
        self.comprar("PRV-005", [("MP-ACUSA", 75)], hoy, recibir=False, almacen="ALM-ACO")
        # Base jabonosa terminada esta mañana y una orden ECO en proceso (el ESP32 envía datos a esta orden)
        inicio = self.ahora - timedelta(hours=5)
        if disponible(self.p["SE-ACFIL"], TIPOS_ALMACEN_CONSUMO) < D("37.5"):
            self.producir("SE-ACFIL", 50, inicio - timedelta(hours=3))
        op_bj, fin = self.producir("SE-BJAB", 150, inicio)
        self.inspeccionar(op_bj.lote, "PRO", {"pH": 9.9, "Alcalinidad libre": 0.05}, fin + timedelta(minutes=10))
        op = produccion.crear_orden(self.p["PT-ECO1L"], D("150"), self.u["kperyman"])
        produccion.confirmar(op)
        produccion.iniciar(op, self.u["kperyman"], fecha=self.ahora - timedelta(minutes=50))
        primera = op.registros.first()
        produccion.iniciar_operacion(primera, self.u["kperyman"], fecha=self.ahora - timedelta(minutes=40))
        # Orden de desinfectante planificada para hoy y pedido en borrador
        produccion.crear_orden(self.p["SE-BDES"], D("200"), self.u["kperyman"])
        pedido = PedidoVenta.objects.create(numero=ventas.nuevo_numero(), cliente=Cliente.objects.get(codigo="CLI-003"),
                                            creado_por=self.u["azamora"])
        LineaPedido.objects.create(pedido=pedido, producto=self.p["PT-DES1L"], cantidad=D("24"), precio_unitario=self.p["PT-DES1L"].precio_venta)
