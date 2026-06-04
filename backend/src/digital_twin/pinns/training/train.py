#!/usr/bin/env python3
"""
PINN Training Script for Soil Moisture Prediction

Usage:
    python train.py [--epochs EPOCHS] [--lr LR] [--device DEVICE]
    
Example:
    python train.py --epochs 5000 --device cuda
"""

import argparse
import sys
from pathlib import Path
import numpy as np
from typing import Optional, Dict, List

# Add paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import torch

from digital_twin.pinns.models.moisture_pinn import MoisturePINN, MoisturePINNTrainer
from digital_twin.pinns.data.data_generator import generate_full_dataset
from digital_twin.pinns.data.kaggle_adapter import load_kaggle_dataset


def _to_tensor(data: dict, device: str):
    return {k: torch.tensor(v, device=device) for k, v in data.items()}


def _sample_dict(data: Dict[str, np.ndarray], count: int, seed: int) -> Dict[str, np.ndarray]:
    n = len(data['u'])
    if count >= n:
        return data
    rng = np.random.default_rng(seed)
    idx = rng.choice(n, size=count, replace=False)
    return {k: v[idx] for k, v in data.items()}


def _mix_datasets(
    synth: Dict[str, np.ndarray],
    kaggle: Dict[str, np.ndarray],
    kaggle_ratio: float,
    seed: int,
) -> Dict[str, np.ndarray]:
    if kaggle_ratio <= 0.0:
        return synth
    if kaggle_ratio >= 1.0:
        return kaggle

    n_s = len(synth['u'])
    n_k = len(kaggle['u'])
    max_final = int(min(n_s / (1.0 - kaggle_ratio), n_k / kaggle_ratio))

    if max_final <= 0:
        return synth

    take_k = max(1, int(max_final * kaggle_ratio))
    take_s = max(1, max_final - take_k)

    synth_s = _sample_dict(synth, take_s, seed=seed)
    kaggle_s = _sample_dict(kaggle, take_k, seed=seed + 1)

    mixed = {
        k: np.concatenate([synth_s[k], kaggle_s[k]]).astype(np.float32)
        for k in ['x', 'y', 't', 'T', 'u']
    }
    return mixed


