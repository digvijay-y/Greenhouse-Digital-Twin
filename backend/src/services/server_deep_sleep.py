import paho.mqtt.client as mqtt
import time
import openpyxl 
from datetime import datetime

def on_connect(client, userdata, flags, rc):
    global flag_connected
    flag_connected = 1
    client_subscriptions(client)
    print("Connected to MQTT server")

def on_disconnect(client, userdata, rc):
    global flag_connected
    flag_connected = 0
    print("Disconnected from MQTT server")

# Create workbooks for moisture and npk
moisture_workbook = openpyxl.Workbook()
moisture_sheet = moisture_workbook.active
moisture_sheet.append(["Timestamp", "Humidity(%)"])

npk_workbook = openpyxl.Workbook()
npk_sheet = npk_workbook.active
npk_sheet.append(["Timestamp", "Nitrogen", "Phosphorus", "Potassium"])

def humidity_excel_data(humidity_index, id):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    moisture_sheet.append([timestamp, humidity_index])
    moisture_workbook.save(f"moisture_data_{id}.xlsx")
    print(f"Data saved to Excel file for ID {id} - Humidity: {humidity_index}")

def npk_excel_data(nitrogen, phosphorus, potassium, id):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    npk_sheet.append([timestamp, nitrogen, phosphorus, potassium])
    npk_workbook.save(f"npk_data_{id}.xlsx")
    print(f"Data saved to Excel file for ID {id} - NPK: N={nitrogen}, P={phosphorus}, K={potassium}")

def moisture_decision(moisture_value):
    if moisture_value < 55:
        return 1  # Solenoid valves on
    elif 55 <= moisture_value < 60:
        return 2  # Waiting mode 
    elif 60 <= moisture_value < 70:
        return 3  # OK
    elif 70 <= moisture_value < 80:
        return 4  # Enough
    else:
        return 5  # Maximum

def callback_esp32_sensor(client, userdata, msg):
    decoded_data = msg.payload.decode('utf-8')

    if msg.topic.endswith(('sensor5', 'sensor6')):
        # This is for NPK data
        values = decoded_data.split("%")
        if len(values) == 3:
            try:
                var_1 = int(values[0])
                var_2 = int(values[1])
                var_3 = int(values[2])

                print("Data Received from", msg.topic, var_1, var_2, var_3)
                npk_excel_data(var_1, var_2, var_3, int(msg.topic[-1]))
            except ValueError as e:
                print(f"Error converting values to integers: {e}")
        else:
            print(f"Invalid payload format for {msg.topic}: {decoded_data}")

    elif msg.topic.startswith('esp32/sensor'):
        # This is for moisture data
        decoded_data = msg.payload.decode('utf-8')
        if decoded_data:
            humidity_index = float(decoded_data)
            print("Data Received from", msg.topic, humidity_index)

            valve_control = moisture_decision(humidity_index)
            print("Valve value", valve_control)
            client.publish(f"{msg.topic.replace('sensor', 'relay')}", f"1%{valve_control * 10 + 5}")
            humidity_excel_data(humidity_index, int(msg.topic[-1]))

def client_subscriptions(client):
    client.subscribe("esp32/#")

client = mqtt.Client("rpi_client1")  # this should be a unique name
flag_connected = 0

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.message_callback_add('esp32/sensor1', callback_esp32_sensor)
client.message_callback_add('esp32/sensor2', callback_esp32_sensor)
client.message_callback_add('esp32/sensor3', callback_esp32_sensor)
client.message_callback_add('esp32/sensor4', callback_esp32_sensor)
client.message_callback_add('esp32/sensor5', callback_esp32_sensor)
client.message_callback_add('esp32/sensor6', callback_esp32_sensor)

client.connect('127.0.0.1', 1883)
# start a new thread
client.loop_start()
client_subscriptions(client)
print("......client setup complete............")

while True:
    time.sleep(4)
    if flag_connected != 1:
        print("trying to connect MQTT server..")
