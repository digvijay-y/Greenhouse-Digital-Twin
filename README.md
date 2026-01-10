# 🌱 Greenhouse Digital Twin

A smart irrigation system with real-time monitoring, digital twin simulation, and automated decision-making for greenhouse management.

## 📁 Project Structure

```
Greenhouse-Digital-Twin/
├── firmware/                          # Microcontroller code
│   ├── esp32_main/src/
│   │   ├── sensors/                   # NPK, soil temp/humidity sensors
│   │   ├── actuators/                 # Relay control for valves
│   │   └── mqtt_client/               # MQTT communication
│   └── sensor_nodes/pico/             # Raspberry Pi Pico sensor nodes
│
├── backend/                           # Python server
│   ├── src/
│   │   ├── digital_twin/              # Digital Twin core logic
│   │   │   ├── models/                # Twin.m simulation model
│   │   │   ├── state_manager/         # Current/predicted state
│   │   │   ├── anomaly_detection/     # Fault detection
│   │   │   └── irrigation_engine/     # Automated decisions
│   │   ├── api/                       # FastAPI/Django routes
│   │   ├── services/                  # MQTT, Telegram bot
│   │   └── utils/                     # Helpers, simulators
│   └── requirements.txt
│
├── frontend/                          # Web dashboard
│   ├── src/
│   │   ├── css/                       # Stylesheets
│   │   ├── js/                        # JavaScript
│   │   └── pages/                     # Dashboard pages
│   └── index.html
│
├── database/                          # SQLite database
├── docs/                              # Documentation
└── scripts/                           # Deployment scripts
```

## 🚀 Quick Start

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. Start MQTT Broker
```bash
# Install Mosquitto
sudo apt install mosquitto mosquitto-clients

# Start broker
sudo systemctl start mosquitto
```

### 3. Run the Application
```bash
cd backend/src/digital_twin/state_manager
python mqtt_gui_controller.py
```

### 4. Simulate Sensors (for testing)
```bash
cd backend/src/utils
python sensor_simulator.py
```

## 🔧 Hardware Components

| Component | Purpose |
|-----------|---------|
| ESP32 | NPK sensor, relay control |
| ESP8266 | Solenoid valve relays |
| Raspberry Pi Pico | Soil moisture + BME280 |
| Solenoid Valves | Irrigation control |

## 📡 MQTT Topics

| Topic | Description |
|-------|-------------|
| `pico1/moisture1` | Soil moisture sensor 1 |
| `pico1/moisture2` | Soil moisture sensor 2 |
| `pico2/moisture1` | Soil moisture sensor 3 |
Mo
| `pico2/moisture2` | Soil moisture sensor 4 |
| `pico1/bme280` | Temperature, humidity, pressure |
| `esp32/npk` | NPK sensor values (JSON) |
| `esp32/relay1-3` | Valve control commands |

## 📊 Digital Twin

The MATLAB model (`Twin.m`) simulates real-time moisture distribution across the greenhouse using:
- **Laplace equation** for heat/moisture diffusion
- **4-point sensor boundary conditions**
- **Live database integration**

## 📝 License

MIT License
