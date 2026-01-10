import paho.mqtt.client as mqtt
import time

def on_publish(client, userdata, result):
    print("Message Published")

client = mqtt.Client("server_publisher")

client.connect("192.168.11.62", 1883)

# Topic to publish the message
topic = "esp32/sensor1"

# Message to be sent
message = "Hello from server!"

# Publishing the message
client.on_publish = on_publish
client.publish(topic, message)

time.sleep(1)  # Wait for the message to be sent

client.disconnect()
