"""CSV writer/reader with a '#'-comment header (spec §6: every file begins with
a header comment containing the variant parameters and COMSOL version)."""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

import numpy as np
import pandas as pd


def write_csv(path: Path, df: pd.DataFrame, header: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(f"# written: {_dt.datetime.now().isoformat(timespec='seconds')}\n")
        for k, v in header.items():
            f.write(f"# {k}: {v}\n")
        df.to_csv(f, index=False, float_format="%.10g")


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, comment="#")


def read_header(path: Path) -> dict:
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("#"):
                break
            if ":" in line:
                k, v = line[1:].split(":", 1)
                out[k.strip()] = v.strip()
    return out


def nan_array(n: int) -> np.ndarray:
    return np.full(n, np.nan)
