import paho.mqtt.client as mqtt
import tkinter as tk
from tkinter import ttk
from openpyxl import Workbook
from datetime import datetime, timedelta
import time
import json
import sqlite3

DB_FILE = "greenhouse.db"

class SmartIrrigationSystemGUI:
    
    def __init__(self, root, mqtt_client):
        self.root = root
        self.root.title("Digital Twin Analytical board")
        
        # --- Data Storage ---
        # Tkinter variables for the GUI
        self.tk_vars = {
            "moisture1": tk.DoubleVar(),
            "moisture2": tk.DoubleVar(),
            "moisture3": tk.DoubleVar(),
            "moisture4": tk.DoubleVar(),
            "npk": tk.StringVar(),
            "temperature": tk.DoubleVar(),
            "humidity": tk.DoubleVar(),
            "pressure": tk.DoubleVar(),
        }
        # Dictionary to hold the latest raw sensor values for DB insertion
        self.latest_data = {}

        # --- Database Setup ---
        self.db_conn = self.setup_database()

        # --- GUI and MQTT ---
        self.create_widgets()
        
        broker_address = '127.0.0.1'
        print(f"Connecting to MQTT broker at {broker_address}")
        self.mqtt_client = mqtt_client
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect(broker_address, 1883)
        self.mqtt_client.subscribe([
            ("pico1/moisture1", 0), ("pico1/moisture2", 0),
            ("pico2/moisture1", 0), ("pico2/moisture2", 0),
            ("pico1/bme280", 0), ("esp32/npk", 0)
        ])
        self.mqtt_client.loop_start()

    def setup_database(self):
        """Creates the database and table if they don't exist."""
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_data (
                timestamp TEXT PRIMARY KEY,
                temperature REAL,
                humidity REAL,
                pressure REAL,
                moisture1 REAL,
                moisture2 REAL,
                moisture3 REAL,
                moisture4 REAL,
                n_value INTEGER,
                p_value INTEGER,
                k_value INTEGER
            )
        ''')
        conn.commit()
        print(f"Database '{DB_FILE}' is ready.")
        return conn

    def on_message(self, client, userdata, msg):
        """Handles incoming MQTT messages, updates GUI, and stores latest data."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            print(f"Received message on topic {topic}: {payload}")

            # Update the dictionary holding the latest raw values
            if topic == 'pico1/moisture1':
                self.latest_data['moisture1'] = float(payload)
            elif topic == 'pico1/moisture2':
                self.latest_data['moisture2'] = float(payload)
            elif topic == 'pico2/moisture1':
                self.latest_data['moisture3'] = float(payload)
            elif topic == 'pico2/moisture2':
                self.latest_data['moisture4'] = float(payload)
            elif topic == 'esp32/npk':
                npk_data = json.loads(payload)
                self.latest_data.update(npk_data) # Adds 'n', 'p', 'k' to dict
                self.tk_vars["npk"].set(f"N:{npk_data.get('n')}, P:{npk_data.get('p')}, K:{npk_data.get('k')}")
            elif topic == 'pico1/bme280':
                temp, hum, pres = payload.split(',')
                self.latest_data['temperature'] = float(temp)
                self.latest_data['humidity'] = float(hum)
                self.latest_data['pressure'] = float(pres)
                # BME280 is the trigger to save a full record to the database
                self.save_data_to_db()

            # Update the GUI display after processing
            self.update_gui_displays()
            self.update_last_updated()

        except Exception as e:
            print(f"Error processing message on topic {msg.topic}: {e}")

    def save_data_to_db(self):
        """Saves the latest complete set of sensor data to the database."""
        try:
            cursor = self.db_conn.cursor()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Prepare data, using None for any missing values
            data_to_insert = (
                timestamp,
                self.latest_data.get('temperature'),
                self.latest_data.get('humidity'),
                self.latest_data.get('pressure'),
                self.latest_data.get('moisture1'),
                self.latest_data.get('moisture2'),
                self.latest_data.get('moisture3'),
                self.latest_data.get('moisture4'),
                self.latest_data.get('n'),
                self.latest_data.get('p'),
                self.latest_data.get('k')
            )

            sql = '''
                INSERT INTO sensor_data (
                    timestamp, temperature, humidity, pressure,
                    moisture1, moisture2, moisture3, moisture4,
                    n_value, p_value, k_value
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            cursor.execute(sql, data_to_insert)
            self.db_conn.commit()
            print(f"Saved data to DB at {timestamp}")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
        except Exception as e:
            print(f"Error saving data to DB: {e}")

    def update_gui_displays(self):
        """Updates all GUI fields from the latest data."""
        for key, var in self.tk_vars.items():
            if key in self.latest_data and key != "npk": # NPK is handled separately
                var.set(self.latest_data[key])

    def create_widgets(self):
        self.label_date_now = tk.Label(self.root, text="Current Date", font=('Arial', 15))
        self.label_date_now.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        self.label_time_now = tk.Label(self.root, text="Current Time", font=('Arial', 15))
        self.label_time_now.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        # Sensor Values Display
        sensor_values_label = tk.Label(self.root, text="Sensor Values:", font=('Arial', 18, 'bold'))
        sensor_values_label.grid(row=2, column=0, columnspan=2, pady=8)

        moisture_labels = ["Moisture Sensor 1", "Moisture Sensor 2", "Moisture Sensor 3", "Moisture Sensor 4"]
        for i, label in enumerate(moisture_labels):
            sensor_label = tk.Label(self.root, text=label, font=('Arial', 16))
            sensor_label.grid(row=i + 3, column=0, padx=10, pady=5, sticky="w")
            sensor_entry = tk.Entry(self.root, textvariable=self.tk_vars[f"moisture{i+1}"], state="readonly", font=('Arial', 16))
            sensor_entry.grid(row=i + 3, column=1, padx=10, pady=5)

        # NPK Values Display
        npk_label = tk.Label(self.root, text="NPK Sensor", font=('Arial', 16))
        npk_label.grid(row=7, column=0, padx=10, pady=5, sticky="w")
        npk_entry = tk.Entry(self.root, textvariable=self.tk_vars["npk"], state="readonly", font=('Arial', 16))
        npk_entry.grid(row=7, column=1, padx=10, pady=5)

        # BME280 Display
        bme_label = tk.Label(self.root, text="BME280 Sensor:", font=('Arial', 18, 'bold'))
        bme_label.grid(row=2, column=2, columnspan=2, pady=8)
        
        temp_label = tk.Label(self.root, text="Temperature (°C)", font=('Arial', 16))
        temp_label.grid(row=3, column=2, padx=10, pady=5, sticky="w")
        temp_entry = tk.Entry(self.root, textvariable=self.tk_vars["temperature"], state="readonly", font=('Arial', 16))
        temp_entry.grid(row=3, column=3, padx=10, pady=5)

        hum_label = tk.Label(self.root, text="Humidity (%)", font=('Arial', 16))
        hum_label.grid(row=4, column=2, padx=10, pady=5, sticky="w")
        hum_entry = tk.Entry(self.root, textvariable=self.tk_vars["humidity"], state="readonly", font=('Arial', 16))
        hum_entry.grid(row=4, column=3, padx=10, pady=5)

        pres_label = tk.Label(self.root, text="Pressure (hPa)", font=('Arial', 16))
        pres_label.grid(row=5, column=2, padx=10, pady=5, sticky="w")
        pres_entry = tk.Entry(self.root, textvariable=self.tk_vars["pressure"], state="readonly", font=('Arial', 16))
        pres_entry.grid(row=5, column=3, padx=10, pady=5)

        # Last Updated Label
        self.last_updated_label = tk.Label(self.root, text="", font=('Arial', 12))
        self.last_updated_label.grid(row=0, column=2, padx=10, pady=10, sticky="e")

        # Restart Button
        restart_button = tk.Button(self.root, text="Restart", command=self.restart_app, font=('Arial', 16))
        restart_button.grid(row=0, column=0, padx=10, pady=10, sticky="e")

        # Update Date and Time
        self.update_clock()

    def update_clock(self):
        raw_TS = datetime.now()
        self.label_date_now.config(text=f"Current Date: {raw_TS.strftime('%d %b %Y')}")
        self.label_time_now.config(text=f"Current Time: {raw_TS.strftime('%I:%M:%S %p')}")
        self.root.after(1000, self.update_clock)

    def update_last_updated(self):
        formatted_now = datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")
        self.last_updated_label.config(text=f"Last Updated At: {formatted_now}")

    def restart_app(self):
        print("Restarting application...")
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        self.db_conn.close()
        self.root.destroy()
        main()

def main():
    root = tk.Tk()
    # Use the newer API version for the client
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    app = SmartIrrigationSystemGUI(root, mqtt_client)
    root.mainloop()
    # Cleanup on exit
    print("Application closing.")
    app.db_conn.close()

if __name__ == "__main__":
    main()
