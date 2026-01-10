import paho.mqtt.client as mqtt
import time
import random
import json

# --- Configuration ---
BROKER_ADDRESS = "localhost"
CLIENT_NAME = "SensorSimulator"

# --- Topics ---
TOPIC_NPK = "esp32/npk"
TOPIC_MOISTURE_1 = "pico1/moisture1"
TOPIC_MOISTURE_2 = "pico1/moisture2"
TOPIC_BME280 = "pico1/bme280"
TOPIC_MOISTURE_3 = "pico2/moisture1"
TOPIC_MOISTURE_4 = "pico2/moisture2"

# --- Main ---
print(f"Attempting to connect to broker at {BROKER_ADDRESS}...")
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, CLIENT_NAME)

try:
    client.connect(BROKER_ADDRESS)
    print("Successfully connected to MQTT broker.")
except Exception as e:
    print(f"Failed to connect to MQTT broker: {e}")
    print("Please ensure the Mosquitto broker is running.")
    print("You can start it with: sudo systemctl start mosquitto")
    exit()

client.loop_start()
print("Starting sensor simulation. Press Ctrl+C to stop.")

try:
    while True:
        # 1. Simulate NPK data (JSON)
        n_val = random.randint(10, 20)
        p_val = random.randint(35, 45)
        k_val = random.randint(20, 30)
        npk_payload = json.dumps({"n": n_val, "p": p_val, "k": k_val})
        client.publish(TOPIC_NPK, npk_payload)
        print(f"Published to {TOPIC_NPK}: {npk_payload}")

        # 2. Simulate Moisture data (plain text)
        m1 = 80 + random.uniform(-5, 5)
        m2 = 25 + random.uniform(-5, 5)
        m3 = 65 + random.uniform(-5, 5)
        m4 = 35 + random.uniform(-5, 5)
        client.publish(TOPIC_MOISTURE_1, f"{m1:.1f}")
        client.publish(TOPIC_MOISTURE_2, f"{m2:.1f}")
        client.publish(TOPIC_MOISTURE_3, f"{m3:.1f}")
        client.publish(TOPIC_MOISTURE_4, f"{m4:.1f}")
        print(f"Published Moisture: {m1:.1f}, {m2:.1f}, {m3:.1f}, {m4:.1f}")

        # 3. Simulate BME280 data (CSV string)
        temp = 24 + random.uniform(-1, 1)
        humidity = 60 + random.uniform(-5, 5)
        pressure = 1013 + random.uniform(-1, 1)
        bme_payload = f"{temp:.1f},{humidity:.1f},{pressure:.2f}"
        client.publish(TOPIC_BME280, bme_payload)
        print(f"Published to {TOPIC_BME280}: {bme_payload}")
        
        print("--- Cycle complete. Waiting 5 seconds. ---\n")
        time.sleep(5)

except KeyboardInterrupt:
    print("\nSimulation stopped by user.")
finally:
    client.loop_stop()
    client.disconnect()
    print("Disconnected from MQTT broker.")
