#!/usr/bin/env python3
"""Convert dataset/soil_moisture.csv to PINN NPZ format (x,y,t,T,u).

Saves output to backend/src/digital_twin/pinns/data/kaggle_data.npz
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path
from typing import List


def list_numeric_cols(cols: List[str]) -> List[str]:
    numeric = []
    for c in cols:
        try:
            float(c)
            numeric.append(c)
        except Exception:
            continue
    return numeric


def convert(csv_path: Path, out_dir: Path):
    df = pd.read_csv(csv_path)
    cols = list(df.columns)

    # Identify spatial columns (numeric names)
    spatial_cols = list_numeric_cols(cols)
    if not spatial_cols:
        raise RuntimeError('No numeric spatial columns found')

    # Parse datetime
    if 'datetime' in df.columns:
        times = pd.to_datetime(df['datetime'])
    else:
        # fallback: use index as time
        times = pd.to_datetime(df.index)

    t_seconds = (times - times.min()).dt.total_seconds().to_numpy(dtype=np.float32)
    if t_seconds.max() > 0:
        t_norm = t_seconds / float(t_seconds.max())
    else:
        t_norm = np.zeros_like(t_seconds)

    # Temperature
    if 'soil_temperature' in df.columns:
        T = df['soil_temperature'].to_numpy(dtype=np.float32)
    else:
        T = np.full(len(df), 25.0, dtype=np.float32)
    # normalize using assumed [15,40]
    T_norm = (T - 15.0) / 25.0
    T_norm = np.clip(T_norm, 0.0, 1.0).astype(np.float32)

    # Spatial x positions from column names (as numbers)
    xs_raw = np.array([float(c) for c in spatial_cols], dtype=np.float32)
    x_min, x_max = xs_raw.min(), xs_raw.max()
    if x_max > x_min:
        xs_norm = (xs_raw - x_min) / (x_max - x_min)
    else:
        xs_norm = np.zeros_like(xs_raw)

    # Build long-form arrays
    x_list = []
    y_list = []
    t_list = []
    T_list = []
    u_list = []

    for i, row in df.iterrows():
        t_i = float(t_norm[i])
        T_i = float(T_norm[i])
        for j, col in enumerate(spatial_cols):
            val = float(row[col])
            x_list.append(xs_norm[j])
            y_list.append(0.0)
            t_list.append(t_i)
            T_list.append(T_i)
            u_list.append(val)

    x = np.array(x_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.float32)
    t = np.array(t_list, dtype=np.float32)
    T = np.array(T_list, dtype=np.float32)
    u = np.array(u_list, dtype=np.float32)

    # If u looks like fraction [0,1], scale to percent
    if u.max() <= 2.0:
        u = u * 100.0

    u = np.clip(u, 0.0, 100.0)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / 'kaggle_data.npz'
    np.savez(out_path, x=x, y=y, t=t, T=T, u=u)

    print('Saved converted dataset to:', out_path)
    print('Samples:', len(x))
    return out_path


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Convert soil_moisture.csv to PINN NPZ')
    parser.add_argument('--csv', default='../../../../dataset/soil_moisture.csv', help='Path to CSV (relative to this script)')
    parser.add_argument('--out', default='.', help='Output directory (will create)')
    args = parser.parse_args()

    csv_path = Path(args.csv).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    convert(csv_path, out_dir)
