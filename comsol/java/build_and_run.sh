#!/usr/bin/env bash
# Driver B wrapper (Linux/macOS).  Usage: ./build_and_run.sh [build|run|all] [core|full]
# COMSOL is located from $COMSOL63_PATH, then install_path in config/user_env.yaml,
# then the standard COMSOL 6.3 folders, then `comsol` on PATH.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
export PIN_PELTIER_ROOT="$(cd "$HERE/../.." && pwd)"
MODE="${1:-all}"
export PIN_SET="${2:-core}"

CROOT="${COMSOL63_PATH:-}"
if [[ -z "$CROOT" ]]; then
  CFG=$(grep -E '^  install_path:' "$PIN_PELTIER_ROOT/config/user_env.yaml" | sed -E "s/^  install_path:[[:space:]]*//; s/['\"]//g")
  [[ -n "$CFG" && "$CFG" != "null" ]] && CROOT="$CFG"
fi
for c in /usr/local/comsol63/multiphysics /opt/comsol63/multiphysics /Applications/COMSOL63/Multiphysics; do
  [[ -z "$CROOT" && -d "$c/bin" ]] && CROOT="$c"
done
if [[ -n "$CROOT" ]]; then COMSOL="$CROOT/bin/comsol"; else COMSOL="$(command -v comsol || true)"; fi
if [[ -z "$COMSOL" || ! -x "$COMSOL" ]]; then
  echo "[pin_peltier] COMSOL 6.3 not found. Set COMSOL63_PATH or install_path in config/user_env.yaml." >&2
  exit 1
fi
echo "[pin_peltier] COMSOL: $COMSOL"
mkdir -p "$PIN_PELTIER_ROOT/comsol/models" "$PIN_PELTIER_ROOT/results"
cd "$HERE"
if [[ "$MODE" != "run" ]]; then
  "$COMSOL" compile BuildPinPeltier.java
  "$COMSOL" batch -inputfile BuildPinPeltier.class \
      -outputfile "$PIN_PELTIER_ROOT/comsol/models/pin_peltier_base.mph" \
      -batchlog "$PIN_PELTIER_ROOT/comsol/models/build_batch.log"
fi
if [[ "$MODE" != "build" ]]; then
  "$COMSOL" compile RunVariants.java
  "$COMSOL" batch -inputfile RunVariants.class -nosave -batchlog "$PIN_PELTIER_ROOT/results/run_batch.log"
fi
echo "[pin_peltier] done."
