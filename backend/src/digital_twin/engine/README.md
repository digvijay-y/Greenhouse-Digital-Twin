# 🔧 Digital Twin Engine (C++)

## Overview

The **Digital Twin Engine** is a high-performance C++ module that simulates soil moisture dynamics in real-time. It provides two core algorithms:

1. **Laplace Solver**: Computes 2D steady-state moisture distribution from boundary conditions
2. **What-If Simulator**: Predicts future moisture evolution over time with irrigation events

Python bindings via pybind11 allow seamless integration with the PyTorch PINN and data generation pipeline.

## Architecture

```
backend/src/digital_twin/engine/
├── include/
│   ├── laplace_solver.hpp          # Steady-state 2D solver
│   ├── whatif_simulator.hpp        # Time evolution simulator
│   └── digital_twin_engine.hpp
├── src/
│   ├── laplace_solver.cpp
│   ├── whatif_simulator.cpp
│   └── CMakeLists.txt
├── python/
│   ├── bindings.cpp                # pybind11 Python interface
│   └── twin_engine.py              # High-level Python wrapper
└── build/                          # Compiled binaries (auto-generated)
```

---

## 1. Laplace Solver: Steady-State Moisture Distribution

### Problem Statement

Given 4 corner sensor readings (Dirichlet boundary conditions), compute the 2D moisture distribution across the greenhouse at a single time step.

**Governing Equation: Laplace's Equation**

$$\nabla^2 u = \frac{\partial^2 u}{\partial x^2} + \frac{\partial^2 u}{\partial y^2} = 0$$

**Physical Interpretation**: In steady state (no time change), moisture spreads isotropically until equilibrium.

### Boundary Conditions

Four corner sensors fix the domain boundaries:

$$u(x, y) = \begin{cases}
m_1 & \text{at corner } (0, 0) \text{ (bottom-left)} \\
m_2 & \text{at corner } (L, 0) \text{ (bottom-right)} \\
m_3 & \text{at corner } (0, L) \text{ (top-left)} \\
m_4 & \text{at corner } (L, L) \text{ (top-right)}
\end{cases}$$

**Edge Interpolation**: Linear interpolation between corners

$$u(\text{edge between } m_i \text{ and } m_j) = (1-t) \cdot m_i + t \cdot m_j$$

where $t \in [0, 1]$ is the fractional position along the edge.

### Algorithm: Jacobi Iterative Method

The **Jacobi method** solves the discrete Laplace equation via fixed-point iteration using a **4-point stencil**:

$$u_{i,j}^{(k+1)} = \frac{1}{4}\left(u_{i-1,j}^{(k)} + u_{i+1,j}^{(k)} + u_{i,j-1}^{(k)} + u_{i,j+1}^{(k)}\right)$$

**Discrete Problem**:
On an $n_x \times n_y$ grid with spacing $h = 1/(n_x - 1)$:

$$u_{i,j} \approx \frac{1}{4}(u_{W} + u_{E} + u_{N} + u_{S})$$

where W, E, N, S are west, east, north, south neighbors.

### Convergence Criterion

Iteration continues until maximum residual falls below tolerance:

$$\max_{i,j} |u_{i,j}^{(k+1)} - u_{i,j}^{(k)}| < \epsilon = 10^{-4}$$

Or maximum iterations reached (default: 1000).

### Quick Start

#### Build

```bash
cd backend/src/digital_twin/engine
bash build.sh
```

### Use in Python

```python
import sys
sys.path.insert(0, 'build')

import twin_engine_py as te

# Compute moisture distribution
grid = te.compute_moisture_distribution(80, 60, 45, 55)

# Run what-if simulation
sim = te.WhatIfSimulator()
result = sim.simulate([80, 60, 45, 55], 28.0, 150.0, 12.0, 72, 0.5)
print(result['zones']['zone1']['final_moisture'])
```

---

## 2. What-If Simulator: Time Evolution with Irrigation

### Problem Statement

Given initial moisture at 4 zones, ambient temperature, and watering schedule, predict moisture evolution over time.

