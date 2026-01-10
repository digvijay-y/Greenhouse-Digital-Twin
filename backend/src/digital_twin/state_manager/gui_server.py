import paho.mqtt.client as mqtt
import tkinter as tk
from tkinter import ttk
from openpyxl import Workbook
from datetime import datetime, timedelta
import time

def on_connect(client, userdata, flags, rc):
   global flag_connected
   flag_connected = 1
   client_subscriptions(client)
   print("Connected to MQTT server")

def on_disconnect(client, userdata, rc):
   global flag_connected
   flag_connected = 0
   print("Disconnected from MQTT server")

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

fetched_values = {}  # Define this dictionary with actual values
min_requirements = {}

def Humidity_excel_data(humidity_index, id):#need to fix this function
    filename = f"received_data_{id}.xlsx"  # Generate a unique filename based on the ID
    try:
        workbook = Workbook()
        sheet = workbook.active
        # Get the current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append(["timestamp", "Humidity(%)"])

        if humidity_index != -1:
            humidity = humidity_index
            # Append the data to the Excel sheet
            sheet.append([timestamp, humidity])
            # Save the workbook to a file with the unique filename
            workbook.save(filename)
            print(f"Data saved to Excel file for ID {id} - Humidity: {humidity_index}")
        else:
            print("Data not saved")
    except Exception as e:
        print(f"An error occurred: while saving the data into the excel {e}")
def NPK_excel_data(nitrogen, phosphorus, potassium, id):#need to fix this function
    filename = f"npk_data_{id}.xlsx"  # Generate a unique filename based on the ID
    try:
        workbook = Workbook()
        sheet = workbook.active
        # Get the current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append(["timestamp", "Nitrogen", "Phosphorus", "Potassium"])

        if nitrogen != -1 and phosphorus != -1 and potassium != -1:
            # Append the data to the Excel sheet
            sheet.append([timestamp, nitrogen, phosphorus, potassium])
            # Save the workbook to a file with the unique filename
            workbook.save(filename)
            print(f"Data saved to Excel file for ID {id} - NPK: N={nitrogen}, P={phosphorus}, K={potassium}")
        else:
            print("Data not saved")
    except Exception as e:
        print(f"An error occurred while saving the data into the Excel file: {e}")

# a callback functions for the MQTT
def callback_esp32_sensor1(client, userdata, msg):
   # print('ESP sensor1 data: ', msg.payload.decode('utf-8'))
    decoded_data = msg.payload.decode('utf-8')
    if decoded_data:
        humidity_index = float(decoded_data)
        print("Data Recived from esp1 ",humidity_index)

        valve_control = moisture_decision(humidity_index)
        print("Valve value",valve_control)
        client.publish("esp32/relay1",  f"1%{valve_control * 10 + 5}") #valves should on for according to  minutes
        #Humidity_excel_data(humidity_index, 1)

def callback_esp32_sensor2(client, userdata, msg):
    #print('ESP sensor2 data: ', msg.payload.decode('utf-8'))
    decoded_data = msg.payload.decode('utf-8')
    if decoded_data:
        # Get the current timestamp
        # Extract humidity and temperature values from the received data
        humidity_index = float(decoded_data)
        print("Data Recived from esp1 ",humidity_index)
        valve_control = moisture_decision(humidity_index)
        print("Valve value",valve_control)
        client.publish("esp32/relay2",  f"1%{valve_control * 10 + 5}") #valves should on for according to  minutes
        #Humidity_excel_data(humidity_index, 2)

def callback_esp32_sensor3(client, userdata, msg):
    decoded_data = msg.payload.decode('utf-8')
    if decoded_data:
        humidity_reading = float(decoded_data)
        print("Data Received from esp1 ", humidity_reading)
        valve_control = moisture_decision(humidity_reading)
        print("Valve value", valve_control)
        client.publish("esp32/relay3", f"1%{valve_control * 10 + 5}")  # valves should be on for according to minutes


