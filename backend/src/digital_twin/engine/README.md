# Greenhouse Digital Twin - C++ Engine

A high-performance C++ engine for greenhouse moisture simulation, with Python bindings.

## Features

- **Laplace Solver**: 2D moisture distribution using Laplace equation (ported from MATLAB)
- **What-If Simulator**: Future moisture prediction with evaporation/irrigation models
- **Python Bindings**: Seamless integration with existing Python code via pybind11

## Quick Start

### Build

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

### High-Level Wrapper

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

## Project Structure

```
engine/
├── CMakeLists.txt          # Build configuration
├── build.sh                # Build script
├── README.md               # This file
├── include/
│   ├── digital_twin_engine.hpp  # Main header
│   ├── laplace_solver.hpp       # Laplace solver
│   └── whatif_simulator.hpp     # What-if simulator
├── src/
│   ├── laplace_solver.cpp       # Laplace implementation
│   └── whatif_simulator.cpp     # Simulator implementation
├── python/
│   ├── bindings.cpp            # pybind11 bindings
│   └── twin_engine.py          # Python wrapper
├── tests/
│   └── test_engine.cpp         # C++ tests
└── examples/
    └── gui_integration.py      # GUI integration example
```

## API Reference

### LaplaceSolver

```cpp
LaplaceSolver solver(100, 100);  // 100x100 grid
BoundaryConditions bc(80, 60, 45, 55);
Grid2D result = solver.solve(bc);
```

### WhatIfSimulator

```cpp
WhatIfSimulator sim;
auto result = sim.simulate(
    {80, 60, 45, 55},  // Initial moisture
    28.0,               // Temperature
    150.0,              // Water (ml)
    12.0,               // Frequency (hours)
    72,                 // Duration (hours)
    0.5                 // Time step (hours)
);
```

## Performance

| Operation | Grid Size | Time |
|-----------|-----------|------|
| Laplace Solve | 100x100 | ~50ms |
| Laplace Solve | 50x50 | ~12ms |
| What-If (72h) | - | ~1ms |

## Integration

See `examples/gui_integration.py` for how to integrate with the existing MQTT GUI.