**Governing Physics**:

1. **Evaporation**: Water loss proportional to current moisture (exponential decay)
2. **Temperature Coupling**: Hotter → faster evaporation
3. **Irrigation Events**: Periodic water addition

### Physics Model

#### A. Exponential Evaporation

Moisture decays exponentially in each zone:

$$M(t) = M_0 \cdot e^{-k \cdot t}$$

Where $k$ is the **decay constant** (inverse of time constant).

**Rate equation**:

$$\frac{dM}{dt} = -k \cdot M$$

This captures diffusion out of the zone and plant uptake.

#### B. Temperature Dependence

Evaporation increases with temperature (Q10 effect):

$$k(T) = k_{\text{base}} \cdot \exp\left(\alpha \cdot (T - T_{\text{ref}})\right)$$

Or linear approximation (used in code):

$$k(T) = k_{\text{base}} \cdot (1 + 0.03 \cdot (T - 25))$$

**Interpretation**:
- At $T = 25°C$: $k = k_{\text{base}}$ (baseline)
- At $T = 35°C$: $k = 1.3 \times k_{\text{base}}$ (+30% faster loss)
- At $T = 15°C$: $k = 0.7 \times k_{\text{base}}$ (-30% slower loss)

**Sensitivity coefficient**: $\beta = 0.03$ °C$^{-1}$ (3% change per °C)

#### C. Irrigation Model

When watering event occurs:

$$M_{\text{after}} = M_{\text{before}} + \text{gain}$$

Where moisture gain is:

$$\text{gain} = \frac{\text{water\_ml}}{100} \times g_{\text{factor}}$$

Default: $g_{\text{factor}} = 5\%$ per 100 ml (configurable)

**Watering Strategy**:
- Fixed frequency: Every $f$ hours (e.g., 6-hour intervals)
- Fixed amount: $W$ ml per event (e.g., 50 ml)

### Discrete Simulation Algorithm

**Time stepping with explicit Euler method**:

$$M(t + \Delta t) = M(t) \cdot e^{-k(T) \cdot \Delta t}$$

---

## 3. High-Level Python Integration

```python
from python.twin_engine import TwinEngine

engine = TwinEngine(grid_size=100)

# Moisture distribution
grid = engine.compute_moisture_map(80, 60, 45, 55)

# What-if scenario
result = engine.simulate_scenario(
    current_moisture={'zone1': 80, 'zone2': 60, 'zone3': 45, 'zone4': 55},
    temperature=28.0,
    watering_ml=150,
    watering_hours=12,
    duration_hours=72
)
```

---

## 4. Performance Characteristics

| Operation | Grid Size | Time |
|-----------|-----------|------|
| Laplace solve | 100×100 | ~5 ms |
| Laplace solve | 200×200 | ~25 ms |
| Simulation 72h | 4 zones | ~0.5 ms |
| Python overhead | - | ~0.1 ms |

**Memory Usage**:
- 100×100 grid: ~80 KB
- 200×200 grid: ~320 KB
- Typical: negligible

---

## 5. Build & Compilation

### Dependencies

- CMake ≥ 3.15
- C++17 compiler (GCC 7+, Clang 5+, MSVC 2017+)
- pybind11 (auto-downloaded via CMake)

### Build Steps

```bash
cd backend/src/digital_twin/engine
bash build.sh
```

### Output Files

- **C++ library**: `build/libtwin_engine.so` (Linux), `.dll` (Windows)
- **Python module**: `build/twin_engine_py*.so`
- **Test executable**: `build/test_engine`

---

## 6. References

1. **Jacobi Method**: Quarteroni et al., "Numerical Mathematics," Springer, 2007.
2. **Diffusion Equation**: Evans, "Partial Differential Equations," AMS, 2010.
3. **Q10 Temperature Effects**: Lloyd & Taylor, "On Temperature Dependence of Soil Respiration," Functional Ecology, 1994.

---

## Integration

See `examples/gui_integration.py` for how to integrate with the existing MQTT GUI.
