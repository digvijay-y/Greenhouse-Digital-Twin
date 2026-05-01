"""
Enhanced MQTT GUI Controller with Digital Twin Engine Integration

This version adds:
1. Real-time moisture distribution heatmap (via C++ Laplace solver)
2. What-If simulation panel with visualization
3. Comparison of live vs predicted data

Original: mqtt_gui_controller.py
Enhanced: mqtt_gui_controller_v2.py
"""

import paho.mqtt.client as mqtt
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import json
import sqlite3
import sys
from pathlib import Path

# Project root and engine paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENGINE_DIR = PROJECT_ROOT / "backend" / "src" / "digital_twin" / "engine"
BUILD_DIR = ENGINE_DIR / "build"
sys.path.insert(0, str(BUILD_DIR))
sys.path.insert(0, str(ENGINE_DIR / "python"))

# Check for matplotlib
try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available. Install with: pip install matplotlib numpy")

# Check for C++ engine
try:
    import twin_engine_py as te
    from twin_engine import TwinEngine
    ENGINE_AVAILABLE = True
    print(f"Digital Twin Engine v{te.get_version()} loaded")
except ImportError:
    ENGINE_AVAILABLE = False
    print("Warning: C++ engine not built. Run: cd ../engine && bash build.sh")

DB_FILE = "greenhouse.db"


