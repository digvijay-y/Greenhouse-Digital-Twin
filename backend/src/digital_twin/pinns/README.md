# 🧠 Physics-Informed Neural Networks (PINN) for Soil Moisture Prediction

## Overview

This module implements a **Physics-Informed Neural Network** to predict 2D soil moisture distribution in a greenhouse given boundary conditions (4 corner sensor readings), ambient temperature, and time.

**Key Innovation**: Unlike traditional neural networks, PINNs embed physical laws as loss constraints, forcing the model to learn physically realistic solutions that obey the diffusion equation.

---

## Mathematical Foundation

### 1. Primary Governing Equation: 2D Diffusion with Evaporation

The soil moisture evolution is modeled by the **advection-diffusion equation with temperature-dependent evaporation**:

$$\frac{\partial u}{\partial t} = D \left(\frac{\partial^2 u}{\partial x^2} + \frac{\partial^2 u}{\partial y^2}\right) - E(T) \cdot u$$

**Variables:**
- $u(x,y,t)$ = Soil moisture percentage [0, 100]
- $x, y$ = Spatial coordinates [0, 1] (normalized greenhouse dimensions)
- $t$ = Time [0, 1] (normalized)
- $D$ = Diffusion coefficient = 0.01 (controls lateral water spread)
- $E(T)$ = Temperature-dependent evaporation rate

### 2. Evaporation Rate (Temperature Coupling)

Evaporation increases exponentially with temperature:

$$E(T) = e_0 \cdot \left(1 + \alpha(T_{\text{denorm}} - T_{\text{ref}})\right)$$

Where:
- $e_0$ = Base evaporation rate = 0.001 day$^{-1}$
- $\alpha$ = Temperature sensitivity coefficient = 0.03 °C$^{-1}$
- $T_{\text{ref}}$ = Reference temperature = 25°C
- $T_{\text{denorm}}$ = Denormalized temperature (15°C – 40°C)

**Physical Interpretation**: For every 1°C increase above 25°C, evaporation increases by 3%.

### 3. Boundary Conditions

Four **Dirichlet boundary conditions** at sensor locations (corners):

$$u(x_i, y_i, t) = m_i(t) \quad \text{for } i \in \{1,2,3,4\}$$

The 4 sensors are placed at:
- Sensor 1: $(x_1, y_1) = (0, 0)$ (bottom-left)
- Sensor 2: $(x_2, y_2) = (1, 0)$ (bottom-right)
- Sensor 3: $(x_3, y_3) = (0, 1)$ (top-left)
- Sensor 4: $(x_4, y_4) = (1, 1)$ (top-right)

**Edge conditions** are linearly interpolated between corners:
$$u(\text{edge}) = \text{Lerp}(m_i, m_j, \text{position})$$

### 4. Initial Conditions

Optional initial state at $t=0$:

$$u(x, y, 0) = u_0(x, y)$$

---

## Neural Network Architecture

### Input/Output Space

| Layer | Dimension | Details |
|-------|-----------|---------|
| **Input** | 4D | $(x, y, t, T)$ where $T$ is normalized temperature |
| **Hidden 1** | 64 neurons | Activation: Tanh |
| **Hidden 2** | 128 neurons | Activation: Tanh |
| **Hidden 3** | 128 neurons | Activation: Tanh |
| **Hidden 4** | 64 neurons | Activation: Tanh |
| **Output** | 1D | $u(x,y,t,T) \in [0, 1]$ (sigmoid), scaled to [0, 100] |

**Weight Initialization**: Xavier normal (preserves activation variance across layers)

$$W \sim \mathcal{N}\left(0, \frac{1}{\text{fan\_in} + \text{fan\_out}}\right)$$

---

## Loss Function (Multi-Objective)

The PINN combines four loss terms with tunable weights:

$$L_{\text{total}} = L_{\text{data}} + \lambda_{\text{PDE}} \cdot L_{\text{PDE}} + \lambda_{\text{BC}} \cdot L_{\text{BC}} + \lambda_{\text{IC}} \cdot L_{\text{IC}}$$

### Loss Components

#### 1. **Data Loss** (Supervised Learning)

Matches network output to observed sensor measurements:

$$L_{\text{data}} = \frac{1}{N_{\text{data}}} \sum_{i=1}^{N_{\text{data}}} \left(u_{\text{NN}}(x_i, y_i, t_i, T_i) - u_i^{\text{obs}}\right)^2$$

- $N_{\text{data}}$ ≈ 262,000 (training data points)
- Ensures model fits observed data

#### 2. **PDE Loss** (Physics Residual)

Enforces the diffusion equation at collocation points:

