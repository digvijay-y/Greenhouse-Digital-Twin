# 🌱 Greenhouse Digital Twin

A greenhouse monitoring and digital twin platform with real-time telemetry and What-If simulation.

## 📁 Project Structure

```
Greenhouse-Digital-Twin/
├── firmware/                          # Microcontroller code
│   ├── esp32_main/src/
│   │   ├── sensors/                   # NPK, soil temp/humidity sensors
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
│   │   │   └── pinns/                 # Physics-Informed NN model
│   │   ├── api/                       # FastAPI/Django routes
│   │   ├── services/                  # MQTT services
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
│  │                 │  │   - Moisture Decay Trends   │   │
│  └─────────────────┘  └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 🔧 Hardware Components

| Component | Purpose |
|-----------|---------|
| ESP32 | NPK sensor + MQTT publisher |
| Raspberry Pi Pico | Soil moisture + BME280 |

## 📡 MQTT Topics

| Topic | Description |
|-------|-------------|
| `pico1/moisture1` | Soil moisture sensor 1 |
| `pico1/moisture2` | Soil moisture sensor 2 |
| `pico2/moisture1` | Soil moisture sensor 3 |
| `pico2/moisture2` | Soil moisture sensor 4 |
| `pico1/bme280` | Temperature, humidity, pressure |
| `esp32/npk` | NPK sensor values (JSON) |

## 🗂️ Kaggle Dataset Recommendation (For Hybrid Training)

If you are under a deadline, use **hybrid training** (synthetic + Kaggle) from day one.

### What to download

Use this Kaggle search and pick a CSV dataset focused on soil moisture time-series:

https://www.kaggle.com/search?q=soil+moisture+dataset

### Best-fit dataset profile

Choose a dataset that has most of these columns:
- Soil moisture: `moisture` or `soil_moisture` (required)
- Temperature: `temperature` or `temp` (recommended)
- Time: `timestamp`, `datetime`, or `date` (recommended)
- Location: `x/y` or `lat/lon` (optional)

The current Kaggle adapter in this repo can handle missing optional columns by filling safe defaults.

### Fastest workflow

1. Download one Kaggle CSV to your machine (example: `~/Downloads/soil_moisture.csv`)
2. Run hybrid training command:

```bash
./scripts/train_pinn.sh --kaggle-csv ~/Downloads/soil_moisture.csv --kaggle-ratio 0.3
```

### Do you need Kaggle to start?

No. You can start with synthetic only (no download):

```bash
./scripts/train_pinn.sh
```

Then switch to hybrid once your CSV is ready.

## 📊 Digital Twin

### C++ Simulation Engine (NEW!)
High-performance engine with Python bindings:
- **Laplace Solver**: 2D moisture distribution (ported from MATLAB)
- **What-If Simulator**: Future prediction with evaporation/irrigation models
- **10-100x faster** than pure Python implementation on larger grids/workloads

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
- **PINN Training Pipeline** - Data generation, training script, and launcher

## 🔄 In Progress:
- **PINNs** - Physics-Informed Neural Networks model tuning and evaluation

## 📋 ToDo:
- **Cloud Deployment** - Deploy as web platform
- **GenAI Integration** - AI-powered agronomist recommendations

## 📝 License

MIT License
