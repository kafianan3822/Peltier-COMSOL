"""Check that Python (MPh) can find and start COMSOL.  No quoting needed:

    python comsol/python/check_comsol.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from env import comsol_root, comsol_version  # noqa: E402


def main() -> int:
    print(f"Python {sys.version.split()[0]}")
    root = comsol_root()
    print(f"COMSOL install folder found by the scripts: {root or 'NOT FOUND'}")
    try:
        import mph
    except ImportError:
        print("MPh is not installed. Activate the environment (.venv\\Scripts\\activate) and run: pip install mph")
        return 1
    print(f"MPh {mph.__version__}; COMSOL installations MPh can see:")
    try:
        for b in mph.discovery.find_backends():
            print(f"  - {b['name']}  ({b['root']})")
    except Exception as exc:  # discovery problems are reported, not fatal
        print(f"  (could not list installations: {exc})")
    print(f"Starting COMSOL {comsol_version()} (10-60 s, longer the first time)...")
    t0 = time.time()
    try:
        client = mph.start(cores=1, version=comsol_version())
    except Exception as exc:
        print(f"FAILED to start COMSOL: {exc}")
        print("See docs/USER_MANUAL.md, section 14, 'MPh cannot start COMSOL'.")
        return 1
    print(f"OK: COMSOL {client.version} started in {time.time() - t0:.0f} s. Python can talk to COMSOL.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
