"""Emulador de los ESP32 de planta (niveles 0-1 de ISA-95).

Publica por MQTT las mismas variables que el prototipo físico/Wokwi:
  tanque1/nivel (HC-SR04, %), tanque1/ph, reactor1/temperatura (°C), envasado/conteo (sensor IR)

Uso:
  python iot/simulador_esp32.py              # publica cada INTERVALO_S segundos
  python iot/simulador_esp32.py --pico       # publica UNA lectura de temperatura fuera de rango (demo de alerta)
"""
import argparse
import json
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
PREFIJO = os.environ.get("MQTT_PREFIJO", "blancosaromaticos/planta")
INTERVALO = float(os.environ.get("INTERVALO_S", "5"))


def conectar():
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"esp32-sim-{random.randint(1000, 9999)}")
    while True:
        try:
            cliente.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
            cliente.loop_start()
            return cliente
        except OSError:
            print(f"[esp32] esperando broker {MQTT_HOST}:{MQTT_PORT}...", flush=True)
            time.sleep(3)


def publicar(cliente, topico, valor):
    carga = json.dumps({"valor": round(valor, 2), "fecha": datetime.now(timezone.utc).isoformat()})
    cliente.publish(f"{PREFIJO}/{topico}", carga, qos=1)
    print(f"[esp32] {PREFIJO}/{topico} -> {carga}", flush=True)


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--pico", action="store_true", help="Envía una temperatura de 93 °C (fuera de rango)")
    opciones = args.parse_args()

    cliente = conectar()
    if opciones.pico:
        publicar(cliente, "reactor1/temperatura", 93.0)
        time.sleep(1)
        cliente.loop_stop()
        return

    nivel, conteo, ciclo = 70.0, 0, 0
    while True:
        ciclo += 1
        nivel = max(8.0, nivel - random.uniform(0.3, 1.2)) if nivel > 12 else 88.0  # se vacía al envasar y se rellena
        conteo += random.randint(1, 3)
        temperatura = random.gauss(77, 2.2)
        if ciclo % 90 == 0:  # pico ocasional: genera alerta en el ERP
            temperatura = random.uniform(89, 92)
        publicar(cliente, "tanque1/nivel", nivel + random.uniform(-0.4, 0.4))
        publicar(cliente, "tanque1/ph", random.gauss(9.8, 0.12))
        publicar(cliente, "reactor1/temperatura", temperatura)
        publicar(cliente, "envasado/conteo", conteo)
        time.sleep(INTERVALO)


if __name__ == "__main__":
    main()
