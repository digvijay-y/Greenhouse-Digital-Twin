import network
import time
from machine import Pin, ADC
from umqtt.simple import MQTTClient

# --- CONFIGURATION ---
WIFI_SSID = 'YOUR_WIFI_SSID' # <-- Enter your WiFi name
WIFI_PASS = 'YOUR_WIFI_PASSWORD' # <-- Enter your WiFi password
MQTT_BROKER = '192.168.1.15'  # <-- Your laptop's IP address
MQTT_CLIENT_ID = 'Pico2_Soil_Sensor'
MOISTURE_TOPIC_1 = b"pico2/moisture1"
MOISTURE_TOPIC_2 = b"pico2/moisture2"

# --- SENSORS SETUP ---
soil_1 = ADC(Pin(26))
soil_2 = ADC(Pin(27))

# --- CALIBRATION ---
# These values are critical. Measure them for your specific sensors.
# To find DRY_VAL: Leave the sensor in open air for a few minutes and check the raw value.
# To find WET_VAL: Submerge the sensor completely in water and check the raw value.
DRY_VAL = 50000  # Raw ADC value for a completely dry sensor
WET_VAL = 20000  # Raw ADC value for a sensor fully submerged in water

def get_moisture_percent(adc):
    """ Converts raw ADC reading to a 0-100% moisture value. """
    raw_value = adc.read_u16()
    # Clamp the raw value to be within the calibrated range
    raw_value = max(WET_VAL, min(DRY_VAL, raw_value))
    # Calculate percentage
    percentage = 100 * (DRY_VAL - raw_value) / (DRY_VAL - WET_VAL)
    return round(percentage, 1)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to WiFi...')
        wlan.connect(WIFI_SSID, WIFI_PASS)
        while not wlan.isconnected():
            time.sleep(1)
    print('WiFi Connected. IP:', wlan.ifconfig()[0])

def connect_mqtt():
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER)
    try:
        client.connect()
        print('MQTT Connected')
        return client
    except OSError as e:
        print(f"MQTT Connection failed: {e}")
        return None

# --- MAIN LOOP ---
connect_wifi()
client = connect_mqtt()

while True:
    try:
        if client is None:
            # Attempt to reconnect if MQTT connection failed initially
            client = connect_mqtt()
            time.sleep(5)
            continue
            
        # 1. Read Soil Moisture
        moisture_1 = get_moisture_percent(soil_1)
        moisture_2 = get_moisture_percent(soil_2)
        
        # 2. Publish to MQTT Broker
        print(f"Sending: M1={moisture_1}%, M2={moisture_2}%")
        
        client.publish(MOISTURE_TOPIC_1, str(moisture_1))
        client.publish(MOISTURE_TOPIC_2, str(moisture_2))
        
        time.sleep(5) # Send data every 5 seconds

    except OSError as e:
        print(f"An error occurred: {e}. Resetting in 5 seconds...")
        time.sleep(5)
        machine.reset()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        time.sleep(5)
