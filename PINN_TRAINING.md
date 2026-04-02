# 🌱 PINN Training Quick Start Guide

## Ready to train PINN for soil moisture prediction!

### **What's been set up:**
✅ Training launcher script: `scripts/train_pinn.sh`  
✅ Checkpoint directory: `backend/src/digital_twin/pinns/training/checkpoints/`  
✅ Data generator ready: `backend/src/digital_twin/pinns/data/data_generator.py`  
✅ Training script ready: `backend/src/digital_twin/pinns/training/train.py`  

---

## **GPU Information**
Your system has an integrated GPU. When you run the launcher, it will:
1. Auto-detect CUDA availability
2. Install PyTorch with GPU support (if not already installed)
3. Show GPU specs (name, VRAM, compute capability)
4. Estimate training time (~3-5 minutes for 2000 epochs on GPU)

---

## **How to Train**

### **Option 1: Default Training (Recommended for first run)**
```bash
./scripts/train_pinn.sh
```
- Epochs: 2000
- Learning Rate: 1e-3
- Device: Auto-detect GPU/CPU
- Data: Generate new datasets

**Expected output:**
- Training takes ~3-5 min (GPU) or 30-40 min (CPU)
- Loss curves are saved
- Model checkpoint: `backend/src/digital_twin/pinns/training/checkpoints/moisture_pinn.pt`
- Visualization: `backend/src/digital_twin/pinns/training/checkpoints/training_results.png`

---

### **Option 2: Custom Configuration**
```bash
# More epochs (deeper training)
./scripts/train_pinn.sh --epochs 5000

# Force GPU or CPU
./scripts/train_pinn.sh --device cuda
./scripts/train_pinn.sh --device cpu

# Adjust physics weight (higher = stricter physics enforcement)
./scripts/train_pinn.sh --lambda-pde 0.5

# Skip data generation (reuse existing data)
./scripts/train_pinn.sh --skip-data-gen --epochs 3000

# Combine them
./scripts/train_pinn.sh --epochs 5000 --device cuda --lambda-pde 0.3

# Hybrid training: synthetic + Kaggle from day one (deadline-friendly)
./scripts/train_pinn.sh --kaggle-csv ~/Downloads/soil_moisture.csv --kaggle-ratio 0.3

# Hybrid retrain with existing synthetic data (skip regen)
./scripts/train_pinn.sh --skip-data-gen --kaggle-csv ~/Downloads/soil_moisture.csv --kaggle-ratio 0.5
```

### **Option 3: Data Generation Only** (no training)
```bash
./scripts/train_pinn.sh --generate-only
```
Creates training data files but doesn't train the model.

---

### **Option 4: Advanced Training**
```bash
# Set custom learning rate
./scripts/train_pinn.sh --lr 5e-4

# Help menu
./scripts/train_pinn.sh --help
```

---

## **What Happens During Training**

**Phase 1: Environment Check** (~10 sec)
- Verifies Python / venv
- Installs PyTorch with GPU support (if needed, ~3-5 min first time)
- Auto-detects GPU and shows specs

**Phase 2: Data Generation** (~1-2 min)
- Generates synthetic training data:
  - 262,000 data points (steady-state + time-series)
  - 10,000 collocation points (PDE residual)
  - 500+ boundary condition points
- Uses C++ engine if available, falls back to Python interpolation

**Phase 3: Training** (~3-5 min on GPU, 30-40 min on CPU)
- Trains PINN neural network
- Monitors loss curves: data loss, PDE loss, BC loss, total loss
- Applies physics-informed penalty if learning poorly
- Saves checkpoint every 100 epochs (if implementing)
- Reduces learning rate if validation plateaus

**Phase 4: Post-Training** (~10 sec)
- Saves model weights: `moisture_pinn.pt`
- Generates loss plots: `training_results.png`
- Shows final metrics

---

## **Training Configuration**

### **Default Physics Parameters:**
```python
λ_pde = 0.1      # PDE residual weight (enforce diffusion equation)
λ_bc = 1.0       # Boundary condition weight
λ_ic = 0.5       # Initial condition weight
diffusion_coeff = 0.01
evaporation = 0.001
```

### **Model Architecture:**
```
Input:  4D  (x, y, t, T) where T = normalized temperature
Hidden: [64, 128, 128, 64] layers with Tanh activation
Output: 1D  (soil moisture %)
```

### **Training Parameters:**
```
Optimizer: Adam
Batch Size: 2048
Learning Rate: 1e-3 (default)
LR Scheduler: ReduceLROnPlateau (patience=100, factor=0.5)
```

