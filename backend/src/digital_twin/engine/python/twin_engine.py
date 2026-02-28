"""
Digital Twin Engine - Python Wrapper

High-level Python interface for the C++ Digital Twin Engine.
This module provides easy integration with the existing MQTT GUI.

Usage:
------
>>> from twin_engine import TwinEngine
>>> 
>>> engine = TwinEngine()
>>> 
>>> # Compute moisture distribution
>>> grid = engine.compute_moisture_map(80, 60, 45, 55)
>>> 
>>> # Run what-if simulation
>>> result = engine.simulate_scenario(
...     current_moisture={'zone1': 80, 'zone2': 60, 'zone3': 45, 'zone4': 55},
...     temperature=28.0,
...     watering_ml=150,
...     watering_hours=12,
...     duration_hours=72
... )
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

# Add build directory to path
ENGINE_DIR = Path(__file__).parent.parent
BUILD_DIR = ENGINE_DIR / "build"

if BUILD_DIR.exists():
    sys.path.insert(0, str(BUILD_DIR))

try:
    import twin_engine_py as _engine
    ENGINE_AVAILABLE = True
except ImportError:
    ENGINE_AVAILABLE = False
    print("Warning: C++ engine not built. Run 'bash build.sh' first.")
    print(f"Expected at: {BUILD_DIR}")


class TwinEngine:
    """
    High-level interface to the Digital Twin C++ engine.
    
    Provides:
    - Moisture distribution computation (Laplace solver)
    - What-if simulation (evaporation + irrigation)
    - Easy integration with existing Python code
    """
    
    def __init__(self, grid_size: int = 100):
        """
        Initialize the Twin Engine.
        
        Args:
            grid_size: Resolution for moisture distribution grid (default: 100x100)
        """
        if not ENGINE_AVAILABLE:
            raise RuntimeError(
                "C++ engine not available. Build it first:\n"
                f"  cd {ENGINE_DIR}\n"
                "  bash build.sh"
            )
        
        self.grid_size = grid_size
        self._solver = _engine.LaplaceSolver(grid_size, grid_size)
        self._simulator = _engine.WhatIfSimulator()
        
        # Version info
        self.version = _engine.get_version()
    
    def compute_moisture_map(
        self,
        moisture1: float,
        moisture2: float,
        moisture3: float,
        moisture4: float
    ) -> np.ndarray:
        """
        Compute 2D moisture distribution from 4 sensor values.
        
        Uses Laplace equation to interpolate moisture across the greenhouse.
        This is a direct replacement for the MATLAB Twin.m simulation.
        
        Args:
            moisture1: Top-left sensor value (Zone 1)
            moisture2: Top-right sensor value (Zone 2)
            moisture3: Bottom-left sensor value (Zone 3)
            moisture4: Bottom-right sensor value (Zone 4)
        
        Returns:
            2D NumPy array with interpolated moisture values
        """
        return _engine.compute_moisture_distribution(
            moisture1, moisture2, moisture3, moisture4, 
            self.grid_size
        )
    
    def simulate_scenario(
        self,
        current_moisture: Dict[str, float],
        temperature: float,
        watering_ml: float,
        watering_hours: float,
        duration_hours: int = 72,
        time_step_hours: float = 0.5
    ) -> Dict:
        """
        Run a what-if simulation to predict future moisture levels.
        
        Simulates moisture evolution based on:
        - Evaporation (temperature-dependent decay)
        - Periodic irrigation events
        
        Args:
            current_moisture: Dict with zone1, zone2, zone3, zone4 values
            temperature: Ambient temperature (°C)
            watering_ml: Water volume per irrigation event (ml)
            watering_hours: Hours between watering events
            duration_hours: Total simulation duration (default: 72)
            time_step_hours: Simulation resolution (default: 0.5)
        
        Returns:
            Dictionary with simulation results for each zone
        """
        # Extract moisture values in order
        moisture_list = [
            current_moisture.get('zone1', current_moisture.get('moisture1', 50)),
            current_moisture.get('zone2', current_moisture.get('moisture2', 50)),
            current_moisture.get('zone3', current_moisture.get('moisture3', 50)),
            current_moisture.get('zone4', current_moisture.get('moisture4', 50)),
        ]
        
        return self._simulator.simulate(
            moisture_list,
            temperature,
            watering_ml,
            watering_hours,
            duration_hours,
            time_step_hours
        )
    
    def predict_future(
        self,
        current_moisture: Dict[str, float],
        temperature: float,
        watering_ml: float,
        watering_hours: float,
        predict_hours: float
    ) -> Dict[str, float]:
        """
        Quick prediction of moisture values after specified hours.
        
        Args:
            current_moisture: Current moisture values
            temperature: Ambient temperature (°C)
            watering_ml: Water per irrigation (ml)
            watering_hours: Hours between watering
            predict_hours: Hours to predict ahead
        
        Returns:
            Predicted moisture values for each zone
        """
        moisture_list = [
            current_moisture.get('zone1', 50),
            current_moisture.get('zone2', 50),
            current_moisture.get('zone3', 50),
            current_moisture.get('zone4', 50),
        ]
        
        predictions = _engine.predict_moisture(
            moisture_list, temperature, watering_ml, 
            watering_hours, predict_hours
        )
        
        return {
            'zone1': predictions[0],
            'zone2': predictions[1],
            'zone3': predictions[2],
            'zone4': predictions[3],
        }
    
    def get_simulation_data_for_plot(
        self,
        simulation_result: Dict
    ) -> Dict[str, Tuple[List[float], List[float]]]:
        """
        Extract time/moisture arrays from simulation result for plotting.
        
        Args:
            simulation_result: Result from simulate_scenario()
        
        Returns:
            Dict mapping zone_id to (times, moistures) tuples
        """
        plot_data = {}
        for zone_id, zone_data in simulation_result['zones'].items():
            times = zone_data['times']
            moistures = zone_data['moistures']
            plot_data[zone_id] = (times, moistures)
        return plot_data


def get_engine_info() -> str:
    """Get information about the engine."""
    if ENGINE_AVAILABLE:
        return f"Digital Twin Engine v{_engine.get_version()} (C++)"
    else:
        return "Engine not available - needs to be built"


# Quick test when run directly
if __name__ == "__main__":
    print("Digital Twin Engine - Python Wrapper")
    print("=" * 40)
    
    if not ENGINE_AVAILABLE:
        print("\nEngine not built. Please run:")
        print(f"  cd {ENGINE_DIR}")
        print("  bash build.sh")
        sys.exit(1)
    
    # Test moisture distribution
    print("\n1. Testing Laplace Solver...")
    engine = TwinEngine(grid_size=50)
    grid = engine.compute_moisture_map(80, 60, 45, 55)
    print(f"   Grid shape: {grid.shape}")
    print(f"   Center value: {grid[25, 25]:.2f}%")
    print(f"   Corners: TL={grid[0,0]:.1f}, TR={grid[0,-1]:.1f}, "
          f"BL={grid[-1,0]:.1f}, BR={grid[-1,-1]:.1f}")
    
    # Test what-if simulation
    print("\n2. Testing What-If Simulator...")
    result = engine.simulate_scenario(
        current_moisture={'zone1': 80, 'zone2': 60, 'zone3': 45, 'zone4': 55},
        temperature=28.0,
        watering_ml=150,
        watering_hours=12,
        duration_hours=72
    )
    
    print(f"   Duration: {result['duration_hours']} hours")
    print(f"   Watering events: {result['total_watering_events']}")
    print(f"   Total water: {result['total_water_used_ml']:.0f} ml")
    
    print("\n   Zone predictions (72h):")
    for zone_id, zone_data in result['zones'].items():
        print(f"   {zone_id}: {zone_data['initial_moisture']:.1f}% -> "
              f"{zone_data['final_moisture']:.1f}% "
              f"(min: {zone_data['min_moisture']:.1f}, "
              f"max: {zone_data['max_moisture']:.1f})")
    
    # Test quick prediction
    print("\n3. Testing Quick Prediction...")
    future = engine.predict_future(
        {'zone1': 80, 'zone2': 60, 'zone3': 45, 'zone4': 55},
        temperature=28.0,
        watering_ml=150,
        watering_hours=12,
        predict_hours=24
    )
    print(f"   24h prediction: {future}")
    
    print("\n" + "=" * 40)
    print("All tests passed!")
