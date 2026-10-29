"""Locate the COMSOL installation from config/user_env.yaml (spec §2)."""
from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
USER_ENV = ROOT / "config" / "user_env.yaml"


def user_env() -> dict:
    return yaml.safe_load(USER_ENV.read_text(encoding="utf-8"))


def _os_key() -> str:
    s = platform.system().lower()
    return "windows" if s.startswith("win") else "macos" if s == "darwin" else "linux"


def comsol_root() -> Path | None:
    """Install root (folder containing bin/), or None if not found."""
    env = user_env()["comsol"]
    cands = []
    if os.environ.get(env.get("env_var", "COMSOL63_PATH")):
        cands.append(os.environ[env["env_var"]])
    if env.get("install_path"):
        cands.append(env["install_path"])
    cands += env.get("search_paths", {}).get(_os_key(), [])
    for c in cands:
        p = Path(c)
        if (p / "bin").is_dir():
            return p
    exe = shutil.which("comsol")
    if exe:
        return Path(exe).resolve().parents[1]
    return None


def comsol_version() -> str:
    return str(user_env()["comsol"]["version"])


def describe() -> str:
    r = comsol_root()
    return f"COMSOL {comsol_version()} at {r}" if r else f"COMSOL {comsol_version()}: install not found"
