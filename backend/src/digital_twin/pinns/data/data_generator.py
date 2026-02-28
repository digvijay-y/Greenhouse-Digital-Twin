"""
Data Generation for PINN Training

Generates synthetic training data using:
1. C++ Laplace solver for steady-state moisture distributions
2. What-If simulator for time-series data
3. Optional: Load real data from Kaggle datasets

The generated data includes:
- Sensor observations (x, y, t, T, u)
- Collocation points for PDE residual
- Boundary conditions
- Initial conditions
"""

import numpy as np
from typing import Tuple, Optional, Dict
from pathlib import Path
import sys

# Add engine path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
ENGINE_DIR = PROJECT_ROOT / "src" / "digital_twin" / "engine"
BUILD_DIR = ENGINE_DIR / "build"
sys.path.insert(0, str(BUILD_DIR))
sys.path.insert(0, str(ENGINE_DIR / "python"))


class SyntheticDataGenerator:
    """
    Generate synthetic soil moisture data using the C++ Digital Twin engine.
    """
    
    def __init__(self, grid_size: int = 50, use_engine: bool = True):
        """
        Initialize the generator.
        
        Args:
            grid_size: Size of the spatial grid
            use_engine: Whether to use C++ engine (falls back to simple model)
        """
        self.grid_size = grid_size
        self.use_engine = use_engine
        
        if use_engine:
            try:
                from twin_engine import TwinEngine
                self.engine = TwinEngine(grid_size=grid_size)
                print("✅ Using C++ engine for data generation")
            except ImportError:
                print("⚠️ C++ engine not available, using fallback model")
                self.engine = None
                self.use_engine = False
        else:
            self.engine = None
    
    def generate_steady_state_samples(
        self, 
        n_samples: int = 100,
        moisture_range: Tuple[float, float] = (20.0, 80.0),
        temp_range: Tuple[float, float] = (15.0, 35.0)
    ) -> Dict[str, np.ndarray]:
        """
        Generate steady-state moisture distribution samples.
        
        For each sample:
        - Random corner moisture values (sensor readings)
        - Laplace-solved interior distribution
        - Random temperature
        
        Args:
            n_samples: Number of samples to generate
            moisture_range: Range for random moisture values
            temp_range: Range for random temperature
            
        Returns:
            Dictionary with 'x', 'y', 't', 'T', 'u' arrays
        """
        x_list, y_list, t_list, T_list, u_list = [], [], [], [], []
        
        # Create normalized grid
        xx = np.linspace(0, 1, self.grid_size)
        yy = np.linspace(0, 1, self.grid_size)
        X, Y = np.meshgrid(xx, yy)
        
        for i in range(n_samples):
            # Random corner moisture values
            m1 = np.random.uniform(*moisture_range)
            m2 = np.random.uniform(*moisture_range)
            m3 = np.random.uniform(*moisture_range)
            m4 = np.random.uniform(*moisture_range)
            
            # Random temperature (normalized to [0, 1])
            temp = np.random.uniform(*temp_range)
            temp_norm = (temp - temp_range[0]) / (temp_range[1] - temp_range[0])
            
            # Compute moisture distribution
            if self.use_engine and self.engine:
                grid = self.engine.compute_moisture_map(m1, m2, m3, m4)
            else:
                grid = self._bilinear_interpolation(m1, m2, m3, m4)
            
            # Flatten and store
            x_list.append(X.flatten())
            y_list.append(Y.flatten())
            t_list.append(np.zeros(self.grid_size**2))  # t=0 for steady state
            T_list.append(np.full(self.grid_size**2, temp_norm))
            u_list.append(grid.flatten())
            
            if (i + 1) % 20 == 0:
                print(f"  Generated {i+1}/{n_samples} steady-state samples")
        
        return {
            'x': np.concatenate(x_list).astype(np.float32),
            'y': np.concatenate(y_list).astype(np.float32),
            't': np.concatenate(t_list).astype(np.float32),
            'T': np.concatenate(T_list).astype(np.float32),
            'u': np.concatenate(u_list).astype(np.float32)
        }
    
    def generate_time_series_samples(
        self,
        n_trajectories: int = 20,
        duration_hours: int = 48,
        time_steps: int = 24,
        moisture_range: Tuple[float, float] = (30.0, 70.0),
        temp_range: Tuple[float, float] = (20.0, 30.0)
    ) -> Dict[str, np.ndarray]:
        """
        Generate time-series moisture data using What-If simulation.
        
        For each trajectory:
        - Random initial moisture at corners
        - Simulate evolution over time
        - Sample at multiple spatial points
        
        Returns:
            Dictionary with 'x', 'y', 't', 'T', 'u' arrays
        """
        x_list, y_list, t_list, T_list, u_list = [], [], [], [], []
        
        # Time points (normalized to [0, 1])
        times = np.linspace(0, 1, time_steps)
        
        # Spatial sample points (subset for efficiency)
        n_spatial = 25  # 5x5 grid of sample points
        xx = np.linspace(0, 1, int(np.sqrt(n_spatial)))
        yy = np.linspace(0, 1, int(np.sqrt(n_spatial)))
        X_sample, Y_sample = np.meshgrid(xx, yy)
        
        for traj in range(n_trajectories):
            # Initial moisture values
            initial_moisture = {
                'zone1': np.random.uniform(*moisture_range),
                'zone2': np.random.uniform(*moisture_range),
                'zone3': np.random.uniform(*moisture_range),
                'zone4': np.random.uniform(*moisture_range)
            }
            
            # Temperature
            temp = np.random.uniform(*temp_range)
            temp_norm = (temp - 15) / 25  # Normalize assuming [15, 40] range
            
            # Watering parameters
            water_ml = np.random.choice([0, 50, 100, 150])
            water_freq = np.random.choice([6, 12, 24])
            
            if self.use_engine and self.engine:
                # Use engine simulation
                result = self.engine.simulate_scenario(
                    current_moisture=initial_moisture,
                    temperature=temp,
                    watering_ml=water_ml,
                    watering_hours=water_freq,
                    duration_hours=duration_hours
                )
                
                # Extract data at each time step
                for t_idx, t_norm in enumerate(times):
                    t_actual = int(t_norm * duration_hours)
                    
                    # Get moisture at this time for each zone
                    moistures = []
                    for zone_id in ['zone1', 'zone2', 'zone3', 'zone4']:
                        zone_times = result['zones'][zone_id]['times']
                        zone_moist = result['zones'][zone_id]['moistures']
                        # Find closest time
                        idx = np.argmin(np.abs(np.array(zone_times) - t_actual))
                        moistures.append(zone_moist[idx])
                    
                    # Interpolate to sample grid
                    grid = self._bilinear_interpolation(*moistures)
                    
                    # Sample at sparse points
                    for i, (x, y) in enumerate(zip(X_sample.flatten(), Y_sample.flatten())):
                        xi = int(x * (self.grid_size - 1))
                        yi = int(y * (self.grid_size - 1))
                        
                        x_list.append(x)
                        y_list.append(y)
                        t_list.append(t_norm)
                        T_list.append(temp_norm)
                        u_list.append(grid[yi, xi])
            else:
                # Simple decay model
                for t_idx, t_norm in enumerate(times):
                    decay = np.exp(-0.02 * t_norm * duration_hours)
                    moistures = [m * decay for m in initial_moisture.values()]
                    grid = self._bilinear_interpolation(*moistures)
                    
                    for i, (x, y) in enumerate(zip(X_sample.flatten(), Y_sample.flatten())):
                        xi = int(x * (self.grid_size - 1))
                        yi = int(y * (self.grid_size - 1))
                        
                        x_list.append(x)
                        y_list.append(y)
                        t_list.append(t_norm)
                        T_list.append(temp_norm)
                        u_list.append(grid[yi, xi])
            
            if (traj + 1) % 5 == 0:
                print(f"  Generated {traj+1}/{n_trajectories} time-series trajectories")
        
        return {
            'x': np.array(x_list, dtype=np.float32),
            'y': np.array(y_list, dtype=np.float32),
            't': np.array(t_list, dtype=np.float32),
            'T': np.array(T_list, dtype=np.float32),
            'u': np.array(u_list, dtype=np.float32)
        }
    
    def generate_collocation_points(
        self,
        n_points: int = 5000,
        t_range: Tuple[float, float] = (0.0, 1.0),
        T_range: Tuple[float, float] = (0.0, 1.0)
    ) -> Dict[str, np.ndarray]:
        """
        Generate random collocation points for PDE residual.
        
        These points don't need labels - we just enforce PDE = 0.
        
        Returns:
            Dictionary with 'x', 'y', 't', 'T' arrays
        """
        return {
            'x': np.random.uniform(0, 1, n_points).astype(np.float32),
            'y': np.random.uniform(0, 1, n_points).astype(np.float32),
            't': np.random.uniform(*t_range, n_points).astype(np.float32),
            'T': np.random.uniform(*T_range, n_points).astype(np.float32)
        }
    
    def generate_boundary_conditions(
        self,
        n_points_per_edge: int = 50,
        n_time_samples: int = 10
    ) -> Dict[str, np.ndarray]:
        """
        Generate boundary condition points at the 4 corners (sensor locations).
        
        Returns:
            Dictionary with 'x', 'y', 't', 'T', 'u' arrays
        """
        x_list, y_list, t_list, T_list, u_list = [], [], [], [], []
        
        # Corner positions
        corners = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)]
        
        for t_norm in np.linspace(0, 1, n_time_samples):
            temp_norm = np.random.uniform(0, 1)
            
            for i, (cx, cy) in enumerate(corners):
                # Sample points near each corner
                for _ in range(n_points_per_edge // 4):
                    x = cx + np.random.normal(0, 0.05)
                    y = cy + np.random.normal(0, 0.05)
                    x = np.clip(x, 0, 1)
                    y = np.clip(y, 0, 1)
                    
                    # Moisture value (random for training)
                    u = np.random.uniform(30, 70)
                    
                    x_list.append(x)
                    y_list.append(y)
                    t_list.append(t_norm)
                    T_list.append(temp_norm)
                    u_list.append(u)
        
        return {
            'x': np.array(x_list, dtype=np.float32),
            'y': np.array(y_list, dtype=np.float32),
            't': np.array(t_list, dtype=np.float32),
            'T': np.array(T_list, dtype=np.float32),
            'u': np.array(u_list, dtype=np.float32)
        }
    
    def _bilinear_interpolation(
        self, m1: float, m2: float, m3: float, m4: float
    ) -> np.ndarray:
        """
        Simple bilinear interpolation for fallback.
        
        m1 (top-left), m2 (top-right), m3 (bottom-left), m4 (bottom-right)
        """
        grid = np.zeros((self.grid_size, self.grid_size))
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                x = j / (self.grid_size - 1)
                y = i / (self.grid_size - 1)
                
                top = m1 * (1 - x) + m2 * x
                bottom = m3 * (1 - x) + m4 * x
                grid[i, j] = top * (1 - y) + bottom * y
        
        return grid


def generate_full_dataset(
    output_dir: Optional[Path] = None,
    n_steady_samples: int = 100,
    n_trajectories: int = 20
) -> Dict[str, Dict[str, np.ndarray]]:
    """
    Generate a complete dataset for PINN training.
    
    Returns:
        Dictionary with 'train', 'collocation', 'boundary' data
    """
    print("=" * 60)
    print("Generating PINN Training Dataset")
    print("=" * 60)
    
    generator = SyntheticDataGenerator(grid_size=50, use_engine=True)
    
    print("\n1. Generating steady-state samples...")
    steady_data = generator.generate_steady_state_samples(n_samples=n_steady_samples)
    
    print("\n2. Generating time-series samples...")
    temporal_data = generator.generate_time_series_samples(n_trajectories=n_trajectories)
    
    print("\n3. Generating collocation points...")
    collocation = generator.generate_collocation_points(n_points=10000)
    
    print("\n4. Generating boundary conditions...")
    boundary = generator.generate_boundary_conditions()
    
    # Combine steady and temporal data
    train_data = {
        'x': np.concatenate([steady_data['x'], temporal_data['x']]),
        'y': np.concatenate([steady_data['y'], temporal_data['y']]),
        't': np.concatenate([steady_data['t'], temporal_data['t']]),
        'T': np.concatenate([steady_data['T'], temporal_data['T']]),
        'u': np.concatenate([steady_data['u'], temporal_data['u']])
    }
    
    dataset = {
        'train': train_data,
        'collocation': collocation,
        'boundary': boundary
    }
    
    print("\n" + "=" * 60)
    print(f"Dataset Summary:")
    print(f"  Training points: {len(train_data['x']):,}")
    print(f"  Collocation points: {len(collocation['x']):,}")
    print(f"  Boundary points: {len(boundary['x']):,}")
    print("=" * 60)
    
    # Save if output directory specified
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for key, data in dataset.items():
            np.savez(output_dir / f"{key}_data.npz", **data)
        print(f"\nSaved to: {output_dir}")
    
    return dataset


if __name__ == "__main__":
    # Generate and save dataset
    data_dir = Path(__file__).parent.parent / "data"
    dataset = generate_full_dataset(output_dir=data_dir)
