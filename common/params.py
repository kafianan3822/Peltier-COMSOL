"""Load config/params_base.yaml and config/variants.yaml and evaluate the
COMSOL-syntax expressions to SI floats (no COMSOL needed).

Only the unit strings that actually occur in the config files are supported;
an unknown unit raises a KeyError naming it, so nothing is guessed silently.
"""
from __future__ import annotations

import itertools
import math
import re
from copy import deepcopy
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"

# CODATA 2018 exact values (COMSOL built-ins k_B_const, e_const)
K_B = 1.380649e-23        # J/K
Q_E = 1.602176634e-19     # C

# unit string -> SI factor
UNITS = {
    "K": 1.0, "V": 1.0, "1": 1.0, "m": 1.0,
    "um": 1e-6, "mm": 1e-3, "cm": 1e-2,
    "mm^2": 1e-6,
    "ms": 1e-3, "us": 1e-6, "s": 1.0,
    "1/cm^3": 1e6, "1/m^3": 1.0, "1/m": 1.0,
    "cm^6/s": 1e-12,
    "W/(m*K)": 1.0, "W/(m^2*K)": 1.0,
    "kg/m^3": 1.0, "J/(kg*K)": 1.0,
    "cm^2/(V*s)": 1e-4,
    "m^2*K/W": 1.0, "W/m^2": 1.0, "W": 1.0,
}

_UNIT_RE = re.compile(r"\[([^\]]+)\]")


def _replace_units(expr: str) -> str:
    def sub(m):
        u = m.group(1).strip()
        if u not in UNITS:
            raise KeyError(f"Unit '[{u}]' in expression '{expr}' is not in common.params.UNITS")
        return f"*({UNITS[u]!r})"
    return _UNIT_RE.sub(sub, expr)


def eval_expr(expr: str, env: dict) -> float:
    """Evaluate a COMSOL-style scalar expression with SI units."""
    py = _replace_units(str(expr)).replace("^", "**")
    ns = {"__builtins__": {}, "log": math.log, "exp": math.exp, "sqrt": math.sqrt,
          "abs": abs, "k_B_const": K_B, "e_const": Q_E, "pi": math.pi}
    ns.update(env)
    return float(eval(py, ns))  # noqa: S307 -- trusted local config only


def load_base(path: Path | None = None) -> dict:
    with open(path or CONFIG / "params_base.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_variants(path: Path | None = None) -> dict:
    with open(path or CONFIG / "variants.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def param_exprs(base: dict | None = None) -> dict[str, tuple[str, str]]:
    base = base or load_base()
    return {k: (str(v[0]), str(v[1])) for k, v in base["parameters"].items()}


def evaluate_params(overrides: dict[str, str] | None = None, base: dict | None = None) -> dict[str, float]:
    """Evaluate all §5.1 parameters to SI floats, applying COMSOL-expression overrides."""
    exprs = {k: e for k, (e, _) in param_exprs(base).items()}
    for k, v in (overrides or {}).items():
        if k not in exprs:
            raise KeyError(f"Override of unknown parameter '{k}'")
        exprs[k] = str(v)
    env: dict[str, float] = {}
    for k, e in exprs.items():
        env[k] = eval_expr(e, env)
    return env


def parse_range(s: str) -> np.ndarray:
    """COMSOL range(start, step, stop) -> numpy array (inclusive stop)."""
    m = re.fullmatch(r"\s*range\(([^,]+),([^,]+),([^,]+)\)\s*", s)
    if not m:
        raise ValueError(f"not a range(): {s}")
    a, d, b = (float(x) for x in m.groups())
    n = int(round((b - a) / d)) + 1
    return np.round(a + d * np.arange(n), 12)


# ---------------------------------------------------------------- variants
def expand_variants(set_name: str = "core", ids: list[str] | None = None) -> list[dict]:
    """Return fully-resolved run dicts for a variant set (or explicit ids).

    Each run dict has: id, parent, purpose, params (dict of expressions),
    stats, bgn, mobility, fletcher, qsrc, configs, flag.
    """
    cfg = load_variants()
    ids = ids or cfg["sets"][set_name]
    runs = []
    for vid in ids:
        v = cfg["variants"][vid]
        merged = deepcopy(cfg["defaults"])
        merged["params"] = dict(merged.get("params", {}))
        merged["params"].update(v.get("params", {}))
        for key in ("stats", "bgn", "mobility", "fletcher", "qsrc", "configs"):
            if key in v:
                merged[key] = v[key]
        merged["purpose"] = v.get("purpose", "")
        merged["flag"] = v.get("flag", "")
        merged["parent"] = vid
        sweep = v.get("sweep")
        if not sweep:
            runs.append({"id": vid, **merged})
            continue
        names = list(sweep)
        for combo in itertools.product(*(sweep[n] for n in names)):
            r = deepcopy(merged)
            tag = "_".join(f"{n}={_slug(val)}" for n, val in zip(names, combo))
            r["id"] = f"{vid}_{tag}"
            r["params"].update(dict(zip(names, combo)))
            r["sweep_values"] = dict(zip(names, combo))
            runs.append(r)
    return runs


def _slug(expr: str) -> str:
    return re.sub(r"[^0-9A-Za-z.\-]+", "", str(expr).replace("[", "").replace("]", "").replace("^", "").replace("/", "per"))
