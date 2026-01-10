#include <ESP8266WiFi.h>
#include <PubSubClient.h>


const char* ssid = "Sonali";
const char* password = "123456789";
const char* mqtt_server = "192.168.29.62";

const int relayPin = 14; // GPIO pin connected to the relay

WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  Serial.begin(115200);
  delay(10);

  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived on topic: ");
  Serial.println(topic);

  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.println("Message received: " + message);

  if (message.startsWith("1")) {
    int duration = 20;
    //message.substring(2).toInt(); // Extract duration from the message
    digitalWrite(relayPin, LOW); // Turn ON the relay
    Serial.println("Relay turned ON for " + String(duration) + " seconds");
    delay(duration * 1000); // Convert seconds to milliseconds
    digitalWrite(relayPin, HIGH); // Turn OFF the relay after duration
    Serial.println("Relay turned OFF");
    delay(10000);
  } else {
    digitalWrite(relayPin, HIGH); // Turn OFF the relay immediately
    Serial.println("Relay turned OFF");
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP8266Client")) {
      Serial.println("connected");
      client.subscribe("esp32/relay1");
      client.subscribe("esp32/relay2");
      client.subscribe("esp32/relay3");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  pinMode(relayPin, OUTPUT);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
}