#include <Wire.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <PubSubClient.h>

// --- PINS ---
#define RE 32
#define DE 33
#define RX_PIN 26
#define TX_PIN 27

// Use Hardware Serial 2
HardwareSerial mod(2);

// --- CONFIGURATION ---
const char* WIFI_SSID = "D's Galaxy";
const char* WIFI_PASSWORD = "L1234D@07";
const char* MQTT_BROKER_IP = "192.168.132.138";
const int MQTT_BROKER_PORT = 1883;
const char* MQTT_CLIENT_NAME = "esp32_npk_sensor";
const char* NPK_TOPIC = "esp32/npk";

// --- MQTT and WiFi Clients ---
WiFiClient espClient;
PubSubClient client(espClient);

// --- SENSOR COMMANDS (Method A - Confirmed Working) ---
const byte nitro[] = {0x01, 0x03, 0x00, 0x1e, 0x00, 0x01, 0xe4, 0x0c};
const byte phos[] = {0x01, 0x03, 0x00, 0x1f, 0x00, 0x01, 0xb5, 0xcc};
const byte pota[] = {0x01, 0x03, 0x00, 0x20, 0x00, 0x01, 0x85, 0xc0};

byte values[11];
int N, P, K;

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect(MQTT_CLIENT_NAME)) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  
  // Setup hardware serial (from working code)
  mod.begin(9600, SERIAL_8N1, RX_PIN, TX_PIN);

  pinMode(RE, OUTPUT);
  pinMode(DE, OUTPUT);

  setup_wifi();
  client.setServer(MQTT_BROKER_IP, MQTT_BROKER_PORT);
}

// --- ROBUST READING FUNCTION (from working code) ---
byte get_value(const byte* command, int len) {
  // 1. Clear any old garbage data
  while (mod.available()) mod.read(); 
  
  // 2. Switch to TRANSMIT mode
  digitalWrite(DE, HIGH);
  digitalWrite(RE, HIGH);
  delay(5); 

  // 3. Send Command
  mod.write(command, len);
  
  // 4. IMPORTANT: Wait for transmission to finish completely
  mod.flush(); 
  
  // 5. Switch to RECEIVE mode
  digitalWrite(DE, LOW);
  digitalWrite(RE, LOW);
  
  // 6. Wait for response (Timeout after 200ms)
  unsigned long startTime = millis();
  while (mod.available() < 7) {
    if (millis() - startTime > 200) {
      return 0; // Timeout, return 0
    }
  }

  // 7. Read the data
  for (byte i = 0; i < 7; i++) {
    values[i] = mod.read();
  }
  
  // The actual value is at index 4
  return values[4];
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Read values using the working function
  N = get_value(nitro, 8);
  delay(20);
  P = get_value(phos, 8);
  delay(20);
  K = get_value(pota, 8);

  Serial.print("Nitrogen: ");
  Serial.print(N);
  Serial.println(" mg/kg");
  Serial.print("Phosphorous: ");
  Serial.print(P);
  Serial.println(" mg/kg");
  Serial.print("Potassium: ");
  Serial.print(K);
  Serial.println(" mg/kg");

  // Create a JSON document
  JsonDocument doc;
  doc["n"] = N;
  doc["p"] = P;
  doc["k"] = K;

  // Serialize JSON to a string
  char jsonBuffer[128];
  serializeJson(doc, jsonBuffer);

  // Publish the JSON string
  client.publish(NPK_TOPIC, jsonBuffer);
  Serial.print("Published to ");
  Serial.print(NPK_TOPIC);
  Serial.print(": ");
  Serial.println(jsonBuffer);

  delay(5000);
}