"""
Example: Integrating C++ Digital Twin Engine with MQTT GUI

This demonstrates how to enhance the existing mqtt_gui_controller.py
with the new C++ engine for:
1. Real-time moisture distribution visualization
2. What-if scenario simulation
"""

import sys
import os
from pathlib import Path

# Add engine to path
ENGINE_DIR = Path(__file__).parent.parent / "engine"
BUILD_DIR = ENGINE_DIR / "build"
sys.path.insert(0, str(BUILD_DIR))
sys.path.insert(0, str(ENGINE_DIR / "python"))

import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

# Import the engine
try:
    from twin_engine import TwinEngine
    ENGINE_AVAILABLE = True
except ImportError:
    ENGINE_AVAILABLE = False
    print("Warning: C++ engine not available. Build it first!")


class DigitalTwinVisualization:
    """
    Add moisture distribution heatmap and what-if simulation
    to the existing MQTT GUI.
    """
    
    def __init__(self, parent_frame, grid_size=50):
        """
        Initialize visualization components.
        
        Args:
            parent_frame: Tkinter frame to add widgets to
            grid_size: Resolution for moisture distribution
        """
        self.parent = parent_frame
        self.grid_size = grid_size
        
        if ENGINE_AVAILABLE:
            self.engine = TwinEngine(grid_size=grid_size)
        else:
            self.engine = None
        
        # Current sensor values
        self.moisture_values = [50.0, 50.0, 50.0, 50.0]
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the visualization widgets."""
        
        # Main container
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left: Heatmap
        heatmap_frame = ttk.LabelFrame(main_frame, text="Moisture Distribution (Digital Twin)")
        heatmap_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.fig_heatmap, self.ax_heatmap = plt.subplots(figsize=(5, 4))
        self.canvas_heatmap = FigureCanvasTkAgg(self.fig_heatmap, heatmap_frame)
        self.canvas_heatmap.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self._init_heatmap()
        
        # Right: What-If Simulation
        whatif_frame = ttk.LabelFrame(main_frame, text="What-If Simulation")
        whatif_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        # Simulation inputs
        input_frame = ttk.Frame(whatif_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Temperature
        ttk.Label(input_frame, text="Temperature (°C):").grid(row=0, column=0, sticky="w")
        self.temp_var = tk.DoubleVar(value=25.0)
        ttk.Entry(input_frame, textvariable=self.temp_var, width=10).grid(row=0, column=1)
        
        # Watering amount
        ttk.Label(input_frame, text="Water (ml):").grid(row=1, column=0, sticky="w")
        self.water_var = tk.IntVar(value=100)
        ttk.Entry(input_frame, textvariable=self.water_var, width=10).grid(row=1, column=1)
        
        # Frequency
        ttk.Label(input_frame, text="Frequency (hours):").grid(row=2, column=0, sticky="w")
        self.freq_var = tk.IntVar(value=12)
        ttk.Entry(input_frame, textvariable=self.freq_var, width=10).grid(row=2, column=1)
        
        # Duration
        ttk.Label(input_frame, text="Duration (hours):").grid(row=3, column=0, sticky="w")
        self.duration_var = tk.IntVar(value=72)
        ttk.Entry(input_frame, textvariable=self.duration_var, width=10).grid(row=3, column=1)
        
        # Simulate button
        ttk.Button(input_frame, text="🔮 Simulate", command=self._run_simulation).grid(
            row=4, column=0, columnspan=2, pady=10
        )
        
        # Simulation plot
        self.fig_sim, self.ax_sim = plt.subplots(figsize=(5, 3))
        self.canvas_sim = FigureCanvasTkAgg(self.fig_sim, whatif_frame)
        self.canvas_sim.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self._init_simulation_plot()
        
        # Results text
        self.results_var = tk.StringVar(value="Run simulation to see results")
        ttk.Label(whatif_frame, textvariable=self.results_var, wraplength=300).pack(pady=5)
    
    def _init_heatmap(self):
        """Initialize the moisture heatmap."""
        # Create initial uniform grid
        grid = np.ones((self.grid_size, self.grid_size)) * 50
        
        self.heatmap_img = self.ax_heatmap.imshow(
            grid, cmap='RdYlGn', vmin=0, vmax=100,
            extent=[0, 10, 10, 0], aspect='auto'
        )
        self.ax_heatmap.set_xlabel('Width (m)')
        self.ax_heatmap.set_ylabel('Length (m)')
        self.ax_heatmap.set_title('Soil Moisture (%)')
        
        # Colorbar
        cbar = self.fig_heatmap.colorbar(self.heatmap_img, ax=self.ax_heatmap)
        cbar.set_label('Moisture %')
        
        # Sensor markers
        sensor_x = [0.5, 9.5, 0.5, 9.5]
        sensor_y = [0.5, 0.5, 9.5, 9.5]
        self.sensor_markers = self.ax_heatmap.scatter(
            sensor_x, sensor_y, c='blue', s=100, marker='s', edgecolors='white'
        )
        
        self.fig_heatmap.tight_layout()
        self.canvas_heatmap.draw()
    
    def _init_simulation_plot(self):
        """Initialize the simulation time series plot."""
        self.ax_sim.set_xlabel('Time (hours)')
        self.ax_sim.set_ylabel('Moisture %')
        self.ax_sim.set_title('Predicted Moisture Evolution')
        self.ax_sim.set_xlim(0, 72)
        self.ax_sim.set_ylim(0, 100)
        self.ax_sim.grid(True, alpha=0.3)
        self.ax_sim.legend(loc='upper right')
        self.fig_sim.tight_layout()
        self.canvas_sim.draw()
    
    def update_moisture(self, m1: float, m2: float, m3: float, m4: float):
        """
        Update moisture values and refresh heatmap.
        
        Call this from the MQTT message handler.
        """
        self.moisture_values = [m1, m2, m3, m4]
        
        if self.engine:
            # Compute moisture distribution using C++ engine
            grid = self.engine.compute_moisture_map(m1, m2, m3, m4)
            self.heatmap_img.set_data(grid)
            self.canvas_heatmap.draw()
    
    def _run_simulation(self):
        """Run the what-if simulation."""
        if not self.engine:
            self.results_var.set("Engine not available!")
            return
        
        # Get parameters
        temperature = self.temp_var.get()
        water_ml = self.water_var.get()
        frequency = self.freq_var.get()
        duration = self.duration_var.get()
        
        # Run simulation
        result = self.engine.simulate_scenario(
            current_moisture={
                'zone1': self.moisture_values[0],
                'zone2': self.moisture_values[1],
                'zone3': self.moisture_values[2],
                'zone4': self.moisture_values[3],
            },
            temperature=temperature,
            watering_ml=water_ml,
            watering_hours=frequency,
            duration_hours=duration
        )
        
        # Update plot
        self.ax_sim.clear()
        self.ax_sim.set_xlabel('Time (hours)')
        self.ax_sim.set_ylabel('Moisture %')
        self.ax_sim.set_title(f'Predicted Moisture (T={temperature}°C)')
        
        colors = ['#2ecc71', '#3498db', '#e74c3c', '#f39c12']
        
        for i, (zone_id, zone_data) in enumerate(result['zones'].items()):
            times = zone_data['times']
            moistures = zone_data['moistures']
            self.ax_sim.plot(times, moistures, label=zone_id, color=colors[i], linewidth=2)
        
        self.ax_sim.axhline(y=30, color='red', linestyle='--', alpha=0.5, label='Critical Low')
        self.ax_sim.axhline(y=70, color='blue', linestyle='--', alpha=0.5, label='Optimal')
        self.ax_sim.set_xlim(0, duration)
        self.ax_sim.set_ylim(0, 100)
        self.ax_sim.grid(True, alpha=0.3)
        self.ax_sim.legend(loc='upper right', fontsize=8)
        self.fig_sim.tight_layout()
        self.canvas_sim.draw()
        
        # Update results text
        summary = f"Total water: {result['total_water_used_ml']:.0f}ml\n"
        for zone_id, zone_data in result['zones'].items():
            summary += f"{zone_id}: {zone_data['initial_moisture']:.0f}% → {zone_data['final_moisture']:.0f}%\n"
        self.results_var.set(summary)


# =====================================================
# Integration Example with mqtt_gui_controller.py
# =====================================================

def integrate_with_gui(original_gui):
    """
    Extend the existing SmartIrrigationSystemGUI with Digital Twin visualization.
    
    Usage in mqtt_gui_controller.py:
    --------------------------------
    
    1. Import at the top:
       from examples.gui_integration import DigitalTwinVisualization
    
    2. In SmartIrrigationSystemGUI.__init__, after create_widgets():
       # Add Digital Twin visualization
       twin_frame = ttk.Frame(self.root)
       twin_frame.grid(row=10, column=0, columnspan=4)
       self.twin_viz = DigitalTwinVisualization(twin_frame)
    
    3. In on_message(), after updating moisture values:
       if hasattr(self, 'twin_viz'):
           m1 = self.latest_data.get('moisture1', 50)
           m2 = self.latest_data.get('moisture2', 50)
           m3 = self.latest_data.get('moisture3', 50)
           m4 = self.latest_data.get('moisture4', 50)
           self.twin_viz.update_moisture(m1, m2, m3, m4)
    """
    pass


# =====================================================
# Standalone Demo
# =====================================================

def run_demo():
    """Run standalone demo of the Digital Twin visualization."""
    root = tk.Tk()
    root.title("Digital Twin Engine Demo")
    root.geometry("1200x600")
    
    # Create visualization
    viz = DigitalTwinVisualization(root, grid_size=50)
    
    # Simulate some sensor updates
    def update_sensors():
        import random
        m1 = 70 + random.uniform(-5, 5)
        m2 = 55 + random.uniform(-5, 5)
        m3 = 40 + random.uniform(-5, 5)
        m4 = 60 + random.uniform(-5, 5)
        viz.update_moisture(m1, m2, m3, m4)
        root.after(2000, update_sensors)
    
    # Start updates
    root.after(1000, update_sensors)
    
    root.mainloop()


if __name__ == "__main__":
    if not ENGINE_AVAILABLE:
        print("Please build the engine first:")
        print(f"  cd {ENGINE_DIR}")
        print("  bash build.sh")
        sys.exit(1)
    
    # Install matplotlib if needed
    try:
        import matplotlib
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "matplotlib"])
    
    run_demo()
