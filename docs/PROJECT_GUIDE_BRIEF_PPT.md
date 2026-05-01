# Greenhouse Digital Twin
## Brief Project Presentation
### For Project Guide

---

## Slide 1: Problem Statement

- Greenhouse management often relies on sparse sensor readings.
- Operators need a complete moisture view, not point values only.
- Manual reasoning about future moisture trends is slow and error-prone.

Goal:
- Build a digital twin that ingests real-time sensor data and predicts moisture distribution and short-term trends.

---

## Slide 2: Project Scope (Current)

Included:
- Real-time sensor telemetry ingestion over MQTT.
- 2D moisture distribution estimation.
- What-If simulation engine for future trend exploration.
- PINN (Physics-Informed Neural Network) training pipeline.

Out of scope (removed):
- Irrigation automation/control logic.
- Anomaly detection module.
- Telegram bot integrations.

---

## Slide 3: High-Level Architecture

Layers:
- Firmware/Sensor layer: ESP32 + Pico publish telemetry.
- Messaging layer: MQTT broker (Mosquitto).
- Compute layer:
  - C++ engine (Laplace + What-If)
  - Python training/inference utilities for PINN
- Interface layer:
  - Python GUI dashboard
  - Web dashboard (frontend)

---

## Slide 4: Data Flow

1. Sensors publish moisture, BME280, NPK to MQTT topics.
2. Backend/GUI subscribers parse incoming values.
3. C++ engine computes full-grid moisture map.
4. GUI renders live map and trend summaries.
5. PINN pipeline trains on synthetic and optional Kaggle data.

---

## Slide 5: Core Mathematical Model

Steady-state moisture map (engine):
- Solves Laplace equation in 2D.

$$\nabla^2 u = 0$$

PINN dynamics (training model):

$$\frac{\partial u}{\partial t} = D\left(\frac{\partial^2 u}{\partial x^2}+\frac{\partial^2 u}{\partial y^2}\right)-E(T)u$$

Where:
- $u$: moisture percentage
- $D$: diffusion coefficient
- $E(T)$: temperature-dependent evaporation term

---

## Slide 6: Why Physics-Informed ML

Traditional ML only fits data.
PINN adds physical constraints during training:

$$L_{total}=L_{data}+\lambda_{pde}L_{pde}+\lambda_{bc}L_{bc}+\lambda_{ic}L_{ic}$$

Benefits:assets.

What
- Better generalization with sparse real data.
- Physically consistent predictions.
- Lower risk of unrealistic outputs.


---

## Slide 7: Training Strategy Under Deadline

Practical hybrid strategy:
- Synthetic data for physics coverage.
- Kaggle data for real-world variation.

Implemented support:
- Optional Kaggle CSV ingestion.
- Configurable mix ratio via launcher.

Example:

```bash
./scripts/train_pinn.sh --kaggle-csv ~/Downloads/soil_moisture.csv --kaggle-ratio 0.3
```

---

## Slide 8: Current Deliverables

Completed:
- Scope-aligned repository cleanup.
- Emoji-free GUI text.
- C++ engine + Python bindings.
- PINN training launcher and hybrid data support.
- Documentation for setup and training.

Artifacts:
- scripts/train_pinn.sh
- backend/src/digital_twin/engine/
- backend/src/digital_twin/pinns/

---

## Slide 9: Risks and Mitigations

Risk:
- Domain mismatch between Kaggle and greenhouse data.

Mitigation:
- Keep synthetic anchor with physics constraints.
- Use moderate Kaggle ratio first (e.g., 0.2-0.4).
- Validate with held-out synthetic + live telemetry snapshots.

Risk:
- Limited GPU resources.

Mitigation:
- Smaller epochs for iteration.
- Resume checkpoints for incremental improvements.

---

## Slide 10: Next Steps

Short-term:
- Train baseline + hybrid model.
- Compare losses and trend realism.
- Package reproducible experiment settings.

Submission-ready outputs:
- Architecture diagram
- Workflow diagram
- Training logs and model checkpoints
- Demo of live dashboard + what-if simulation