$$L_{\text{PDE}} = \frac{1}{N_{\text{collocation}}} \sum_{j=1}^{N_{\text{collocation}}} \left(\frac{\partial u}{\partial t} - D\nabla^2 u + E \cdot u\right)_j^2$$

Where the residual is computed via **automatic differentiation** (PyTorch autograd):

$$\text{Residual}_j = \frac{\partial u}{\partial t}\bigg|_j - D\left(\frac{\partial^2 u}{\partial x^2} + \frac{\partial^2 u}{\partial y^2}\right)\bigg|_j + E(T) \cdot u_j$$

- $N_{\text{collocation}}$ = 10,000 random interior points
- Residual should → 0 if solution satisfies PDE
- **Weight**: $\lambda_{\text{PDE}} = 0.1$ (default)

#### 3. **Boundary Condition Loss**

Penalties at domain edges:

$$L_{\text{BC}} = \frac{1}{N_{\text{BC}}} \sum_{k=1}^{N_{\text{BC}}} \left(u_{\text{NN}}(\mathbf{x}_k^{\text{edge}}, t_k, T_k) - u_k^{\text{BC}}\right)^2$$

- $N_{\text{BC}}$ ≈ 500 (sampled near corners and edges)
- **Weight**: $\lambda_{\text{BC}} = 1.0$ (critical, fixes domain boundaries)

#### 4. **Initial Condition Loss** (Optional)

Enforces starting state:

$$L_{\text{IC}} = \frac{1}{N_{\text{IC}}} \sum_{\ell=1}^{N_{\text{IC}}} \left(u_{\text{NN}}(x_\ell, y_\ell, 0, T_\ell) - u_0(x_\ell, y_\ell)\right)^2$$

- **Weight**: $\lambda_{\text{IC}} = 0.5$ (supplementary)

---

## Automatic Differentiation for Physics

The key advantage of PINNs: computing derivatives analytically via **reverse-mode autodiff** (backpropagation):

$$\frac{\partial u}{\partial t} = \frac{\partial}{\partial t} \text{NN}(x, y, t, T)$$

$$\frac{\partial^2 u}{\partial x^2} = \frac{\partial}{\partial x}\left(\frac{\partial}{\partial x} \text{NN}(x, y, t, T)\right)$$

**Computational Cost**: 1 forward pass + 1 extra backward pass per gradient computation. PyTorch handles this automatically.

---

## Training Algorithm

### Optimizer: Adam with Learning Rate Schedule

**Initial Setup:**
- Optimizer: Adam ($\beta_1 = 0.9, \beta_2 = 0.999, \epsilon = 10^{-8}$)
- Initial LR: $\eta_0 = 10^{-3}$ (configurable)
- Batch size: $N_b = 2048$

**Update Rule (Adam):**

$$\theta_{t+1} = \theta_t - \eta_t \cdot \frac{m_t}{\sqrt{v_t} + \epsilon}$$

Where:
$$m_t = \beta_1 m_{t-1} + (1-\beta_1) \nabla L_t \quad \text{(momentum)}$$
$$v_t = \beta_2 v_{t-1} + (1-\beta_2) \nabla L_t^2 \quad \text{(adaptive rate)}$$

**Learning Rate Schedule: ReduceLROnPlateau**

If validation loss plateaus for $p=100$ consecutive epochs:

$$\eta_{\text{new}} = \gamma \cdot \eta_{\text{old}}, \quad \gamma = 0.5$$

Prevents overfitting and allows finer optimization phases.

### Fast Local Run

If you only need a small end-to-end run on a CPU, use the fast preset:

```bash
python training/train.py --fast --epochs 1 --device cpu
```

This switches to a smaller synthetic dataset, skips the C++ engine, and uses a narrower network so you can get a working checkpoint quickly rather than optimizing for accuracy.

---

## Data Generation Pipeline

### Training Dataset Composition

| Source | Count | Details |
|--------|-------|---------|
| Steady-state samples | 100 | Random corner conditions → 2D grids (50×50) |
| Time-series trajectories | 20 | 48-hour simulations with hourly samples |
| Total data points | ~262,000 | Combined steady + temporal |
| Collocation points | 10,000 | Random interior for PDE |
| Boundary points | ~500 | Near corners and edges |

## Normalization

All inputs normalized to [0, 1] range:

$$x_{\text{norm}} = \frac{x}{L_x}, \quad y_{\text{norm}} = \frac{y}{L_y}, \quad t_{\text{norm}} = \frac{t}{T_{\text{total}}}$$

$$T_{\text{norm}} = \frac{T - 15}{40 - 15}, \quad T \in [15°C, 40°C]$$

Moisture output already [20, 80]% → scaled by sigmoid to [0→100]%

---

## Expected Convergence Behavior

### Loss Curves

**Epoch 0-500**: Steep decline
- Data loss: 2.5 → 1.0
- PDE loss: 0.8 → 0.3
- Model learns rough patterns

