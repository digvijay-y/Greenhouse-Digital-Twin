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

# Add paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import torch

from digital_twin.pinns.models.moisture_pinn import MoisturePINN, MoisturePINNTrainer
from digital_twin.pinns.data.data_generator import generate_full_dataset


def train_pinn(
    epochs: int = 2000,
    batch_size: int = 2048,
    lr: float = 1e-3,
    lambda_pde: float = 0.1,
    device: str = 'cpu',
    save_path: Optional[Path] = None
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
    """
    print("=" * 70)
    print("  PINN Training for Soil Moisture Prediction")
    print("=" * 70)
    
    # Check device
    if device == 'cuda' and not torch.cuda.is_available():
        print("⚠️ CUDA not available, falling back to CPU")
        device = 'cpu'
    print(f"Device: {device}")
    
    # Generate or load dataset
    data_dir = Path(__file__).parent / "data"
    train_file = data_dir / "train_data.npz"
    
    if train_file.exists():
        print("\nLoading existing dataset...")
        train_data = dict(np.load(train_file))
        collocation = dict(np.load(data_dir / "collocation_data.npz"))
        boundary = dict(np.load(data_dir / "boundary_data.npz"))
    else:
        print("\nGenerating new dataset...")
        dataset = generate_full_dataset(output_dir=data_dir)
        train_data = dataset['train']
        collocation = dataset['collocation']
        boundary = dataset['boundary']
    
    # Convert to tensors
    def to_tensor(data: dict, device: str):
        return {k: torch.tensor(v, device=device) for k, v in data.items()}
    
    train_tensors = to_tensor(train_data, device)
    coll_tensors = to_tensor(collocation, device)
    bc_tensors = to_tensor(boundary, device)
    
    # Create model
    print("\nCreating PINN model...")
    model = MoisturePINN(
        hidden_layers=[64, 128, 128, 64],
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
        print_every=epochs // 20
    )
    
    # Save model
    if save_path is None:
        save_path = Path(__file__).parent / "checkpoints" / "moisture_pinn.pt"
    
    save_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        'model_state_dict': model.state_dict(),
        'losses': trainer.losses,
        'config': {
            'hidden_layers': [64, 128, 128, 64],
            'activation': 'tanh',
            'diffusion_coeff': 0.01,
            'evap_base': 0.001
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
    from typing import Optional
    
    parser = argparse.ArgumentParser(description="Train PINN for moisture prediction")
    parser.add_argument("--epochs", type=int, default=2000, help="Training epochs")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--lambda-pde", type=float, default=0.1, help="PDE loss weight")
    parser.add_argument("--device", type=str, default="cpu", help="Device (cpu/cuda)")
    parser.add_argument("--eval", type=str, default=None, help="Evaluate model from path")
    
    args = parser.parse_args()
    
    if args.eval:
        evaluate_model(Path(args.eval))
    else:
        train_pinn(
            epochs=args.epochs,
            lr=args.lr,
            lambda_pde=args.lambda_pde,
            device=args.device
        )
