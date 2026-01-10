import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta

fetched_values = {1: '54', 2: '45', 3: '43', 4: '43', 5: '43', 6: '43'}

# Dictionary to store minimum requirements for each crop and stage
min_requirements = {
    "Tomato": {
        "Initial": {"humidity": 50, "npk": {"N": 20, "P": 20, "K": 20}},
        "Medium": {"humidity": 60, "npk": {"N": 30, "P": 30, "K": 30}},
        "Final": {"humidity": 70, "npk": {"N": 40, "P": 40, "K": 40}},
    },
    "Onion": {
        "Initial": {"humidity": 40, "npk": {"N": 10, "P": 10, "K": 10}},
        "Medium": {"humidity": 50, "npk": {"N": 20, "P": 20, "K": 20}},
        "Final": {"humidity": 60, "npk": {"N": 30, "P": 30, "K": 30}},
    },
    "Potato": {
        "Initial": {"humidity": 30, "npk": {"N": 5, "P": 5, "K": 5}},
        "Medium": {"humidity": 40, "npk": {"N": 10, "P": 10, "K": 10}},
        "Final": {"humidity": 50, "npk": {"N": 15, "P": 15, "K": 15}},
    },
}


class SmartIrrigationSystemGUI:
    def __init__(self, root):
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

    def update_values(self):
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
    app = SmartIrrigationSystemGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
