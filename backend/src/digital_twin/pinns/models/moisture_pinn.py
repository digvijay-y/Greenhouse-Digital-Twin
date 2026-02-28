"""
PINN Model for Soil Moisture Diffusion

Architecture:
    Input: (x, y, t, T) - spatial coords, time, temperature
    Output: u(x, y, t) - moisture at that point
    
The network is trained to minimize:
    L_total = L_data + λ_pde * L_pde + λ_bc * L_bc + λ_ic * L_ic

Where:
    L_data: MSE on observed sensor data
    L_pde: Residual of the diffusion equation
    L_bc: Boundary condition loss
    L_ic: Initial condition loss
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Tuple, Optional


class MoisturePINN(nn.Module):
    """
    Physics-Informed Neural Network for soil moisture prediction.
    
    The network learns the mapping: (x, y, t, T) -> u
    while satisfying the diffusion PDE.
    """
    
    def __init__(
        self,
        hidden_layers: list = [64, 64, 64, 64],
        activation: str = 'tanh',
        diffusion_coeff: float = 0.01,
        evap_base: float = 0.001
    ):
        """
        Initialize the PINN.
        
        Args:
            hidden_layers: List of hidden layer sizes
            activation: Activation function ('tanh', 'relu', 'gelu')
            diffusion_coeff: Diffusion coefficient D
            evap_base: Base evaporation rate
        """
        super().__init__()
        
        self.D = diffusion_coeff
        self.E_base = evap_base
        
        # Build network
        layers = []
        input_dim = 4  # (x, y, t, T)
        
        for hidden_dim in hidden_layers:
            layers.append(nn.Linear(input_dim, hidden_dim))
            if activation == 'tanh':
                layers.append(nn.Tanh())
            elif activation == 'relu':
                layers.append(nn.ReLU())
            elif activation == 'gelu':
                layers.append(nn.GELU())
            input_dim = hidden_dim
        
        # Output layer (moisture value)
        layers.append(nn.Linear(input_dim, 1))
        layers.append(nn.Sigmoid())  # Moisture in [0, 1], scale to [0, 100] later
        
        self.network = nn.Sequential(*layers)
        
        # Initialize weights (Xavier)
        self._init_weights()
    
    def _init_weights(self):
        """Initialize weights using Xavier initialization."""
        for m in self.network.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_normal_(m.weight)
                nn.init.zeros_(m.bias)
    
    def forward(self, x: torch.Tensor, y: torch.Tensor, 
                t: torch.Tensor, T: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x, y: Spatial coordinates (normalized to [0, 1])
            t: Time (normalized)
            T: Temperature (normalized)
            
        Returns:
            u: Predicted moisture (scaled to [0, 100])
        """
        inputs = torch.stack([x, y, t, T], dim=-1)
        u_normalized = self.network(inputs).squeeze(-1)
        return u_normalized * 100  # Scale to percentage
    
    def compute_pde_residual(
        self, 
        x: torch.Tensor, 
        y: torch.Tensor, 
        t: torch.Tensor, 
        T: torch.Tensor
    ) -> torch.Tensor:
        """
        Compute the PDE residual for the diffusion equation.
        
        PDE: ∂u/∂t = D * (∂²u/∂x² + ∂²u/∂y²) - E(T) * u
        
        Residual should be zero for solutions satisfying the PDE.
        """
        # Enable gradients for inputs
        x = x.clone().requires_grad_(True)
        y = y.clone().requires_grad_(True)
        t = t.clone().requires_grad_(True)
        
        # Forward pass
        u = self.forward(x, y, t, T)
        
        # First derivatives
        grad_x = torch.autograd.grad(
            u, x, grad_outputs=torch.ones_like(u),
            create_graph=True, retain_graph=True
        )[0]
        
        grad_y = torch.autograd.grad(
            u, y, grad_outputs=torch.ones_like(u),
            create_graph=True, retain_graph=True
        )[0]
        
        grad_t = torch.autograd.grad(
            u, t, grad_outputs=torch.ones_like(u),
            create_graph=True, retain_graph=True
        )[0]
        
        # Second derivatives (Laplacian)
        grad_xx = torch.autograd.grad(
            grad_x, x, grad_outputs=torch.ones_like(grad_x),
            create_graph=True, retain_graph=True
        )[0]
        
        grad_yy = torch.autograd.grad(
            grad_y, y, grad_outputs=torch.ones_like(grad_y),
            create_graph=True, retain_graph=True
        )[0]
        
        # Evaporation rate (temperature-dependent)
        E = self.E_base * (1 + 0.03 * (T * 40 - 25))  # Denormalize T
        
        # PDE residual: du/dt - D*(d2u/dx2 + d2u/dy2) + E*u = 0
        residual = grad_t - self.D * (grad_xx + grad_yy) + E * u
        
        return residual


