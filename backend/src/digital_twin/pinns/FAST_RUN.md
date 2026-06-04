# Fast PINN Run — quick reference

This documents the quick, CPU-friendly fast run we added to the PINN training path.

What I changed:
- Added a `--fast` preset to `training/train.py` which:
  - Reduces dataset size (steady samples, trajectories)
  - Reduces collocation and boundary points
  - Uses a smaller network by default
  - Disables the C++ engine fallback so generation is fast
- Installed CPU `torch` into the repo venv and verified a 1-epoch run
- Added an `epoch_logger.py` utility to append per-epoch logs to `training_log.md`

Quick commands

Install dependencies in the repository venv (already done by the launch script):

```bash
cd backend
./venv/bin/python -m pip install --upgrade pip setuptools wheel
./venv/bin/python -m pip install --index-url https://download.pytorch.org/whl/cpu torch
./venv/bin/python -m pip install -r src/digital_twin/pinns/requirements.txt
```

Run a fast single-epoch check (what I ran):

```bash
cd backend
./venv/bin/python src/digital_twin/pinns/training/train.py --fast --epochs 1 --device cpu
```

Where outputs landed:
- Dataset: `backend/src/digital_twin/pinns/data/`
- Checkpoint: `backend/src/digital_twin/pinns/training/checkpoints/moisture_pinn.pt`
- Training log (appended by `epoch_logger` if used): `backend/src/digital_twin/pinns/training/checkpoints/training_log.md`

Using the epoch logger from code

You can pass a Python callable to the trainer to log after each epoch. Example (already supported by the trainer API):

```py
from digital_twin.pinns.training.epoch_logger import log_epoch

def cb(epoch, losses):
    log_epoch('backend/src/digital_twin/pinns/training/checkpoints', epoch, losses)

# pass cb as `epoch_callback` to `MoisturePINNTrainer.train`
```

Standalone CLI usage for the logger:

```bash
python backend/src/digital_twin/pinns/training/epoch_logger.py --dir backend/src/digital_twin/pinns/training/checkpoints --epoch 1 --losses '{"total":543.87,"data":351.26}'
```

Next steps (optional):
- Continue training with `--epochs N` (fast or default) to improve fit
- Add automatic checkpointing frequency and evaluation hook
- Optionally explore GPU or Intel iGPU/XPU acceleration (more involved)