def callback_esp32_sensor4(client, userdata, msg):
    #print('ESP sensor3 data: ', msg.payload.decode('utf-8'))
    decoded_data = msg.payload.decode('utf-8')
    if decoded_data: 
        humidity_index = float(decoded_data)
        print("Data Recived from esp1 ",humidity_index)
        #Humidity_excel_data(humidity_index, 4)
            
def callback_esp32_sensor5(client, userdata, msg):
    #print('ESP sensor4 data: ', msg.payload.decode('utf-8'))
    decoded_data = msg.payload.decode('utf-8')
    values = decoded_data.split("%")
    var1, var2, var3 = map(int,values)
    if decoded_data:
        var_1 = float(var1)
        var_2 = float(var2)
        var_3 = float(var3)
        print("Data Recived from esp1 ",var_1,var_2,var_3)
        #NPK_excel_data(var_1, var_2, var_3, 5)
            
def callback_esp32_sensor6(client, userdata, msg):
    #print('ESP sensor4 data: ', msg.payload.decode('utf-8'))
    decoded_data = msg.payload.decode('utf-8')
    values = decoded_data.split("%")
    var1, var2, var3 = map(int,values)
    if decoded_data:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        var_1 = float(var1)
        var_2 = float(var2)
        var_3 = float(var3)
        #NPK_excel_data(var_1, var_2, var_3, 6)
    
def client_subscriptions(client):
    client.subscribe("esp32/#")
    

client = mqtt.Client("rpi_client1") #this should be a unique name
flag_connected = 0

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.message_callback_add('esp32/sensor1', callback_esp32_sensor1)#Soil Moisture Sensor 1 
client.message_callback_add('esp32/sensor2', callback_esp32_sensor2)#Soil Moisture Sensor 2
client.message_callback_add('esp32/sensor3', callback_esp32_sensor3)#Soil Moisture Sensor 3
client.message_callback_add('esp32/sensor4', callback_esp32_sensor4)#Soil Moisture Sensor 4 
client.message_callback_add('esp32/sensor5', callback_esp32_sensor5)#NPK Sensor 1 
client.message_callback_add('esp32/sensor6', callback_esp32_sensor6)#NPK Sensor 2 

client.connect('127.0.0.1',1883)
# start a new thread
client.loop_start()
client_subscriptions(client)
print("......client setup complete............")


while True:
    time.sleep(4)
    if (flag_connected != 1):
        print("trying to connect MQTT server..")