class MoisturePINNTrainer:
    """
    Trainer for the Moisture PINN.
    
    Handles:
    - Data loading
    - Loss computation (data + physics)
    - Training loop
    - Validation
    """
    
    def __init__(
        self,
        model: MoisturePINN,
        lr: float = 1e-3,
        lambda_pde: float = 1.0,
        lambda_bc: float = 1.0,
        lambda_ic: float = 1.0,
        device: str = 'cpu'
    ):
        """
        Initialize trainer.
        
        Args:
            model: The PINN model
            lr: Learning rate
            lambda_pde: Weight for PDE loss
            lambda_bc: Weight for boundary condition loss
            lambda_ic: Weight for initial condition loss
            device: 'cpu' or 'cuda'
        """
        self.model = model.to(device)
        self.device = device
        
        self.lambda_pde = lambda_pde
        self.lambda_bc = lambda_bc
        self.lambda_ic = lambda_ic
        
        self.optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, patience=100, factor=0.5
        )
        
        self.losses = {'total': [], 'data': [], 'pde': [], 'bc': [], 'ic': []}
    
    def compute_loss(
        self,
        data_points: Tuple[torch.Tensor, ...],
        collocation_points: Tuple[torch.Tensor, ...],
        boundary_points: Optional[Tuple[torch.Tensor, ...]] = None,
        initial_points: Optional[Tuple[torch.Tensor, ...]] = None
    ) -> Tuple[torch.Tensor, dict]:
        """
        Compute total loss.
        
        Args:
            data_points: (x, y, t, T, u_true) sensor observations
            collocation_points: (x, y, t, T) points for PDE residual
            boundary_points: (x, y, t, T, u_bc) boundary values
            initial_points: (x, y, t, T, u_ic) initial values
            
        Returns:
            total_loss, loss_dict
        """
        x_data, y_data, t_data, T_data, u_true = data_points
        
        # Data loss
        u_pred = self.model(x_data, y_data, t_data, T_data)
        loss_data = torch.mean((u_pred - u_true) ** 2)
        
        # PDE loss on collocation points
        x_coll, y_coll, t_coll, T_coll = collocation_points
        residual = self.model.compute_pde_residual(x_coll, y_coll, t_coll, T_coll)
        loss_pde = torch.mean(residual ** 2)
        
        # Boundary condition loss
        loss_bc = torch.tensor(0.0, device=self.device)
        if boundary_points is not None:
            x_bc, y_bc, t_bc, T_bc, u_bc = boundary_points
            u_bc_pred = self.model(x_bc, y_bc, t_bc, T_bc)
            loss_bc = torch.mean((u_bc_pred - u_bc) ** 2)
        
        # Initial condition loss
        loss_ic = torch.tensor(0.0, device=self.device)
        if initial_points is not None:
            x_ic, y_ic, t_ic, T_ic, u_ic = initial_points
            u_ic_pred = self.model(x_ic, y_ic, t_ic, T_ic)
            loss_ic = torch.mean((u_ic_pred - u_ic) ** 2)
        
        # Total loss
        total_loss = (
            loss_data + 
            self.lambda_pde * loss_pde + 
            self.lambda_bc * loss_bc + 
            self.lambda_ic * loss_ic
        )
        
        return total_loss, {
            'total': total_loss.item(),
            'data': loss_data.item(),
            'pde': loss_pde.item(),
            'bc': loss_bc.item(),
            'ic': loss_ic.item()
        }
    
    def train_step(
        self,
        data_points: Tuple[torch.Tensor, ...],
        collocation_points: Tuple[torch.Tensor, ...],
        **kwargs
    ) -> dict:
        """Single training step."""
        self.model.train()
        self.optimizer.zero_grad()
        
        loss, loss_dict = self.compute_loss(
            data_points, collocation_points, **kwargs
        )
        
        loss.backward()
        self.optimizer.step()
        
        # Record losses
        for key, val in loss_dict.items():
            self.losses[key].append(val)
        
        return loss_dict
    
    def train(
        self,
        data_points: Tuple[torch.Tensor, ...],
        collocation_points: Tuple[torch.Tensor, ...],
        epochs: int = 1000,
        print_every: int = 100,
        **kwargs
    ):
        """
        Full training loop.
        
        Args:
            data_points: Sensor data
            collocation_points: PDE collocation points
            epochs: Number of epochs
            print_every: Print frequency
        """
        print(f"Training PINN for {epochs} epochs...")
        print("-" * 60)
        
        for epoch in range(epochs):
            loss_dict = self.train_step(data_points, collocation_points, **kwargs)
            self.scheduler.step(loss_dict['total'])
            
            if (epoch + 1) % print_every == 0:
                lr = self.optimizer.param_groups[0]['lr']
                print(f"Epoch {epoch+1:5d} | "
                      f"Total: {loss_dict['total']:.6f} | "
                      f"Data: {loss_dict['data']:.6f} | "
                      f"PDE: {loss_dict['pde']:.6f} | "
                      f"LR: {lr:.2e}")
        
        print("-" * 60)
        print("Training complete!")
    
    def predict(
        self, 
        x: np.ndarray, 
        y: np.ndarray, 
        t: float, 
        T: float
    ) -> np.ndarray:
        """
        Predict moisture distribution.
        
        Args:
            x, y: Grid coordinates (2D arrays)
            t: Time value
            T: Temperature value
            
        Returns:
            Predicted moisture grid
        """
        self.model.eval()
        
        x_flat = torch.tensor(x.flatten(), dtype=torch.float32, device=self.device)
        y_flat = torch.tensor(y.flatten(), dtype=torch.float32, device=self.device)
        t_tensor = torch.full_like(x_flat, t)
        T_tensor = torch.full_like(x_flat, T)
        
        with torch.no_grad():
            u_pred = self.model(x_flat, y_flat, t_tensor, T_tensor)
        
        return u_pred.cpu().numpy().reshape(x.shape)


def create_default_pinn(device: str = 'cpu') -> Tuple[MoisturePINN, MoisturePINNTrainer]:
    """
    Create a default PINN model and trainer.
    
    Returns:
        (model, trainer) tuple
    """
    model = MoisturePINN(
        hidden_layers=[64, 128, 128, 64],
        activation='tanh',
        diffusion_coeff=0.01,
        evap_base=0.001
    )
    
    trainer = MoisturePINNTrainer(
        model=model,
        lr=1e-3,
        lambda_pde=0.1,  # Start with lower PDE weight
        lambda_bc=1.0,
        lambda_ic=1.0,
        device=device
    )
    
    return model, trainer