def train_pinn(
    epochs: Optional[int] = None,
    batch_size: int = 2048,
    lr: float = 1e-3,
    lambda_pde: float = 0.1,
    device: str = 'cpu',
    save_path: Optional[Path] = None,
    kaggle_csv: Optional[Path] = None,
    kaggle_ratio: float = 0.3,
    seed: int = 42,
    fast_mode: bool = False,
    n_steady_samples: int = 100,
    n_trajectories: int = 20,
    grid_size: int = 50,
    n_collocation_points: int = 10000,
    n_boundary_points_per_edge: int = 50,
    n_boundary_time_samples: int = 10,
    use_engine: bool = True,
    hidden_layers: Optional[List[int]] = None,
):
    """
    Train the Moisture PINN.
    
    Args:
        epochs: Number of training epochs
        batch_size: Batch size (if data > batch_size, use batching)
        lr: Learning rate
        lambda_pde: Weight for PDE loss
        device: 'cpu' or 'cuda'
        save_path: Where to save the trained model
        kaggle_csv: Optional CSV path for Kaggle/real-world data
        kaggle_ratio: Fraction of Kaggle samples in mixed training data
        seed: Random seed for deterministic mixing
    """
    print("=" * 70)
    print("  PINN Training for Soil Moisture Prediction")
    print("=" * 70)
    
    # Check device
    if device == 'cuda' and not torch.cuda.is_available():
        print("⚠️ CUDA not available, falling back to CPU")
        device = 'cpu'
    print(f"Device: {device}")

    if fast_mode:
        n_steady_samples = min(n_steady_samples, 12)
        n_trajectories = min(n_trajectories, 3)
        grid_size = min(grid_size, 20)
        n_collocation_points = min(n_collocation_points, 1000)
        n_boundary_points_per_edge = min(n_boundary_points_per_edge, 20)
        n_boundary_time_samples = min(n_boundary_time_samples, 4)
        use_engine = False
        if hidden_layers is None:
            hidden_layers = [32, 64, 64, 32]

    epochs = epochs if epochs is not None else (200 if fast_mode else 2000)
    
    # Generate or load dataset
    data_dir = Path(__file__).resolve().parents[1] / "data"
    train_file = data_dir / "train_data.npz"
    
    if train_file.exists() and not fast_mode:
        print("\nLoading existing dataset...")
        train_data = dict(np.load(train_file))
        collocation = dict(np.load(data_dir / "collocation_data.npz"))
        boundary = dict(np.load(data_dir / "boundary_data.npz"))
    else:
        print("\nGenerating new dataset...")
        dataset = generate_full_dataset(
            output_dir=data_dir,
            n_steady_samples=n_steady_samples,
            n_trajectories=n_trajectories,
            grid_size=grid_size,
            n_collocation_points=n_collocation_points,
            n_boundary_points_per_edge=n_boundary_points_per_edge,
            n_boundary_time_samples=n_boundary_time_samples,
            use_engine=use_engine,
            seed=seed,
        )
        train_data = dataset['train']
        collocation = dataset['collocation']
        boundary = dataset['boundary']
    
    # Optionally blend synthetic + Kaggle data
    if kaggle_csv is not None:
        print(f"\nLoading Kaggle dataset from: {kaggle_csv}")
        kaggle_data = load_kaggle_dataset(kaggle_csv)
        train_data = _mix_datasets(
            synth=train_data,
            kaggle=kaggle_data,
            kaggle_ratio=kaggle_ratio,
            seed=seed,
        )
        print(
            f"Mixed training data size: {len(train_data['u']):,} "
            f"(target Kaggle ratio={kaggle_ratio:.2f})"
        )

    train_tensors = _to_tensor(train_data, device)
    coll_tensors = _to_tensor(collocation, device)
    bc_tensors = _to_tensor(boundary, device)
    
    # Create model
    print("\nCreating PINN model...")
    model_hidden_layers = hidden_layers or [64, 128, 128, 64]
    model = MoisturePINN(
        hidden_layers=model_hidden_layers,
        activation='tanh',
        diffusion_coeff=0.01,
        evap_base=0.001
    )
    
    trainer = MoisturePINNTrainer(
        model=model,
        lr=lr,
        lambda_pde=lambda_pde,
        lambda_bc=1.0,
        lambda_ic=0.5,
        device=device
    )
    
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # Prepare data tuples
    data_points = (
        train_tensors['x'],
        train_tensors['y'],
        train_tensors['t'],
        train_tensors['T'],
        train_tensors['u']
    )
    
    collocation_points = (
        coll_tensors['x'],
        coll_tensors['y'],
        coll_tensors['t'],
        coll_tensors['T']
    )
    
    boundary_points = (
        bc_tensors['x'],
        bc_tensors['y'],
        bc_tensors['t'],
        bc_tensors['T'],
        bc_tensors['u']
    )
    
    # Train
    print(f"\nTraining for {epochs} epochs...")
    trainer.train(
        data_points=data_points,
        collocation_points=collocation_points,
        boundary_points=boundary_points,
        epochs=epochs,
        print_every=max(1, epochs // 20)
    )
    
    # Save model
    if save_path is None:
        save_path = Path(__file__).parent / "checkpoints" / "moisture_pinn.pt"
    
    save_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        'model_state_dict': model.state_dict(),
        'losses': trainer.losses,
        'config': {
            'hidden_layers': model_hidden_layers,
            'activation': 'tanh',
            'diffusion_coeff': 0.01,
            'evap_base': 0.001
        },
        'training_meta': {
            'kaggle_ratio': kaggle_ratio,
            'kaggle_csv': str(kaggle_csv) if kaggle_csv else None,
            'fast_mode': fast_mode,
            'n_steady_samples': n_steady_samples,
            'n_trajectories': n_trajectories,
            'grid_size': grid_size,
            'n_collocation_points': n_collocation_points,
            'n_boundary_points_per_edge': n_boundary_points_per_edge,
            'n_boundary_time_samples': n_boundary_time_samples,
            'use_engine': use_engine,
        }
    }, save_path)
    
    print(f"\n✅ Model saved to: {save_path}")
    
    # Final evaluation
    print("\nFinal Losses:")
    print(f"  Data: {trainer.losses['data'][-1]:.6f}")
    print(f"  PDE: {trainer.losses['pde'][-1]:.6f}")
    print(f"  BC: {trainer.losses['bc'][-1]:.6f}")
    print(f"  Total: {trainer.losses['total'][-1]:.6f}")
    
    return model, trainer


