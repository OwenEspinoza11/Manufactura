"""Puente MQTT -> ERP (patrón Adapter, nivel 2 -> nivel 3 de ISA-95).

Se suscribe a los tópicos de planta y reenvía cada lectura al endpoint HTTP del ERP.
El ERP no necesita saber de MQTT: si mañana el dato viene por Modbus/OPC-UA, solo cambia este adaptador.

Variables de entorno:
  MQTT_HOST (mqtt)  MQTT_PORT (1883)  MQTT_PREFIJO (blancosaromaticos/planta)
  ERP_URL (http://web:8000)  IIOT_TOKEN
"""
import json
import os
import time

import paho.mqtt.client as mqtt
import requests

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
PREFIJO = os.environ.get("MQTT_PREFIJO", "blancosaromaticos/planta")
ERP_URL = os.environ.get("ERP_URL", "http://localhost:8000").rstrip("/")
TOKEN = os.environ.get("IIOT_TOKEN", "esp32-blancos-2026")
ENDPOINT = f"{ERP_URL}/iiot/api/lecturas/"


def a_lectura(topico, payload):
    """Acepta un número plano ('7.02') o JSON ({"valor": 7.02, "fecha": "..."})."""
    texto = payload.decode().strip()
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError:
        datos = texto
    if isinstance(datos, dict):
        return {"topico": topico, "valor": float(datos["valor"]), **({"fecha": datos["fecha"]} if datos.get("fecha") else {})}
    return {"topico": topico, "valor": float(datos)}


def al_conectar(cliente, _userdata, _flags, codigo, _props=None):
    print(f"[puente] conectado a {MQTT_HOST}:{MQTT_PORT} (rc={codigo}); suscrito a {PREFIJO}/#", flush=True)
    cliente.subscribe(f"{PREFIJO}/#", qos=1)


def al_mensaje(_cliente, _userdata, msg):
    try:
        lectura = a_lectura(msg.topic, msg.payload)
        r = requests.post(ENDPOINT, json=lectura, headers={"X-IIoT-Token": TOKEN}, timeout=5)
        estado = r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text
        print(f"[puente] {msg.topic} = {lectura['valor']} -> HTTP {r.status_code} {estado}", flush=True)
    except (ValueError, KeyError) as e:
        print(f"[puente] mensaje ignorado en {msg.topic}: {e}", flush=True)
    except requests.RequestException as e:
        print(f"[puente] ERP no disponible ({e}); se descarta la lectura", flush=True)


def main():
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="puente-erp-blancos")
    cliente.on_connect = al_conectar
    cliente.on_message = al_mensaje
    while True:
        try:
            cliente.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
            break
        except OSError:
            print(f"[puente] esperando broker {MQTT_HOST}:{MQTT_PORT}...", flush=True)
            time.sleep(3)
    cliente.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()
