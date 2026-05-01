# Greenhouse Digital Twin Workflow

## End-to-End Workflow (Mermaid)

```mermaid
flowchart TD
    A[Sensor Nodes\nESP32 / Pico] -->|MQTT publish| B[MQTT Broker\nMosquitto]
    B --> C[Python GUI Subscriber]
    B --> D[Backend Services]

    C --> E[C++ Digital Twin Engine\nLaplace + What-If]
    D --> E

    E --> F[Live Moisture Map\n2D/3D Visualization]
    E --> G[Scenario Forecast\nWhat-If Results]

    H[Synthetic Data Generator] --> I[PINN Training Dataset]
    J[Kaggle CSV Adapter] --> I
    I --> K[PINN Trainer\nPyTorch]
    K --> L[Model Checkpoint]

    L --> M[Inference Utilities]
    M --> F
    M --> G
```

## Training Workflow (Hybrid)

```mermaid
flowchart LR
    S[Synthetic Data] --> M[Dataset Mixer]
    K[Kaggle CSV] --> M
    M --> T[PINN Training]
    T --> C[Checkpoint]
    C --> E[Evaluation]
```

## Operational Loop

1. Collect live sensor telemetry via MQTT.
2. Update dashboard and digital twin map.
3. Run what-if simulation for trend exploration.
4. Periodically retrain PINN with synthetic + Kaggle mix.
5. Deploy updated checkpoint for improved predictions.
