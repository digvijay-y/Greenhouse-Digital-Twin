"""Utilities to adapt Kaggle CSV data to PINN training format.

Expected output keys: x, y, t, T, u (all float32, normalized except u in [0, 100]).
"""

from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd


def _find_col(df: pd.DataFrame, candidates) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    lowered = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in lowered:
            return lowered[c.lower()]
    return None


def _normalize(series: pd.Series, lo: float, hi: float) -> np.ndarray:
    if hi <= lo:
        return np.full(len(series), 0.5, dtype=np.float32)
    return ((series.astype(float) - lo) / (hi - lo)).clip(0.0, 1.0).to_numpy(dtype=np.float32)


def load_kaggle_dataset(csv_path: Path, seed: int = 42) -> Dict[str, np.ndarray]:
    """Load a Kaggle CSV and map it into PINN format.

    Required: a moisture column.
    Optional: temperature, timestamp/time, x/y or lat/lon.
    Missing optional fields are synthesized safely.
    """
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError(f"CSV has no rows: {csv_path}")

    moisture_col = _find_col(
        df,
        ["moisture", "soil_moisture", "humidity_soil", "target", "y", "u"],
    )
    if moisture_col is None:
        raise ValueError(
            "Could not find moisture column. Try one of: moisture, soil_moisture, target"
        )

    temp_col = _find_col(df, ["temperature", "temp", "soil_temp", "air_temp", "t_air"])
    time_col = _find_col(df, ["timestamp", "time", "datetime", "date"])
    x_col = _find_col(df, ["x", "coord_x", "pos_x", "longitude", "lon"])
    y_col = _find_col(df, ["y", "coord_y", "pos_y", "latitude", "lat"])

    rng = np.random.default_rng(seed)

    # Moisture: clamp to physically valid range used by model output.
    u = pd.to_numeric(df[moisture_col], errors="coerce").fillna(method="ffill").fillna(method="bfill")
    u = u.clip(0.0, 100.0).to_numpy(dtype=np.float32)

    # Temperature normalized to [0,1] over expected [15,40]C range.
    if temp_col is not None:
        temp = pd.to_numeric(df[temp_col], errors="coerce").fillna(25.0)
        T = _normalize(temp, 15.0, 40.0)
    else:
        T = np.full(len(df), 0.5, dtype=np.float32)

    # Time normalized [0,1].
    if time_col is not None:
        t_raw = pd.to_datetime(df[time_col], errors="coerce")
        if t_raw.notna().sum() >= 2:
            t_sec = (t_raw - t_raw.min()).dt.total_seconds().fillna(0.0)
            t = _normalize(t_sec, float(t_sec.min()), float(t_sec.max()))
        else:
            t = np.linspace(0.0, 1.0, len(df), dtype=np.float32)
    else:
        t = np.linspace(0.0, 1.0, len(df), dtype=np.float32)

    # Spatial fields normalized [0,1]. If absent, synthesize fixed pseudo-layout.
    if x_col is not None:
        x_raw = pd.to_numeric(df[x_col], errors="coerce").fillna(method="ffill").fillna(method="bfill")
        x = _normalize(x_raw, float(x_raw.min()), float(x_raw.max()))
    else:
        x = rng.uniform(0.0, 1.0, size=len(df)).astype(np.float32)

    if y_col is not None:
        y_raw = pd.to_numeric(df[y_col], errors="coerce").fillna(method="ffill").fillna(method="bfill")
        y = _normalize(y_raw, float(y_raw.min()), float(y_raw.max()))
    else:
        y = rng.uniform(0.0, 1.0, size=len(df)).astype(np.float32)

    return {
        "x": x.astype(np.float32),
        "y": y.astype(np.float32),
        "t": t.astype(np.float32),
        "T": T.astype(np.float32),
        "u": u.astype(np.float32),
    }