def evaluate_model(model_path: Path):
    """Load and evaluate a trained model."""
    import matplotlib.pyplot as plt
    
    checkpoint = torch.load(model_path)
    
    model = MoisturePINN(**checkpoint['config'])
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    # Plot loss curves
    losses = checkpoint['losses']
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    
    axes[0].semilogy(losses['total'], label='Total')
    axes[0].semilogy(losses['data'], label='Data')
    axes[0].semilogy(losses['pde'], label='PDE')
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Loss')
    axes[0].set_title('Training Losses')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Test prediction
    x = np.linspace(0, 1, 50)
    y = np.linspace(0, 1, 50)
    X, Y = np.meshgrid(x, y)
    
    x_flat = torch.tensor(X.flatten(), dtype=torch.float32)
    y_flat = torch.tensor(Y.flatten(), dtype=torch.float32)
    t = torch.zeros_like(x_flat)
    T = torch.full_like(x_flat, 0.5)  # 25°C normalized
    
    with torch.no_grad():
        u_pred = model(x_flat, y_flat, t, T)
    
    u_grid = u_pred.numpy().reshape(50, 50)
    
    im = axes[1].imshow(u_grid, cmap='RdYlGn', extent=[0, 1, 1, 0], vmin=0, vmax=100)
    axes[1].set_xlabel('x')
    axes[1].set_ylabel('y')
    axes[1].set_title('Predicted Moisture at t=0, T=25°C')
    plt.colorbar(im, ax=axes[1], label='Moisture %')
    
    plt.tight_layout()
    plt.savefig(model_path.parent / 'training_results.png', dpi=150)
    plt.show()
    
    print(f"Results saved to: {model_path.parent / 'training_results.png'}")


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Train PINN for moisture prediction")
    parser.add_argument("--epochs", type=int, default=None, help="Training epochs")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--lambda-pde", type=float, default=0.1, help="PDE loss weight")
    parser.add_argument("--device", type=str, default="cpu", help="Device (cpu/cuda)")
    parser.add_argument("--kaggle-csv", type=str, default=None, help="Optional Kaggle CSV file path")
    parser.add_argument("--kaggle-ratio", type=float, default=0.3, help="Kaggle fraction in mixed training data [0,1]")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for data mixing")
    parser.add_argument("--fast", action="store_true", help="Use a smaller dataset and model for a quick run")
    parser.add_argument("--no-engine", action="store_true", help="Skip the C++ engine and use the lightweight synthetic fallback")
    parser.add_argument("--n-steady-samples", type=int, default=None, help="Override steady-state sample count")
    parser.add_argument("--n-trajectories", type=int, default=None, help="Override time-series trajectory count")
    parser.add_argument("--grid-size", type=int, default=None, help="Override synthetic grid size")
    parser.add_argument("--n-collocation-points", type=int, default=None, help="Override PDE collocation point count")
    parser.add_argument("--n-boundary-points-per-edge", type=int, default=None, help="Override boundary sample count per edge")
    parser.add_argument("--n-boundary-time-samples", type=int, default=None, help="Override boundary time sample count")
    parser.add_argument("--hidden-layers", type=int, nargs="*", default=None, help="Override hidden layer sizes, e.g. --hidden-layers 32 64 64 32")
    parser.add_argument("--eval", type=str, default=None, help="Evaluate model from path")
    
    args = parser.parse_args()
    
    if args.eval:
        evaluate_model(Path(args.eval))
    else:
        kaggle_csv = Path(args.kaggle_csv).expanduser().resolve() if args.kaggle_csv else None
        if kaggle_csv is not None and not kaggle_csv.exists():
            raise FileNotFoundError(f"Kaggle CSV not found: {kaggle_csv}")
        if not 0.0 <= args.kaggle_ratio <= 1.0:
            raise ValueError("--kaggle-ratio must be between 0 and 1")

        fast_mode = args.fast
        epochs = args.epochs if args.epochs is not None else (200 if fast_mode else 2000)
        n_steady_samples = args.n_steady_samples if args.n_steady_samples is not None else (12 if fast_mode else 100)
        n_trajectories = args.n_trajectories if args.n_trajectories is not None else (3 if fast_mode else 20)
        grid_size = args.grid_size if args.grid_size is not None else (20 if fast_mode else 50)
        n_collocation_points = args.n_collocation_points if args.n_collocation_points is not None else (1000 if fast_mode else 10000)
        n_boundary_points_per_edge = args.n_boundary_points_per_edge if args.n_boundary_points_per_edge is not None else (20 if fast_mode else 50)
        n_boundary_time_samples = args.n_boundary_time_samples if args.n_boundary_time_samples is not None else (4 if fast_mode else 10)
        use_engine = not args.no_engine and not fast_mode

        train_pinn(
            epochs=epochs,
            lr=args.lr,
            lambda_pde=args.lambda_pde,
            device=args.device,
            kaggle_csv=kaggle_csv,
            kaggle_ratio=args.kaggle_ratio,
            seed=args.seed,
            fast_mode=fast_mode,
            n_steady_samples=n_steady_samples,
            n_trajectories=n_trajectories,
            grid_size=grid_size,
            n_collocation_points=n_collocation_points,
            n_boundary_points_per_edge=n_boundary_points_per_edge,
            n_boundary_time_samples=n_boundary_time_samples,
            use_engine=use_engine,
            hidden_layers=args.hidden_layers,
        )