**Epoch 500-1500**: Gradual refinement
- Data loss: 1.0 → 0.3
- PDE loss: 0.3 → 0.05
- Physics constraints tighten

**Epoch 1500-2000**: Plateau/fine-tuning
- Data loss: 0.3 → 0.1
- PDE loss: 0.05 → 0.01
- LR scheduler may activate

### Success Criteria

✅ **Data Loss** < 0.15 (model fits observations)  
✅ **PDE Loss** < 0.02 (physics residual near zero)  
✅ **BC Loss** < 0.01 (boundaries enforced)  
✅ **Total Loss** decrease ≥ 80% from epoch 0  

---

## Physical Validation Checks

After training, verify learned physics:

### 1. Diffusion Validation

Sample random collocation point $(x, y, t, T)$:

```python
x.requires_grad_(True)
y.requires_grad_(True)
u = model(x, y, t, T)

# Compute Laplacian
u_xx = torch.autograd.grad(torch.autograd.grad(u, x)[0], x)[0]
u_yy = torch.autograd.grad(torch.autograd.grad(u, y)[0], y)[0]
laplacian = u_xx + u_yy

# Should be reasonable (not infinite or NaN)
assert not torch.isnan(laplacian)
```

### 2. Evaporation Sensitivity

Prediction at same location, different T:

$$\frac{\Delta u}{\Delta T}\bigg|_{\text{model}} \approx \frac{\partial u}{\partial T}\bigg|_{\text{theory}}$$

Temperature-dependent evaporation should cause faster moisture decrease at higher T.

### 3. Conservation Check

Check moisture doesn't violate bounds:

$$0 \leq u(x,y,t,T) \leq 100 \quad \forall (x,y,t,T)$$

(Model output constrained by sigmoid, so always satisfied)

---

## Hyperparameter Tuning Guide

| Parameter | Default | Tuning Strategy | Effect |
|-----------|---------|-----------------|--------|
| $\lambda_{\text{PDE}}$ | 0.1 | ↑ to 0.5 if physics poorly learned | Enforces PDE residual |
| $\lambda_{\text{BC}}$ | 1.0 | Keep high (critical) | Boundary enforcement |
| Epochs | 2000 | ↑ to 5000 if loss still decreasing | More optimization |
| LR | 1e-3 | ↓ to 5e-4 if unstable | Stability vs speed |
| Batch size | 2048 | Keep large for AMD GPUs | GPU memory efficiency |

---

## Inference (Using Trained Model)

Load and predict:

```python
import torch
from digital_twin.pinns.models.moisture_pinn import MoisturePINN

# Load checkpoint
checkpoint = torch.load('moisture_pinn.pt')
model = MoisturePINN(**checkpoint['config'])
model.load_state_dict(checkpoint['model_state_dict'])
model.eval()

# Predict at (x, y, t, T) = (0.5, 0.5, 0.3, 0.6)
with torch.no_grad():
    pred = model(
        torch.tensor([0.5]),
        torch.tensor([0.5]),
        torch.tensor([0.3]),
        torch.tensor([0.6])
    )
    print(f"Predicted moisture: {pred.item():.1f}%")
```

---

## Limitations & Future Work

### Current Limitations
- 2D spatial domain (real greenhouse is 3D)
- Assumes isotropic diffusion (ignores soil texture variations)
- No direct representation of irrigation events
- Temperature treated as spatially uniform

### Future Improvements
1. **3D Model**: Extend to z-dimension for root zone
2. **Irrigation Events**: Add impulse terms in PDE
3. **Heterogeneous Soil**: Spatially-varying diffusion $D(x,y)$
4. **Multi-Physics Coupling**: Root uptake, capillary rise
5. **Real Data Fine-Tuning**: Transfer learning from Kaggle datasets

---

## References

1. **Physics-Informed Neural Networks (PINNs):** Raissi et al., "Physics-informed neural networks: A deep learning framework for solving forward and inverse problems involving nonlinear partial differential equations," Journal of Computational Physics, 2019.

2. **Soil Moisture Modeling:** Kosugi et al., "Water retention curve for sandy soils," Journal of Soil Science Society of America.

3. **Automatic Differentiation:** Baydin et al., "Automatic differentiation in machine learning," JMLR, 2015.

---

## Files

- **Model**: [backend/src/digital_twin/pinns/models/moisture_pinn.py](./models/moisture_pinn.py)
- **Training**: [backend/src/digital_twin/pinns/training/train.py](./training/train.py)
- **Data Generation**: [backend/src/digital_twin/pinns/data/data_generator.py](./data/data_generator.py)
- **Launcher**: [scripts/train_pinn.sh](../../../scripts/train_pinn.sh)
