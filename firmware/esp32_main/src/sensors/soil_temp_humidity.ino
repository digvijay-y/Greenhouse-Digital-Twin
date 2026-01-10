#include <SoftwareSerial.h>
#include <Wire.h>
#include <WiFi.h>
#include <PubSubClient.h>

#define RE 32
#define DE 33
SoftwareSerial mod(26, 27);

const char* ssid = "Sonali";
const char* password = "123456789";
const char* mqtt_server = "192.168.137.140";
const int mqtt_port = 1883;

const byte humid[] = {0x01, 0x03, 0x00, 0x04, 0x00, 0x02, 0x64, 0x09};
const byte temp[] = {0x01, 0x03, 0x00, 0x02, 0x00, 0x02, 0x65, 0xCB};
byte values[11];
WiFiClient espClient;
PubSubClient client(espClient);

long lastMsg = 0;

#define ledPin 2

void connect_mqttServer() {
  while (!client.connected()) {
    if (WiFi.status() != WL_CONNECTED) {
      setup_wifi();
    }

    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32_client1")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" trying again in 2 seconds");
      delay(2000);
    }
  }
}

void setup_wifi() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  mod.begin(9600);

  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }

  Serial.println("Connected to WiFi");
  pinMode(RE, OUTPUT);
  pinMode(DE, OUTPUT);
  delay(500);
}

float humidity() {
  digitalWrite(DE, HIGH);
  digitalWrite(RE, HIGH);
  delay(500);

  if (mod.write(humid, sizeof(humid)) == 8) {
    digitalWrite(DE, LOW);
    digitalWrite(RE, LOW);

    for (byte i = 0; i < 7; i++) {
      values[i] = mod.read();
    }

    float humidityValue = ((values[3] << 8) | values[4]) / 10.0;
    return humidityValue;
  }

  return -999.0;
}

float temperature() {
  digitalWrite(DE, HIGH);
  digitalWrite(RE, HIGH);
  delay(500);

  if (mod.write(temp, sizeof(temp)) == 8) {
    digitalWrite(DE, LOW);
    digitalWrite(RE, LOW);

    for (byte i = 0; i < 7; i++) {
      values[i] = mod.read();
    }

    int tempValue = (values[3] << 8) | values[4];

    if (tempValue & 0x8000) {
      tempValue = -((tempValue ^ 0xFFFF) + 1);
    }

    float temperatureC = tempValue / 10.0;
    return temperatureC;
  }

  return -999.0;
}

void loop() {
  byte val1, val2;
  val1 = humidity();
  delay(250);
  val2 = temperature();
  delay(250);

  Serial.print("Humidity ");
  Serial.print(val1);
  Serial.println(" %");

  if (!client.connected()) {
    connect_mqttServer();
  }

  client.loop();

  long now = millis();
  if (now - lastMsg > 4000) {
    lastMsg = now;
    String payload = String(val1);
    client.publish("esp32/sensor1", payload.c_str());
  }
}

void setup() {
  pinMode(ledPin, OUTPUT);
  Serial.begin(115200);
  setup_wifi();
  pinMode(RE, OUTPUT);
  pinMode(DE, OUTPUT);
  delay(500);
  client.setServer(mqtt_server, mqtt_port);
}