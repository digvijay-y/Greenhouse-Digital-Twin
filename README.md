# 🌱 Greenhouse Digital Twin

A smart irrigation system with real-time monitoring, digital twin simulation, with What-if Engine to simulate scenarios without distrubing the producation.

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
│   │   │   ├── engine/                # C++ simulation engine (NEW!)
│   │   │   │   ├── include/           # C++ headers
│   │   │   │   ├── src/               # C++ implementation
│   │   │   │   └── python/            # Python bindings
│   │   │   ├── models/                # Twin.m simulation model (legacy)
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

### Step 1: Launch the Platform
```bash
./scripts/launch.sh
```

This will:
1. Start the MQTT broker (Mosquitto)
2. **Display the broker IP address** - copy this for your sensor nodes
3. Build the C++ engine if needed
4. Show launch options

### Step 2: Configure Your Sensor Nodes

The launch script displays the broker IP like this:
```
╔════════════════════════════════════════════════════════════╗
║  📡 MQTT BROKER CONFIGURATION FOR NODES                    ║
╠════════════════════════════════════════════════════════════╣
║   Broker IP:   192.168.xxx.xxx                             ║
║   Broker Port: 1883                                        ║
╚════════════════════════════════════════════════════════════╝
```

Update the firmware files with this IP:
- **ESP32**: `firmware/esp32_main/src/sensors/*.ino`
- **Pico**: `firmware/sensor_nodes/pico/*.py`

### Step 3: Choose Launch Option

| Option | Use When |
|--------|----------|
| **1) Dashboard only** | Real sensor nodes are connected |
| **2) Dashboard + Simulator** | Testing without hardware |
| **3) Simulator only** | Generate test MQTT data |
| **4) Train PINNs** | Train the neural network model |

### Manual Setup (Alternative)

#### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

#### 2. Build C++ Engine
```bash
cd backend/src/digital_twin/engine
bash build.sh
```

#### 3. Start MQTT Broker
```bash
sudo apt install mosquitto mosquitto-clients
sudo systemctl start mosquitto
```

#### 4. Run Dashboard
```bash
cd frontend/python_gui
export PYTHONPATH=../../backend/src/digital_twin/engine/build:$PYTHONPATH
python dashboard.py
```

#### 5. Test with Simulator (optional, if no hardware)
```bash
python scripts/mqtt_simulator.py --interval 3
```

## Architecture
```
┌─────────────────────────────────────────────────────────┐
│                   Python Application                     │
│   (GUI / FastAPI / Data Layer)                          │
└─────────────────────────────────────────────────────────┘
                          │
                    pybind11 bindings
                          │
┌─────────────────────────────────────────────────────────┐
│              C++ Digital Twin Engine                     │
│  ┌─────────────────┐  ┌─────────────────────────────┐   │
│  │ Laplace Solver  │  │   What-If Simulator         │   │
│  │ (from MATLAB)   │  │   - Evaporation Model       │   │
│  │                 │  │   - Irrigation Model        │   │
│  └─────────────────┘  └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
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

### C++ Simulation Engine (NEW!)
High-performance engine with Python bindings:
- **Laplace Solver**: 2D moisture distribution (ported from MATLAB)
- **What-If Simulator**: Future prediction with evaporation/irrigation models
- **10-100x faster** than pure Python implementation i.e For larger systems. for this, its overengineering

```bash
# Build the engine
cd backend/src/digital_twin/engine
bash build.sh

# Use in Python
python -c "
import sys; sys.path.insert(0, 'build')
import twin_engine_py as te
grid = te.compute_moisture_distribution(80, 60, 45, 55)
print(f'Grid shape: {grid.shape}')
"
```

### Legacy MATLAB Model
The MATLAB model (`moisture_distribution_twin.m`) remains available for visualization/validation.

## ✅ Completed:
- **C++ Engine** - High-performance Laplace solver + What-If simulator with pybind11
- **Python Integration** - Seamless use from existing MQTT GUI
- **What-If Dashboard** - Enhanced Tkinter GUI with matplotlib heatmaps and simulation controls

## 🔄 In Progress:
- **PINNs** - Physics-Informed Neural Networks for enhanced prediction

## 📋 ToDo:
- **Cloud Deployment** - Deploy as web platform
- **GenAI Integration** - AI-powered agronomist recommendations

## 📝 License

MIT License
