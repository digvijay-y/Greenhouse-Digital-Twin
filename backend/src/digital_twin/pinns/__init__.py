"""
Physics-Informed Neural Networks (PINNs) for Soil Moisture Prediction

This module implements a PINN that learns to predict soil moisture distribution
while respecting the physics of moisture diffusion in soil.

The governing equation is the 2D diffusion equation:
    ∂u/∂t = D * (∂²u/∂x² + ∂²u/∂y²) - E(T) * u + S(x,y,t)

Where:
    u = soil moisture (%)
    D = diffusion coefficient
    E(T) = evaporation rate (temperature-dependent)
    S = source term (irrigation)

Reference:
    - Raissi, M., Perdikaris, P., & Karniadakis, G. E. (2019). 
      Physics-informed neural networks: A deep learning framework for 
      solving forward and inverse problems involving nonlinear partial 
      differential equations.
"""

__version__ = "0.1.0"