class EnhancedIrrigationGUI:
    """
    Enhanced Smart Irrigation System GUI with Digital Twin capabilities.
    """
    
    def __init__(self, root, mqtt_client):
        self.root = root
        self.root.title("Digital Twin Dashboard - Enhanced")
        self.root.geometry("1400x800")
        
        # Initialize engine
        if ENGINE_AVAILABLE:
            self.engine = TwinEngine(grid_size=50)
        else:
            self.engine = None
        
        # --- Data Storage ---
        self.tk_vars = {
            "moisture1": tk.DoubleVar(value=50.0),
            "moisture2": tk.DoubleVar(value=50.0),
            "moisture3": tk.DoubleVar(value=50.0),
            "moisture4": tk.DoubleVar(value=50.0),
            "npk": tk.StringVar(value="N:-, P:-, K:-"),
            "temperature": tk.DoubleVar(value=25.0),
            "humidity": tk.DoubleVar(value=60.0),
            "pressure": tk.DoubleVar(value=1013.0),
        }
        self.latest_data = {
            'moisture1': 50.0, 'moisture2': 50.0, 
            'moisture3': 50.0, 'moisture4': 50.0,
            'temperature': 25.0, 'humidity': 60.0, 'pressure': 1013.0,
            'n': 0, 'p': 0, 'k': 0
        }
        
        # Simulation parameters
        self.sim_temp = tk.DoubleVar(value=25.0)
        self.sim_water = tk.IntVar(value=100)
        self.sim_freq = tk.IntVar(value=12)
        self.sim_duration = tk.IntVar(value=72)
        
        # --- Database Setup ---
        self.db_conn = self.setup_database()
        
        # --- Create GUI ---
        self.create_main_layout()
        
        # --- MQTT Setup ---
        broker_address = '127.0.0.1'
        print(f"Connecting to MQTT broker at {broker_address}")
        self.mqtt_client = mqtt_client
        self.mqtt_client.on_message = self.on_message
        try:
            self.mqtt_client.connect(broker_address, 1883)
            self.mqtt_client.subscribe([
                ("pico1/moisture1", 0), ("pico1/moisture2", 0),
                ("pico2/moisture1", 0), ("pico2/moisture2", 0),
                ("pico1/bme280", 0), ("esp32/npk", 0)
            ])
            self.mqtt_client.loop_start()
            self.mqtt_connected = True
        except Exception as e:
            print(f"MQTT connection failed: {e}")
            self.mqtt_connected = False
        
        # Initial plot update
        self.update_heatmap()
        self.update_clock()

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

    def create_main_layout(self):
        """Create the main GUI layout with all panels."""
        
        # Main container with 3 columns
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=2)
        self.root.columnconfigure(2, weight=2)
        self.root.rowconfigure(1, weight=1)
        
        # Header
        header = ttk.Frame(self.root)
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=5)
        
        ttk.Label(header, text="Greenhouse Digital Twin Dashboard", 
                  font=('Arial', 18, 'bold')).pack(side=tk.LEFT)
        
        self.clock_label = ttk.Label(header, text="", font=('Arial', 12))
        self.clock_label.pack(side=tk.RIGHT, padx=20)
        
        self.status_label = ttk.Label(header, text="", font=('Arial', 10))
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # Left Panel: Sensor Values
        self.create_sensor_panel()
        
        # Center Panel: Moisture Heatmap
        self.create_heatmap_panel()
        
        # Right Panel: What-If Simulation
        self.create_whatif_panel()

    def create_sensor_panel(self):
        """Create the sensor values panel."""
        panel = ttk.LabelFrame(self.root, text="Live Sensor Data", padding=10)
        panel.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Moisture sensors
        ttk.Label(panel, text="Soil Moisture", font=('Arial', 12, 'bold')).grid(
            row=0, column=0, columnspan=2, pady=(0, 10))
        
        for i in range(4):
            ttk.Label(panel, text=f"Zone {i+1}:").grid(row=i+1, column=0, sticky="w", pady=3)
            
            # Progress bar style indicator
            frame = ttk.Frame(panel)
            frame.grid(row=i+1, column=1, sticky="ew", padx=5)
            
            entry = ttk.Entry(frame, textvariable=self.tk_vars[f"moisture{i+1}"], 
                            width=8, state="readonly")
            entry.pack(side=tk.LEFT)
            ttk.Label(frame, text="%").pack(side=tk.LEFT)
        
        # Separator
        ttk.Separator(panel, orient='horizontal').grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=10)
        
        # BME280 data
        ttk.Label(panel, text="Environment", font=('Arial', 12, 'bold')).grid(
            row=7, column=0, columnspan=2, pady=(0, 10))
        
        env_labels = [("Temp:", "temperature", "°C"),
                  ("Humidity:", "humidity", "%"),
                  ("Pressure:", "pressure", "hPa")]
        
        for i, (label, var, unit) in enumerate(env_labels):
            ttk.Label(panel, text=label).grid(row=8+i, column=0, sticky="w", pady=3)
            frame = ttk.Frame(panel)
            frame.grid(row=8+i, column=1, sticky="ew", padx=5)
            ttk.Entry(frame, textvariable=self.tk_vars[var], width=8, state="readonly").pack(side=tk.LEFT)
            ttk.Label(frame, text=unit).pack(side=tk.LEFT)
        
        # NPK
        ttk.Separator(panel, orient='horizontal').grid(
            row=12, column=0, columnspan=2, sticky="ew", pady=10)
        
        ttk.Label(panel, text="NPK:").grid(row=13, column=0, sticky="w")
        ttk.Entry(panel, textvariable=self.tk_vars["npk"], width=20, state="readonly").grid(
            row=13, column=1, sticky="w", padx=5)
        
        # Last updated
        self.last_updated_label = ttk.Label(panel, text="Waiting for data...", font=('Arial', 9))
        self.last_updated_label.grid(row=14, column=0, columnspan=2, pady=(15, 0))

    def create_heatmap_panel(self):
        """Create the 3D moisture distribution surface panel (like MATLAB)."""
        panel = ttk.LabelFrame(self.root, text="Live Moisture Distribution (Digital Twin)", padding=10)
        panel.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        
        if MATPLOTLIB_AVAILABLE:
            from mpl_toolkits.mplot3d import Axes3D
            
            self.fig_heatmap = Figure(figsize=(6, 5), dpi=100)
            self.ax_heatmap = self.fig_heatmap.add_subplot(111, projection='3d')
            
            # Create mesh grid (10m x 10m greenhouse)
            self.grid_size = 50
            x = np.linspace(0, 10, self.grid_size)
            y = np.linspace(0, 10, self.grid_size)
            self.X_mesh, self.Y_mesh = np.meshgrid(x, y)
            
            # Initial surface
            initial_grid = np.ones((self.grid_size, self.grid_size)) * 50
            self.surface = self.ax_heatmap.plot_surface(
                self.X_mesh, self.Y_mesh, initial_grid,
                cmap='hot', vmin=0, vmax=100,
                edgecolor='none', alpha=0.9
            )
            
            # Styling (matching MATLAB)
            self.ax_heatmap.set_xlabel('Greenhouse Width (m)', fontsize=10)
            self.ax_heatmap.set_ylabel('Greenhouse Length (m)', fontsize=10)
            self.ax_heatmap.set_zlabel('Moisture Content (%)', fontsize=10)
            self.ax_heatmap.set_title('Real-Time Volumetric Soil Moisture', fontsize=11)
            self.ax_heatmap.set_zlim(0, 100)
            self.ax_heatmap.view_init(elev=30, azim=45)  # Same view as MATLAB
            
            # Colorbar
            self.cbar = self.fig_heatmap.colorbar(self.surface, ax=self.ax_heatmap, 
                                                   shrink=0.6, pad=0.1)
            self.cbar.set_label('Soil Moisture (%)')
            
            self.fig_heatmap.tight_layout()
            
            self.canvas_heatmap = FigureCanvasTkAgg(self.fig_heatmap, panel)
            self.canvas_heatmap.draw()
            self.canvas_heatmap.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            ttk.Label(panel, text="Install matplotlib for 3D visualization",
                     font=('Arial', 12)).pack(expand=True)

    def create_whatif_panel(self):
        """Create the What-If simulation panel."""
        panel = ttk.LabelFrame(self.root, text="What-If Simulation", padding=10)
        panel.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)
        
        # Description
        ttk.Label(panel, text="Configure irrigation scenario:",
                  font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # Input controls
        input_frame = ttk.Frame(panel)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Row 1: Temperature and Water
        ttk.Label(input_frame, text="Temp (°C):").grid(row=0, column=0, sticky="w", padx=2, pady=3)
        ttk.Entry(input_frame, textvariable=self.sim_temp, width=8).grid(row=0, column=1, padx=2)
        
        ttk.Label(input_frame, text="Water (ml):").grid(row=1, column=0, sticky="w", padx=2, pady=3)
        ttk.Entry(input_frame, textvariable=self.sim_water, width=8).grid(row=1, column=1, padx=2)
        
        # Row 2: Frequency and Duration
        ttk.Label(input_frame, text="Every (h):").grid(row=2, column=0, sticky="w", padx=2, pady=3)
        ttk.Entry(input_frame, textvariable=self.sim_freq, width=8).grid(row=2, column=1, padx=2)
        
        ttk.Label(input_frame, text="Duration (h):").grid(row=3, column=0, sticky="w", padx=2, pady=3)
        ttk.Entry(input_frame, textvariable=self.sim_duration, width=8).grid(row=3, column=1, padx=2)
        
        # Simulate button - opens popup
        sim_btn = ttk.Button(panel, text="Simulate (opens graph)", 
                             command=self.run_simulation)
        sim_btn.pack(fill=tk.X, pady=15)
        
        # Results summary (text only, graph in popup)
        ttk.Separator(panel, orient='horizontal').pack(fill=tk.X, pady=10)
        
        self.sim_results = tk.StringVar(value="Click 'Simulate' to see prediction graph")
        results_label = ttk.Label(panel, textvariable=self.sim_results, 
                                  wraplength=300, justify=tk.LEFT, font=('Arial', 9))
        results_label.pack(fill=tk.X, pady=5)
        
        # Quick predictions
        pred_frame = ttk.LabelFrame(panel, text="Quick Predictions (auto-updated)", padding=8)
        pred_frame.pack(fill=tk.X, pady=10)
        
        self.pred_24h = tk.StringVar(value="24h: Waiting for data...")
        self.pred_48h = tk.StringVar(value="48h: Waiting for data...")
        
        ttk.Label(pred_frame, textvariable=self.pred_24h, font=('Arial', 9)).pack(anchor='w', pady=2)
        ttk.Label(pred_frame, textvariable=self.pred_48h, font=('Arial', 9)).pack(anchor='w', pady=2)
        
        # Current values display
        curr_frame = ttk.LabelFrame(panel, text="Current Readings", padding=8)
        curr_frame.pack(fill=tk.X, pady=10)
        
        self.current_avg = tk.StringVar(value="Avg: -")
        self.current_status = tk.StringVar(value="Status: -")
        
        ttk.Label(curr_frame, textvariable=self.current_avg, font=('Arial', 9)).pack(anchor='w', pady=2)
        ttk.Label(curr_frame, textvariable=self.current_status, font=('Arial', 9)).pack(anchor='w', pady=2)

    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            print(f"Received: {topic} = {payload}")
            
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
                self.latest_data.update(npk_data)
                self.tk_vars["npk"].set(f"N:{npk_data.get('n')}, P:{npk_data.get('p')}, K:{npk_data.get('k')}")
            elif topic == 'pico1/bme280':
                temp, hum, pres = payload.split(',')
                self.latest_data['temperature'] = float(temp)
                self.latest_data['humidity'] = float(hum)
                self.latest_data['pressure'] = float(pres)
                self.save_data_to_db()
            
            # Update displays
            self.update_gui_displays()
            self.update_heatmap()
            self.update_quick_predictions()
            self.update_last_updated()
            
        except Exception as e:
            print(f"Error processing message: {e}")

    def update_gui_displays(self):
        """Update GUI variables from latest data."""
        for key, var in self.tk_vars.items():
            if key in self.latest_data and key != "npk":
                var.set(round(self.latest_data[key], 1))

    def update_heatmap(self):
        """Update the 3D moisture distribution surface using C++ engine."""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        m1 = self.latest_data.get('moisture1', 50)
        m2 = self.latest_data.get('moisture2', 50)
        m3 = self.latest_data.get('moisture3', 50)
        m4 = self.latest_data.get('moisture4', 50)
        
        if self.engine:
            # Use C++ engine for high-performance Laplace solution
            grid = self.engine.compute_moisture_map(m1, m2, m3, m4)
        else:
            # Fallback: simple bilinear interpolation
            grid = self._simple_interpolation(m1, m2, m3, m4)
        
        # Clear and redraw surface (required for 3D plots)
        self.ax_heatmap.clear()
        
        self.surface = self.ax_heatmap.plot_surface(
            self.X_mesh, self.Y_mesh, grid,
            cmap='hot', vmin=0, vmax=100,
            edgecolor='none', alpha=0.9
        )
        
        # Re-apply styling
        self.ax_heatmap.set_xlabel('Width (m)', fontsize=9)
        self.ax_heatmap.set_ylabel('Length (m)', fontsize=9)
        self.ax_heatmap.set_zlabel('Moisture %', fontsize=9)
        self.ax_heatmap.set_title(
            f'LIVE: Z1={m1:.0f}% Z2={m2:.0f}% Z3={m3:.0f}% Z4={m4:.0f}%',
            fontsize=10
        )
        self.ax_heatmap.set_zlim(0, 100)
        self.ax_heatmap.view_init(elev=30, azim=45)
        
        self.canvas_heatmap.draw()

    def _simple_interpolation(self, m1, m2, m3, m4):
        """Fallback bilinear interpolation if engine not available."""
        size = 50
        grid = np.zeros((size, size))
        for i in range(size):
            for j in range(size):
                x = j / (size - 1)
                y = i / (size - 1)
                top = m1 * (1 - x) + m2 * x
                bottom = m3 * (1 - x) + m4 * x
                grid[i, j] = top * (1 - y) + bottom * y
        return grid

    def run_simulation(self):
        """Run the What-If simulation and show PREDICTED 3D surface in popup."""
        if not self.engine:
            self.sim_results.set("Engine not available. Build it first.")
            return
        
        if not MATPLOTLIB_AVAILABLE:
            self.sim_results.set("matplotlib not available for plotting")
            return
        
        from mpl_toolkits.mplot3d import Axes3D
        
        # Get parameters
        temperature = self.sim_temp.get()
        water_ml = self.sim_water.get()
        frequency = self.sim_freq.get()
        duration = self.sim_duration.get()
        
        # Current moisture values
        current = {
            'zone1': self.latest_data.get('moisture1', 50),
            'zone2': self.latest_data.get('moisture2', 50),
            'zone3': self.latest_data.get('moisture3', 50),
            'zone4': self.latest_data.get('moisture4', 50),
        }
        
        # Run simulation
        result = self.engine.simulate_scenario(
            current_moisture=current,
            temperature=temperature,
            watering_ml=water_ml,
            watering_hours=frequency,
            duration_hours=duration
        )
        
        # Get final predicted moisture values
        pred_m1 = result['zones']['zone1']['final_moisture']
        pred_m2 = result['zones']['zone2']['final_moisture']
        pred_m3 = result['zones']['zone3']['final_moisture']
        pred_m4 = result['zones']['zone4']['final_moisture']
        
        # Compute predicted distribution using Laplace solver
        predicted_grid = self.engine.compute_moisture_map(pred_m1, pred_m2, pred_m3, pred_m4)
        
        # Create popup window - PREDICTED 3D Surface (Digital Twin)
        popup = tk.Toplevel(self.root)
        popup.title(f"Predicted State: After {duration}h @ {temperature}°C")
        popup.geometry("800x650")
        popup.transient(self.root)
        
        # Create 3D figure for predicted state
        fig_popup = Figure(figsize=(8, 6), dpi=100)
        ax_popup = fig_popup.add_subplot(111, projection='3d')
        
        # Plot predicted 3D surface (same style as live view)
        x = np.linspace(0, 10, self.grid_size)
        y = np.linspace(0, 10, self.grid_size)
        X, Y = np.meshgrid(x, y)
        
        surf = ax_popup.plot_surface(
            X, Y, predicted_grid,
            cmap='hot', vmin=0, vmax=100,
            edgecolor='none', alpha=0.9
        )
        
        ax_popup.set_xlabel('Greenhouse Width (m)', fontsize=11)
        ax_popup.set_ylabel('Greenhouse Length (m)', fontsize=11)
        ax_popup.set_zlabel('Moisture Content (%)', fontsize=11)
        ax_popup.set_title(
            f'PREDICTED after {duration}h: Z1={pred_m1:.0f}% Z2={pred_m2:.0f}% Z3={pred_m3:.0f}% Z4={pred_m4:.0f}%',
            fontsize=11
        )
        ax_popup.set_zlim(0, 100)
        ax_popup.view_init(elev=30, azim=45)  # Same view as live
        
        # Colorbar
        cbar = fig_popup.colorbar(surf, ax=ax_popup, shrink=0.6, pad=0.1)
        cbar.set_label('Soil Moisture (%)')
        
        fig_popup.tight_layout()
        
        # Embed in popup
        canvas_popup = FigureCanvasTkAgg(fig_popup, popup)
        canvas_popup.draw()
        canvas_popup.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Summary frame at bottom
        summary_frame = ttk.Frame(popup)
        summary_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Show change summary
        summary_text = f"Scenario: {water_ml}ml every {frequency}h for {duration}h at {temperature}°C\n"
        summary_text += f"Watering events: {result['total_watering_events']}\n\n"
        summary_text += "Zone Changes:\n"
        for zone_id, zone_data in result['zones'].items():
            change = zone_data['final_moisture'] - zone_data['initial_moisture']
            arrow = "↑" if change > 0 else "↓"
            summary_text += f"  {zone_id}: {zone_data['initial_moisture']:.1f}% → {zone_data['final_moisture']:.1f}% ({arrow}{abs(change):.1f}%)\n"
        
        ttk.Label(summary_frame, text=summary_text, font=('Courier', 9), justify=tk.LEFT).pack(side=tk.LEFT)
        
        # Close button
        ttk.Button(popup, text="Close", command=popup.destroy).pack(pady=5)
        
        # Update main panel summary
        summary = f"Simulated ({duration}h, {result['total_watering_events']} waterings)\n"
        for zone_id, zone_data in result['zones'].items():
            change = zone_data['final_moisture'] - zone_data['initial_moisture']
            arrow = "↑" if change > 0 else "↓"
            summary += f"{zone_id}: {zone_data['initial_moisture']:.0f}%→{zone_data['final_moisture']:.0f}% {arrow}\n"
        
        self.sim_results.set(summary)

    def update_quick_predictions(self):
        """Update quick 24h and 48h predictions."""
        if not self.engine:
            return
        
        current = {
            'zone1': self.latest_data.get('moisture1', 50),
            'zone2': self.latest_data.get('moisture2', 50),
            'zone3': self.latest_data.get('moisture3', 50),
            'zone4': self.latest_data.get('moisture4', 50),
        }
        
        temp = self.latest_data.get('temperature', 25)
        
        # 24h prediction
        pred_24 = self.engine.predict_future(current, temp, 100, 12, 24)
        avg_24 = sum(pred_24.values()) / 4
        
        # 48h prediction
        pred_48 = self.engine.predict_future(current, temp, 100, 12, 48)
        avg_48 = sum(pred_48.values()) / 4
        
        self.pred_24h.set(f"24h avg: {avg_24:.1f}% (T={temp:.1f}°C, 100ml/12h)")
        self.pred_48h.set(f"48h avg: {avg_48:.1f}%")
        
        # Update current readings
        avg_current = sum([self.latest_data.get(f'moisture{i+1}', 50) for i in range(4)]) / 4
        self.current_avg.set(f"Avg moisture: {avg_current:.1f}%")
        
        if avg_current < 30:
            self.current_status.set("Status: Too Dry - Irrigate")
        elif avg_current > 70:
            self.current_status.set("Status: Too Wet - Stop watering")
        else:
            self.current_status.set("Status: Optimal Range")

    def save_data_to_db(self):
        """Save sensor data to database."""
        try:
            cursor = self.db_conn.cursor()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
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
            
            cursor.execute('''
                INSERT INTO sensor_data (
                    timestamp, temperature, humidity, pressure,
                    moisture1, moisture2, moisture3, moisture4,
                    n_value, p_value, k_value
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', data_to_insert)
            
            self.db_conn.commit()
            print(f"Saved to DB at {timestamp}")
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")

    def update_clock(self):
        """Update the clock display."""
        now = datetime.now()
        self.clock_label.config(text=now.strftime("%d %b %Y | %I:%M:%S %p"))
        
        # Update status
        status = "MQTT: Connected" if self.mqtt_connected else "MQTT: Disconnected"
        status += " | Engine: Available" if ENGINE_AVAILABLE else " | Engine: Unavailable"
        self.status_label.config(text=status)
        
        self.root.after(1000, self.update_clock)

    def update_last_updated(self):
        """Update the last updated label."""
        formatted_now = datetime.now().strftime("%I:%M:%S %p")
        self.last_updated_label.config(text=f"Last update: {formatted_now}")


def main():
    """Main entry point."""
    root = tk.Tk()
    
    # Style configuration
    style = ttk.Style()
    style.theme_use('clam')
    
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    app = EnhancedIrrigationGUI(root, mqtt_client)
    
    def on_closing():
        print("Shutting down...")
        if app.mqtt_connected:
            app.mqtt_client.loop_stop()
            app.mqtt_client.disconnect()
        app.db_conn.close()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