class SmartIrrigationSystemGUI:
    def __init__(self, root, mqtt_client):
        self.root = root
        self.root.title("Smart Irrigation System")

        # Variables
        self.crop_var = tk.StringVar()
        self.stage_var = tk.StringVar()
        self.days_countdown_var = tk.StringVar()
        self.remaining_days = 0
        self.moisture_sensor_values = [tk.DoubleVar() for _ in range(4)]
        self.npk_sensor_values = [tk.DoubleVar() for _ in range(2)]
        self.humidity_var = tk.DoubleVar()
        self.valve_states = [tk.BooleanVar() for _ in range(3)]

        # GUI Components
        self.create_widgets()

        # Additional setup for MQTT
        self.mqtt_client = mqtt_client
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect('127.0.0.1', 1883)
        self.mqtt_client.subscribe("esp32/#")
        self.mqtt_client.loop_start()

    def on_message(self, client, userdata, msg):
        decoded_data = msg.payload.decode('utf-8')
        topic = msg.topic
        if topic == 'esp32/sensor1':
            self.handle_sensor_data(decoded_data, 1)
        elif topic == 'esp32/sensor2':
            self.handle_sensor_data(decoded_data, 2)
        elif topic == 'esp32/sensor3':
            self.handle_sensor_data(decoded_data, 3)
        elif topic == 'esp32/sensor4':
            self.handle_sensor_data(decoded_data, 4)
        elif topic == 'esp32/sensor5':
            self.handle_npk_data(decoded_data, 5)
        elif topic == 'esp32/sensor6':
            self.handle_npk_data(decoded_data, 6)

    def handle_sensor_data(self, data, sensor_index):
        humidity_index = float(data)
        valve_control = moisture_decision(humidity_index)
        self.set_variable_by_index(sensor_index, humidity_index)
        self.update_values()

    def handle_npk_data(self, data, sensor_index):
        values = data.split("%")
        var1, var2, var3 = map(int, values)
        self.set_variable_by_index(sensor_index, f"{var1}, {var2}, {var3}")
        self.update_values()

    def create_widgets(self):
        # Date and Time Display
        self.label_date_now = tk.Label(self.root, text="Current Date", font=('Arial', 12))
        self.label_date_now.grid(row=0, column=2, padx=10, pady=10, sticky="w")

        self.label_time_now = tk.Label(self.root, text="Current Time", font=('Arial', 12))
        self.label_time_now.grid(row=1, column=2, padx=10, pady=10, sticky="w")

        # Crop Selection
        crop_label = tk.Label(self.root, text="Select Crop:")
        crop_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")

        crops = ["Tomato", "Onion", "Potato"]
        crop_dropdown = ttk.Combobox(self.root, textvariable=self.crop_var, values=crops, font=('Arial', 16))
        crop_dropdown.grid(row=2, column=1, padx=10, pady=10)

        # Stage Selection
        stage_label = tk.Label(self.root, text="Select Crop Stage:")
        stage_label.grid(row=3, column=0, padx=10, pady=10, sticky="w")

        stages = ["Initial", "Medium", "Final"]
        stage_dropdown = ttk.Combobox(self.root, textvariable=self.stage_var, values=stages, font=('Arial', 16))
        stage_dropdown.grid(row=3, column=1, padx=10, pady=10)

        # Days Countdown Entry
        days_label = tk.Label(self.root, text="Enter Days Remaining:", font=('Arial', 16))
        days_label.grid(row=3, column=2, padx=10, pady=10, sticky="w")

        days_entry = tk.Entry(self.root, textvariable=self.days_countdown_var, font=('Arial', 16))
        days_entry.grid(row=3, column=3, padx=10, pady=10)

        # Update Button
        update_button = tk.Button(self.root, text="Update Values Here", command=self.update_values, font=('Arial', 16))
        update_button.grid(row=7, column=1, columnspan=2, pady=10)

        # Display Minimum Requirements
        min_req_label = tk.Label(self.root, text="Minimum Requirements:", font=('Arial', 18, 'bold'))
        min_req_label.grid(row=4, column=0, columnspan=4, pady=10)

        # Display Minimum Humidity
        min_humidity_label = tk.Label(self.root, text="Minimum Humidity:", font=('Arial', 16))
        min_humidity_label.grid(row=6, column=0, padx=10, pady=5, sticky="w")

        self.min_humidity_var = tk.DoubleVar()
        min_humidity_entry = tk.Entry(self.root, textvariable=self.min_humidity_var, state="readonly",
                                      font=('Arial', 16))
        min_humidity_entry.grid(row=6, column=1, padx=10, pady=5)

        # Display Minimum NPK Requirements
        min_npk_label = tk.Label(self.root, text="Minimum NPK (N-P-K):", font=('Arial', 16))
        min_npk_label.grid(row=6, column=2, padx=10, pady=5, sticky="w")

        self.min_npk_var = tk.StringVar()
        min_npk_entry = tk.Entry(self.root, textvariable=self.min_npk_var, state="readonly", font=('Arial', 16))
        min_npk_entry.grid(row=6, column=3, padx=10, pady=5)

        # Sensor Values Display
        sensor_values_label = tk.Label(self.root, text="Sensor Values:", font=('Arial', 18, 'bold'))
        sensor_values_label.grid(row=7, column=0, columnspan=2, pady=10)

        sensor_labels = ["Moisture Sensor 1", "Moisture Sensor 2", "Moisture Sensor 3", "Moisture Sensor 4"]

        for i, label in enumerate(sensor_labels):
            sensor_label = tk.Label(self.root, text=label, font=('Arial', 16))
            sensor_label.grid(row=i + 8, column=0, padx=10, pady=5, sticky="w")

            sensor_entry = tk.Entry(self.root, textvariable=self.get_variable_by_index(i), state="readonly",
                                    font=('Arial', 16))
            sensor_entry.grid(row=i + 8, column=1, padx=10, pady=5)

        # NPK Values Display
        npk_values_label = tk.Label(self.root, text="NPK Values:", font=('Arial', 18, 'bold'))
        npk_values_label.grid(row=7, column=2, pady=10, columnspan=2)

        npk_labels = ["NPK Sensor 1", "NPK Sensor 2"]

        for i, label in enumerate(npk_labels):
            npk_label = tk.Label(self.root, text=label, font=('Arial', 16))
            npk_label.grid(row=i + 8, column=2, padx=10, pady=5, sticky="w")

            npk_entry = tk.Entry(self.root, textvariable=self.get_variable_by_index(i + len(sensor_labels)),
                                 state="readonly", font=('Arial', 16))
            npk_entry.grid(row=i + 8, column=3, padx=10, pady=5)

        # Last Updated Label
        self.last_updated_label = tk.Label(self.root, text="", font=('Arial', 12))
        self.last_updated_label.grid(row=0, column=4, padx=10, pady=10, sticky="e")

        # Restart Button
        restart_button = tk.Button(self.root, text="Restart", command=self.restart_app, font=('Arial', 16))
        restart_button.grid(row=0, column=0, padx=10, pady=10, sticky="e")

        # Update Date and Time
        self.update_clock()

    def update_clock(self):
        raw_TS = datetime.now()
        formatted_now = raw_TS.strftime("%d-%m-%Y %I:%M:%S %p")
        self.label_date_now.config(text=f"Current Date: {raw_TS.strftime('%d %b %Y')}")
        self.label_time_now.config(text=f"Current Time: {raw_TS.strftime('%I:%M:%S %p')}")

        # Check and update countdown every 24 hours
        if raw_TS.hour == 0 and raw_TS.minute == 0 and raw_TS.second == 0:
            self.update_countdown()

        self.root.after(1000, self.update_clock)
        return formatted_now

    def update_countdown(self):
        try:
            remaining_days = int(self.days_countdown_var.get())
            if remaining_days > 0:
                remaining_days -= 1
                self.days_countdown_var.set(str(remaining_days))
        except ValueError:
            pass

    def update_values(self, fetched_values):
        selected_crop, selected_stage = self.get_selected_values()
        if selected_crop and selected_stage:
            self.update_min_requirements(selected_crop, selected_stage)
            for key in fetched_values:
                sensor_value = fetched_values[key]
                self.set_variable_by_index(key, sensor_value)

            # Update countdown based on remaining days
            try:
                self.remaining_days = int(self.days_countdown_var.get())
                self.remaining_days = max(self.remaining_days, 0)
            except ValueError:
                pass
            finally:
                self.days_countdown_var.set(str(self.remaining_days))

            # Display last updated time
            formatted_now = self.update_clock()
            self.last_updated_label.config(text=f"Last Updated At: {formatted_now}")

    def get_selected_values(self):
        return self.crop_var.get(), self.stage_var.get()

    def get_variable_by_index(self, index):
        all_variables = [
            self.moisture_sensor_values[0],
            self.moisture_sensor_values[1],
            self.moisture_sensor_values[2],
            self.moisture_sensor_values[3],
            self.npk_sensor_values[0],
            self.npk_sensor_values[1],
            self.humidity_var
        ]
        return all_variables[index]

    def set_variable_by_index(self, index, value):
        variable = self.get_variable_by_index(index)
        variable.set(value)

    def update_min_requirements(self, crop, stage):
        min_humidity = min_requirements[crop][stage]["humidity"]
        min_npk = min_requirements[crop][stage]["npk"]

        self.min_humidity_var.set(min_humidity)
        self.min_npk_var.set(f"N: {min_npk['N']} - P: {min_npk['P']} - K: {min_npk['K']}")

    def restart_app(self):
        self.root.destroy()
        main()


def main():
    root = tk.Tk()
    mqtt_client = mqtt.Client("rpi_client_gui")
    app = SmartIrrigationSystemGUI(root, mqtt_client)
    root.mainloop()

if __name__ == "__main__":
    main()
