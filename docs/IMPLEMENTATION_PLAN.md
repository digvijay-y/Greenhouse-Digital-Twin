# Greenhouse Digital Twin - Implementation Plan

> **Document Version:** 1.0  
> **Date:** February 28, 2026  
> **Project:** Greenhouse Digital Twin - Final Year Enhancement

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Current Architecture Analysis](#2-current-architecture-analysis)
3. [Phase 1: What-If Simulation Engine](#3-phase-1-what-if-simulation-engine)
4. [Phase 2: Generative AI Integration](#4-phase-2-generative-ai-integration)
5. [Phase 3: Cloud Deployment](#5-phase-3-cloud-deployment)
6. [Phase 4: Physics-Informed Neural Networks](#6-phase-4-physics-informed-neural-networks)
7. [Implementation Timeline](#7-implementation-timeline)
8. [File Structure Changes](#8-file-structure-changes)

---

## 1. Project Overview

### Current System Capabilities
- **Real-time MQTT sensor data collection** (moisture, temperature, NPK, pressure)
- **SQLite database storage** for historical data
- **Tkinter GUI** for desktop monitoring
- **MATLAB spatial interpolation** using Laplace equation
- **Web dashboard** (frontend) with Plotly.js visualization
- **Hardware integration** with ESP32, ESP8266, and Raspberry Pi Pico

### Target Enhancements (from TODO)
1. **What-If Engine** - Simulate future scenarios with temperature/watering variations
2. **PINNS** - Physics-Informed Neural Networks for enhanced prediction
3. **Platform Integration** - Web application or cloud deployment

---

## 2. Current Architecture Analysis

### Directory Structure Verification ✅

| Path | Status | Notes |
|------|--------|-------|
| `backend/src/digital_twin/state_manager/mqtt_gui_controller.py` | ✅ Working | Main entry point |
| `backend/src/utils/sensor_simulator.py` | ✅ Working | Test utility |
| `backend/src/services/mqtt_broker_client.py` | ✅ Working | MQTT subscriber |
| `backend/src/digital_twin/models/moisture_distribution_twin.m` | ✅ Fixed | DB path corrected |
| `frontend/index.html` | ✅ Valid | Web dashboard |

### Path Fix Applied
```matlab
# File: backend/src/digital_twin/models/moisture_distribution_twin.m
# OLD: dbfile = '/home/d/Documents/TIHIoTChanakya/greenhouse.db';
# NEW: dbfile = '/home/d/Documents/Greenhouse-Digital-Twin/backend/src/digital_twin/state_manager/greenhouse.db';
```

### Deprecation Warnings (Minor)
- `paho-mqtt` callback API v1 deprecation in `sensor_simulator.py` and `mqtt_broker_client.py`
- Upgrade to `mqtt.CallbackAPIVersion.VERSION2` recommended

---

## 3. Phase 1: What-If Simulation Engine

### 3.1 Overview
Transform the system from **passive monitoring** to **active prediction** with user-defined scenario simulation.

### 3.2 New Files to Create

```
backend/src/digital_twin/
├── simulation_engine/
│   ├── __init__.py
│   ├── what_if_simulator.py      # Core simulation logic
│   ├── evaporation_model.py      # Moisture decay model
│   └── watering_model.py         # Irrigation effect model
```

### 3.3 Backend Implementation

#### File: `backend/src/digital_twin/simulation_engine/what_if_simulator.py`

```python
"""
What-If Simulation Engine
Simulates soil moisture evolution based on user-defined scenarios.
"""
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class WhatIfSimulator:
    """
    Simulates moisture distribution over time based on:
    - Evaporation (exponential decay based on temperature)
    - Irrigation events (instant moisture increase)
    """
    
    def __init__(self):
        self.base_decay_constant = 0.02  # k value at 25°C
    
    def calculate_decay_constant(self, temperature: float) -> float:
        """
        Adjust evaporation rate based on temperature.
        Higher temperature = faster moisture loss.
        
        k(T) = k_base * (1 + 0.03 * (T - 25))
        """
        return self.base_decay_constant * (1 + 0.03 * (temperature - 25))
    
    def simulate_moisture(
        self,
        initial_moisture: Dict[str, float],
        ambient_temperature: float,
        watering_amount_ml: float,
        watering_frequency_hours: float,
        simulation_hours: int = 72,
        time_step_hours: float = 0.5
    ) -> Dict[str, List[Tuple[datetime, float]]]:
        """
        Run moisture simulation for specified duration.
        
        Parameters:
        -----------
        initial_moisture : dict
            Current moisture readings {'zone1': 50.0, 'zone2': 55.0, ...}
        ambient_temperature : float
            User-defined temperature (°C)
        watering_amount_ml : float
            Volume of water per irrigation event (mL)
        watering_frequency_hours : float
            Hours between irrigation events
        simulation_hours : int
            Total simulation duration (default: 72 hours)
        time_step_hours : float
            Simulation resolution (default: 0.5 hours)
        
        Returns:
        --------
        dict of zone: [(timestamp, moisture_value), ...]
        """
        k = self.calculate_decay_constant(ambient_temperature)
        moisture_gain = self._calculate_moisture_gain(watering_amount_ml)
        
        results = {zone: [] for zone in initial_moisture.keys()}
        current_moisture = initial_moisture.copy()
        start_time = datetime.now()
        
        steps = int(simulation_hours / time_step_hours)
        time_since_watering = 0.0
        
        for step in range(steps):
            t = step * time_step_hours
            current_time = start_time + timedelta(hours=t)
            time_since_watering += time_step_hours
            
            for zone in current_moisture:
                # Evaporation: M(t) = M0 * exp(-k * t)
                current_moisture[zone] *= np.exp(-k * time_step_hours)
                
                # Watering event
                if time_since_watering >= watering_frequency_hours:
                    current_moisture[zone] = min(100, current_moisture[zone] + moisture_gain)
                
                # Clamp values
                current_moisture[zone] = max(0, min(100, current_moisture[zone]))
                
                results[zone].append((current_time, current_moisture[zone]))
            
            if time_since_watering >= watering_frequency_hours:
                time_since_watering = 0.0
        
        return results
    
    def _calculate_moisture_gain(self, watering_amount_ml: float) -> float:
        """
        Convert watering amount to moisture percentage increase.
        Simplified: 100ml ≈ 5% moisture increase
        """
        return (watering_amount_ml / 100) * 5


def run_simulation_scenario(
    current_readings: Dict[str, float],
    temperature: float,
    watering_ml: float,
    frequency_hours: float,
    duration_hours: int = 72
) -> dict:
    """
    Convenience function for API endpoint.
    """
    simulator = WhatIfSimulator()
    results = simulator.simulate_moisture(
        initial_moisture=current_readings,
        ambient_temperature=temperature,
        watering_amount_ml=watering_ml,
        watering_frequency_hours=frequency_hours,
        simulation_hours=duration_hours
    )
    
    # Convert to JSON-serializable format
    return {
        zone: [
            {"timestamp": ts.isoformat(), "moisture": round(val, 2)}
            for ts, val in data
        ]
        for zone, data in results.items()
    }
```

### 3.4 GUI Enhancements

#### Add to `mqtt_gui_controller.py`:

```python
# Add these widgets in create_widgets():

# --- What-If Simulation Section ---
sim_frame = ttk.LabelFrame(self.root, text="What-If Simulation", padding=10)
sim_frame.grid(row=8, column=0, columnspan=4, padx=10, pady=10, sticky="ew")

# Input fields
ttk.Label(sim_frame, text="Watering Amount (mL):").grid(row=0, column=0, sticky="w")
self.watering_amount = tk.IntVar(value=100)
ttk.Entry(sim_frame, textvariable=self.watering_amount, width=10).grid(row=0, column=1)

ttk.Label(sim_frame, text="Frequency (hours):").grid(row=0, column=2, sticky="w")
self.watering_frequency = tk.IntVar(value=24)
ttk.Entry(sim_frame, textvariable=self.watering_frequency, width=10).grid(row=0, column=3)

ttk.Label(sim_frame, text="Temperature (°C):").grid(row=1, column=0, sticky="w")
self.sim_temperature = tk.DoubleVar(value=25.0)
ttk.Entry(sim_frame, textvariable=self.sim_temperature, width=10).grid(row=1, column=1)

# Simulate button
ttk.Button(sim_frame, text="🔮 Simulate Future", command=self.run_simulation).grid(
    row=1, column=2, columnspan=2, pady=5
)
```

### 3.5 Frontend Visualization Updates

#### Add to `frontend/src/js/app.js`:

```javascript
// What-If Simulation Module
const WhatIfSimulator = {
    plotSimulation(liveData, simulatedData) {
        const data = [
            {
                x: liveData.timestamps,
                y: liveData.values,
                name: 'Live Data',
                type: 'scatter',
                mode: 'lines',
                line: { dash: 'solid', width: 3 }
            },
            {
                x: simulatedData.timestamps,
                y: simulatedData.values,
                name: 'Simulated Scenario',
                type: 'scatter',
                mode: 'lines',
                line: { dash: 'dot', width: 2, color: '#ff7f0e' }
            }
        ];
        
        const layout = {
            title: 'Moisture Prediction: Live vs Simulated',
            legend: { orientation: 'h', y: -0.2 },
            xaxis: { title: 'Time' },
            yaxis: { title: 'Moisture %', range: [0, 100] }
        };
        
        Plotly.newPlot('simulation-chart', data, layout, { responsive: true });
    },
    
    async runSimulation(params) {
        const response = await fetch(`${API_BASE_URL}/simulate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });
        return response.json();
    }
};
```

---

## 4. Phase 2: Generative AI Integration

### 4.1 Overview
Add AI-powered agronomist recommendations using Gemini/OpenAI API.

### 4.2 New Files to Create

```
backend/src/digital_twin/
├── ai_advisor/
│   ├── __init__.py
│   ├── prompt_builder.py        # Constructs prompts from sensor data
│   ├── api_client.py            # Handles API calls to AI services
│   └── recommendation_engine.py # Main advisor logic
```

### 4.3 Implementation

#### File: `backend/src/digital_twin/ai_advisor/recommendation_engine.py`

```python
"""
AI-Augmented Advisory System
Provides expert agronomist recommendations using Generative AI.
"""
import os
import requests
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class SensorReadings:
    moisture_zones: Dict[str, float]
    temperature: float
    humidity: float
    nitrogen: int
    phosphorus: int
    potassium: int

class AIAdvisor:
    """
    Connects to Gemini/OpenAI API for agricultural recommendations.
    """
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "gemini"):
        self.api_key = api_key or os.getenv("GENAI_API_KEY")
        self.provider = provider
        
        if not self.api_key:
            raise ValueError("API key required. Set GENAI_API_KEY environment variable.")
        
        self.api_urls = {
            "gemini": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
            "openai": "https://api.openai.com/v1/chat/completions"
        }
    
    def build_prompt(self, readings: SensorReadings, simulation_params: Optional[dict] = None) -> str:
        """
        Construct a detailed prompt for the AI model.
        """
        prompt = f"""You are an expert agronomist specializing in greenhouse cultivation and precision agriculture.

## Current Sensor Readings:
- **Soil Moisture Zones:**
  - Zone 1: {readings.moisture_zones.get('zone1', 'N/A')}%
  - Zone 2: {readings.moisture_zones.get('zone2', 'N/A')}%
  - Zone 3: {readings.moisture_zones.get('zone3', 'N/A')}%
  - Zone 4: {readings.moisture_zones.get('zone4', 'N/A')}%
- **Temperature:** {readings.temperature}°C
- **Humidity:** {readings.humidity}%
- **NPK Values:**
  - Nitrogen (N): {readings.nitrogen} mg/kg
  - Phosphorus (P): {readings.phosphorus} mg/kg
  - Potassium (K): {readings.potassium} mg/kg

## Analysis Required:
1. Evaluate the current soil moisture distribution. Are any zones critically dry or waterlogged?
2. Assess the NPK levels. Is fertilizer supplementation needed?
3. Given the temperature and humidity, predict potential stress on crops.

## Provide:
- Specific irrigation recommendations (which zones, how much water)
- Fertilizer suggestions if NPK is imbalanced
- Any warnings about current conditions

Keep recommendations actionable and concise.
"""
        return prompt
    
    def get_recommendation(self, readings: SensorReadings) -> str:
        """
        Query the AI API and return the recommendation.
        """
        prompt = self.build_prompt(readings)
        
        if self.provider == "gemini":
            return self._call_gemini(prompt)
        elif self.provider == "openai":
            return self._call_openai(prompt)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def _call_gemini(self, prompt: str) -> str:
        url = f"{self.api_urls['gemini']}?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    
    def _call_openai(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "You are an expert agronomist."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500
        }
        
        response = requests.post(self.api_urls['openai'], headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        return data['choices'][0]['message']['content']


# Convenience function for integration
def get_ai_analysis(sensor_data: dict, api_key: Optional[str] = None) -> str:
    """
    Main entry point for AI recommendations.
    
    Args:
        sensor_data: Dict with moisture1-4, temperature, humidity, n, p, k
        api_key: Optional API key (defaults to env variable)
    
    Returns:
        AI-generated recommendation string
    """
    readings = SensorReadings(
        moisture_zones={
            'zone1': sensor_data.get('moisture1', 50),
            'zone2': sensor_data.get('moisture2', 50),
            'zone3': sensor_data.get('moisture3', 50),
            'zone4': sensor_data.get('moisture4', 50),
        },
        temperature=sensor_data.get('temperature', 25),
        humidity=sensor_data.get('humidity', 60),
        nitrogen=sensor_data.get('n', 0),
        phosphorus=sensor_data.get('p', 0),
        potassium=sensor_data.get('k', 0)
    )
    
    advisor = AIAdvisor(api_key=api_key)
    return advisor.get_recommendation(readings)
```

### 4.4 Security: Environment Variables

Create `.env` file (add to `.gitignore`):
```bash
GENAI_API_KEY=your_api_key_here
AI_PROVIDER=gemini  # or "openai"
```

---

## 5. Phase 3: Cloud Deployment

### 5.1 Web Application Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Cloud Platform                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   FastAPI   │  │  PostgreSQL │  │   MQTT Broker       │  │
│  │   Backend   │──│  Database   │  │   (Cloud HiveMQ)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         │                                    ▲               │
│         ▼                                    │               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                 React/Vue Frontend                   │    │
│  │         (Static hosting: Vercel/Netlify)            │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ MQTT / WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Greenhouse Hardware                         │
│     ESP32 + ESP8266 + Raspberry Pi Pico (On-premise)        │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 FastAPI Backend Implementation

#### File: `backend/src/api/main.py`

```python
"""
FastAPI Backend for Greenhouse Digital Twin
REST API for web dashboard and mobile apps.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
from datetime import datetime

app = FastAPI(
    title="Greenhouse Digital Twin API",
    description="Decision Support System for Smart Irrigation",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "../digital_twin/state_manager/greenhouse.db"


class SensorReading(BaseModel):
    timestamp: str
    temperature: Optional[float]
    humidity: Optional[float]
    moisture1: Optional[float]
    moisture2: Optional[float]
    moisture3: Optional[float]
    moisture4: Optional[float]
    n_value: Optional[int]
    p_value: Optional[int]
    k_value: Optional[int]


class SimulationParams(BaseModel):
    watering_amount_ml: int = 100
    watering_frequency_hours: int = 24
    ambient_temperature: float = 25.0
    duration_hours: int = 72


@app.get("/api/sensors/latest", response_model=SensorReading)
async def get_latest_reading():
    """Get the most recent sensor reading."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM sensor_data 
        ORDER BY timestamp DESC LIMIT 1
    """)
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="No sensor data available")
    
    return SensorReading(**dict(row))


@app.get("/api/sensors/history")
async def get_history(hours: int = 24):
    """Get historical sensor data."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM sensor_data 
        WHERE timestamp >= datetime('now', ? || ' hours')
        ORDER BY timestamp ASC
    """, (f"-{hours}",))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


@app.post("/api/simulate")
async def run_simulation(params: SimulationParams):
    """Run what-if simulation and return predictions."""
    from digital_twin.simulation_engine.what_if_simulator import run_simulation_scenario
    
    # Get current readings
    latest = await get_latest_reading()
    
    current = {
        'zone1': latest.moisture1 or 50,
        'zone2': latest.moisture2 or 50,
        'zone3': latest.moisture3 or 50,
        'zone4': latest.moisture4 or 50,
    }
    
    results = run_simulation_scenario(
        current_readings=current,
        temperature=params.ambient_temperature,
        watering_ml=params.watering_amount_ml,
        frequency_hours=params.watering_frequency_hours,
        duration_hours=params.duration_hours
    )
    
    return results


@app.post("/api/ai-analysis")
async def get_ai_recommendation():
    """Get AI-powered agronomist recommendation."""
    from digital_twin.ai_advisor.recommendation_engine import get_ai_analysis
    
    latest = await get_latest_reading()
    
    sensor_data = {
        'moisture1': latest.moisture1,
        'moisture2': latest.moisture2,
        'moisture3': latest.moisture3,
        'moisture4': latest.moisture4,
        'temperature': latest.temperature,
        'humidity': latest.humidity,
        'n': latest.n_value,
        'p': latest.p_value,
        'k': latest.k_value
    }
    
    try:
        recommendation = get_ai_analysis(sensor_data)
        return {"recommendation": recommendation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/valve/{valve_id}")
async def control_valve(valve_id: int, action: str):
    """Control irrigation valve (publish to MQTT)."""
    import paho.mqtt.publish as publish
    
    if valve_id not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Invalid valve ID")
    
    topic = f"esp32/relay{valve_id}"
    payload = "1" if action.upper() == "ON" else "0"
    
    publish.single(topic, payload, hostname="localhost")
    
    return {"status": "success", "valve": valve_id, "action": action}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 5.3 Docker Deployment

#### File: `docker-compose.yml`

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - GENAI_API_KEY=${GENAI_API_KEY}
      - DATABASE_URL=sqlite:///./greenhouse.db
    volumes:
      - ./backend/data:/app/data
    depends_on:
      - mqtt

  mqtt:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - mosquitto_data:/mosquitto/data

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  mosquitto_data:
```

---

## 6. Phase 4: Physics-Informed Neural Networks (PINNs)

### 6.1 Overview
Replace/enhance the MATLAB Laplace solver with a trainable neural network that respects physics constraints.

### 6.2 PINN Architecture

```python
"""
Physics-Informed Neural Network for Moisture Distribution
Solves the Laplace equation: ∇²u = 0
with learned corrections for real-world deviations.
"""
import torch
import torch.nn as nn
import numpy as np

class MoisturePINN(nn.Module):
    """
    PINN that predicts moisture distribution given:
    - Spatial coordinates (x, y)
    - Boundary conditions (4 sensor values)
    """
    
    def __init__(self, hidden_layers=4, neurons_per_layer=64):
        super().__init__()
        
        layers = []
        input_dim = 6  # x, y, m1, m2, m3, m4
        
        layers.append(nn.Linear(input_dim, neurons_per_layer))
        layers.append(nn.Tanh())
        
        for _ in range(hidden_layers - 1):
            layers.append(nn.Linear(neurons_per_layer, neurons_per_layer))
            layers.append(nn.Tanh())
        
        layers.append(nn.Linear(neurons_per_layer, 1))  # Output: moisture
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x, y, boundary_conditions):
        """
        Forward pass.
        
        Args:
            x: x-coordinates [batch_size]
            y: y-coordinates [batch_size]
            boundary_conditions: [m1, m2, m3, m4]
        """
        bc = boundary_conditions.expand(x.shape[0], -1)
        inputs = torch.cat([x.unsqueeze(1), y.unsqueeze(1), bc], dim=1)
        return self.network(inputs)
    
    def physics_loss(self, x, y, boundary_conditions):
        """
        Compute the Laplace equation residual: ∇²u = 0
        """
        x.requires_grad_(True)
        y.requires_grad_(True)
        
        u = self.forward(x, y, boundary_conditions)
        
        # First derivatives
        du_dx = torch.autograd.grad(u.sum(), x, create_graph=True)[0]
        du_dy = torch.autograd.grad(u.sum(), y, create_graph=True)[0]
        
        # Second derivatives (Laplacian)
        d2u_dx2 = torch.autograd.grad(du_dx.sum(), x, create_graph=True)[0]
        d2u_dy2 = torch.autograd.grad(du_dy.sum(), y, create_graph=True)[0]
        
        # Laplace residual should be zero
        laplacian = d2u_dx2 + d2u_dy2
        
        return torch.mean(laplacian ** 2)
    
    def boundary_loss(self, boundary_conditions, predictions_at_corners):
        """
        Enforce boundary conditions at sensor locations.
        """
        return nn.MSELoss()(predictions_at_corners, boundary_conditions)


def train_pinn(model, num_epochs=5000, learning_rate=1e-3):
    """
    Training loop for the PINN.
    """
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    
    # Generate training points (collocation points)
    x_train = torch.rand(1000) * 10  # 0-10m
    y_train = torch.rand(1000) * 10
    
    # Sample boundary conditions from database (example)
    bc_samples = torch.tensor([[50, 60, 45, 55]], dtype=torch.float32)
    
    for epoch in range(num_epochs):
        optimizer.zero_grad()
        
        # Physics loss
        loss_physics = model.physics_loss(x_train, y_train, bc_samples)
        
        # Boundary loss at corners
        corners_x = torch.tensor([0, 10, 0, 10], dtype=torch.float32)
        corners_y = torch.tensor([0, 0, 10, 10], dtype=torch.float32)
        corner_preds = model.forward(corners_x, corners_y, bc_samples)
        loss_boundary = model.boundary_loss(bc_samples.squeeze(), corner_preds.squeeze())
        
        # Total loss
        loss = loss_physics + 10 * loss_boundary
        
        loss.backward()
        optimizer.step()
        
        if epoch % 500 == 0:
            print(f"Epoch {epoch}: Physics={loss_physics.item():.6f}, Boundary={loss_boundary.item():.6f}")
    
    return model
```

### 6.3 Integration Points

1. **Replace MATLAB solver**: Use trained PINN for real-time inference
2. **Hybrid approach**: Use PINN for fast predictions, MATLAB for validation
3. **Transfer learning**: Pre-train on synthetic data, fine-tune on real sensor data

---

## 7. Implementation Timeline

| Week | Phase | Tasks |
|------|-------|-------|
| 1-2 | Phase 1 | What-If simulation backend + GUI integration |
| 3 | Phase 1 | Frontend visualization with Plotly.js |
| 4 | Phase 2 | AI Advisor backend (API integration) |
| 5 | Phase 2 | Security (env vars, API key management) |
| 6-7 | Phase 3 | FastAPI development + Docker setup |
| 8 | Phase 3 | Cloud deployment (AWS/GCP/Azure) |
| 9-10 | Phase 4 | PINN development and training |
| 11 | Phase 4 | PINN integration and testing |
| 12 | All | Final testing, documentation, presentation prep |

---

## 8. File Structure Changes

### New Files to Create

```
backend/src/
├── api/
│   ├── main.py                    # FastAPI application
│   └── routes/
│       ├── sensors.py             # Sensor data endpoints
│       ├── simulation.py          # What-if endpoints
│       └── ai.py                  # AI recommendation endpoints
├── digital_twin/
│   ├── simulation_engine/
│   │   ├── __init__.py
│   │   ├── what_if_simulator.py
│   │   ├── evaporation_model.py
│   │   └── watering_model.py
│   ├── ai_advisor/
│   │   ├── __init__.py
│   │   ├── prompt_builder.py
│   │   ├── api_client.py
│   │   └── recommendation_engine.py
│   └── pinn/
│       ├── __init__.py
│       ├── moisture_pinn.py
│       └── train.py

frontend/src/
├── components/
│   ├── WhatIfSimulator.js
│   ├── AIAdvisor.js
│   └── MoistureHeatmap.js
├── js/
│   └── simulation.js

# Root level
├── docker-compose.yml
├── .env.example
└── Dockerfile
```

### Updated Dependencies (`requirements.txt`)

```txt
# Existing
paho-mqtt>=2.0.0
python-telegram-bot>=20.0
Django>=5.0
openpyxl>=3.1.0

# New for Phase 1-3
fastapi>=0.100.0
uvicorn>=0.23.0
python-dotenv>=1.0.0
requests>=2.31.0

# New for Phase 4 (PINNs)
torch>=2.0.0
numpy>=1.24.0
scipy>=1.10.0
```

---

## Quick Start After Implementation

```bash
# 1. Setup environment
cd backend
source venv/bin/activate
pip install -r requirements.txt

# 2. Set API key for AI features
export GENAI_API_KEY="your_key_here"

# 3. Start MQTT broker
sudo systemctl start mosquitto

# 4. Run FastAPI backend
cd src/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 5. Open frontend
# Navigate to http://localhost:8000/docs for API documentation
# Or open frontend/index.html for web dashboard
```

---

**Document prepared for Greenhouse Digital Twin Final Year Project Enhancement**
