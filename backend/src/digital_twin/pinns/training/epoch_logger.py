#!/usr/bin/env python3
"""Simple epoch logger that appends training progress to a markdown file.

Usage:
    from epoch_logger import log_epoch
    log_epoch(checkpoint_dir, epoch, losses_dict)

CLI:
    python epoch_logger.py --dir ./checkpoints --epoch 1 --losses '{"total":123.4,"data":100.0}'
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict


def format_line(epoch: int, losses: Dict[str, float]) -> str:
    ts = datetime.utcnow().isoformat() + 'Z'
    parts = [f"**{ts}**", f"Epoch **{epoch}**"]
    parts += [f"{k}: {v:.6f}" for k, v in losses.items()]
    return " - ".join(parts)


def log_epoch(checkpoint_dir: str | Path, epoch: int, losses: Dict[str, float]) -> None:
    checkpoint_dir = Path(checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    log_path = checkpoint_dir / "training_log.md"

    line = format_line(epoch, losses)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _cli():
    parser = argparse.ArgumentParser(description="Append epoch losses to training_log.md")
    parser.add_argument("--dir", required=True, help="Checkpoint / log directory")
    parser.add_argument("--epoch", type=int, required=True)
    parser.add_argument("--losses", required=True, help="JSON string of loss dict")

    args = parser.parse_args()
    losses = json.loads(args.losses)
    log_epoch(args.dir, args.epoch, losses)


if __name__ == "__main__":
    _cli()
