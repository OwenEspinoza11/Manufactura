// ESP32 — Tanque T-01 y reactor R-01 de Blancos Aromáticos (niveles 0-1 ISA-95)
// Simulable en https://wokwi.com (ESP32 + HC-SR04 + 2 potenciómetros + botón).
//   HC-SR04  -> nivel del tanque T-01 (%)
//   Pot. 1   -> sonda de pH (0-14)
//   Pot. 2   -> termopar del reactor (20-100 °C)
//   Botón    -> sensor IR de conteo de botellas
// Publica en un broker MQTT público; el puente del ERP se conecta al mismo broker con
//   MQTT_HOST=broker.hivemq.com docker compose up puente-mqtt
#include <WiFi.h>
#include <PubSubClient.h>

const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASS = "";
const char* MQTT_HOST = "broker.hivemq.com";
const char* PREFIJO   = "blancosaromaticos/planta";

const int PIN_TRIG = 5, PIN_ECHO = 18, PIN_PH = 34, PIN_TEMP = 35, PIN_IR = 4;
const float ALTURA_TANQUE_CM = 120.0;

WiFiClient red;
PubSubClient mqtt(red);
unsigned long conteo = 0, ultimoEnvio = 0;
bool irAnterior = HIGH;

void conectar() {
  while (WiFi.status() != WL_CONNECTED) { WiFi.begin(WIFI_SSID, WIFI_PASS); delay(500); }
  while (!mqtt.connected()) {
    String id = "esp32-t01-" + String(random(0xffff), HEX);
    if (!mqtt.connect(id.c_str())) delay(1000);
  }
}

void publicar(const char* topico, float valor) {
  char t[96], v[16];
  snprintf(t, sizeof(t), "%s/%s", PREFIJO, topico);
  dtostrf(valor, 0, 2, v);
  mqtt.publish(t, v);
  Serial.printf("%s = %s\n", t, v);
}

float nivelPorcentaje() {
  digitalWrite(PIN_TRIG, LOW); delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  float distancia = pulseIn(PIN_ECHO, HIGH) * 0.0343 / 2.0;          // cm hasta la superficie
  return constrain((ALTURA_TANQUE_CM - distancia) / ALTURA_TANQUE_CM * 100.0, 0, 100);
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_TRIG, OUTPUT); pinMode(PIN_ECHO, INPUT); pinMode(PIN_IR, INPUT_PULLUP);
  mqtt.setServer(MQTT_HOST, 1883);
  conectar();
}

void loop() {
  if (!mqtt.connected()) conectar();
  mqtt.loop();
  bool ir = digitalRead(PIN_IR);
  if (irAnterior == HIGH && ir == LOW) conteo++;                       // flanco = botella detectada
  irAnterior = ir;

  if (millis() - ultimoEnvio > 5000) {
    ultimoEnvio = millis();
    publicar("tanque1/nivel", nivelPorcentaje());
    publicar("tanque1/ph", analogRead(PIN_PH) / 4095.0 * 14.0);
    publicar("reactor1/temperatura", 20.0 + analogRead(PIN_TEMP) / 4095.0 * 80.0);
    publicar("envasado/conteo", conteo);
  }
}