---

## **Monitoring Training**

### **During Training:**
- Console shows epoch number and loss values
- Updates every 100 epochs (configurable)
- Look for `data_loss`, `pde_loss`, `bc_loss`, `total_loss` decreasing

### **Success Indicators:**
✅ Total loss decreases by 50%+ from start  
✅ PDE loss decreases by 80%+ (physics learning)  
✅ Training completes without errors  
✅ Model checkpoint file is saved  

### **Example Output:**
```
Epoch 0 | Total: 2.34 | Data: 1.50 | PDE: 0.60 | BC: 0.24
Epoch 100 | Total: 1.89 | Data: 1.20 | PDE: 0.45 | BC: 0.24
Epoch 500 | Total: 0.98 | Data: 0.70 | PDE: 0.20 | BC: 0.08
Epoch 1000 | Total: 0.45 | Data: 0.35 | PDE: 0.08 | BC: 0.02
Epoch 2000 | Total: 0.12 | Data: 0.10 | PDE: 0.01 | BC: 0.01 ✓
```

---

## **After Training**

### **1. View Results**
```bash
# Open the training visualization
open backend/src/digital_twin/pinns/training/checkpoints/training_results.png
```

Shows:
- Loss curves (data, PDE, BC, total)
- Predicted moisture distribution at t=0, T=25°C

### **2. Use the Model**
Model checkpoint saved as: `backend/src/digital_twin/pinns/training/checkpoints/moisture_pinn.pt`

To load and use:
```python
import torch
from digital_twin.pinns.models.moisture_pinn import MoisturePINN

# Load
checkpoint = torch.load('checkpoints/moisture_pinn.pt')
model = MoisturePINN(**checkpoint['config'])
model.load_state_dict(checkpoint['model_state_dict'])
model.eval()

# Predict
with torch.no_grad():
    x, y, t, T = 0.5, 0.5, 0.3, 0.6  # Normalized coordinates
    moisture = model(torch.tensor([x]), torch.tensor([y]), 
                     torch.tensor([t]), torch.tensor([T]))
    print(f"Predicted moisture: {moisture.item():.1f}%")
```

### **3. Retrain with Different Parameters**
```bash
# Use same data, different hyperparameters
./scripts/train_pinn.sh --skip-data-gen --epochs 5000 --lambda-pde 0.3
```

---

## **Troubleshooting**

### **Q: Training is slow (on CPU)?**
**A:** This is expected (30-40 min on CPU). To use GPU:
1. Check if CUDA installed: `nvidia-smi`
2. Run: `./scripts/train_pinn.sh --device cuda`
3. If still slow, GPU may not be properly set up.

### **Q: Data generation fails?**
**A:** C++ engine not available (optional). The script falls back to Python interpolation. If it still fails, check:
```bash
backend/venv/bin/python backend/src/digital_twin/pinns/data/data_generator.py
```

### **Q: Training stops early or crashes?**
**A:** Check:
1. Disk space: `df -h` (need ~200MB)
2. RAM: `free -h` (need ~4GB)
3. Console errors above the crash

### **Q: GPU not detected?**
**A:** 
```bash
backend/venv/bin/python -c "import torch; print(torch.cuda.is_available())"
```
Should print `True`. If `False`, GPU support needs reinstall:
```bash
backend/venv/bin/pip uninstall torch -y
backend/venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cu118
```

---

## **Next Steps After Training**

1. **Validate results:** Check loss curves and predicted moisture map
2. **Fine-tune:** Retrain with adjusted hyperparameters if physics isn't learned well
3. **Integrate:** Use model in inference endpoints / dashboard
4. **Benchmark:** Compare against simplified baselines (exponential decay, etc.)
5. **Kaggle data:** After baseline works, integrate real agricultural datasets for refinement

---

## **Files Reference**

| File | Purpose |
|------|---------|
| `scripts/train_pinn.sh` | Main training launcher (you'll run this) |
| `backend/src/digital_twin/pinns/training/train.py` | Core training code |
| `backend/src/digital_twin/pinns/models/moisture_pinn.py` | PINN model definition |
| `backend/src/digital_twin/pinns/data/data_generator.py` | Synthetic data generation |
| `backend/src/digital_twin/pinns/training/checkpoints/` | Saved models (output) |
| `backend/src/digital_twin/pinns/data/` | Training data (output) |

---

**🚀 Ready? Run:** `./scripts/train_pinn.sh`
