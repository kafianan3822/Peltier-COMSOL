# Instructions for the agent

This repository simulates junction (Peltier) cooling in a **germanium** n⁺-i-p⁺ diode with
COMSOL Multiphysics 6.3 (Semiconductor Module), driven from Python through MPh.

## Pipeline (run in this order, from the repository root)

1. `python -m pytest -q` : must pass before anything else (no COMSOL needed).
2. `python comsol/python/check_comsol.py` : confirms COMSOL and the licence are reachable.
3. `python reference/reference_model.py` then `python reference/cascade_calculator.py`.
4. `python comsol/python/build_model.py` : stages 1-8, writes `comsol/models/pin_peltier_base.mph`.
5. `python comsol/python/run_variants.py --set core` : V0 and V1.
6. `python postprocess/report.py` : checks C1-C9, figures, `results/summary.md`.
7. Only when C1-C5 and C7-C9 pass for the core set: `python comsol/python/run_variants.py --set full`,
   then `python postprocess/report.py` again.

Read `docs/USER_MANUAL.md` section 10 for the meaning of each error.

## Rules

- `config/params_base.yaml` is the single source of truth. After editing any file in `config/`, run
  `python comsol/python/write_params_txt.py` and `python comsol/python/sync_java_api_names.py`.
- **Do not change physical parameters, check windows or `report.plausibility_limit` to make a
  check pass.** Report the failure and stop. Parameter values and their justification are in
  `docs/GERMANIUM_PARAMETERS.md`.
- If a script stops with `ApiNameError`, the named COMSOL property or feature name is wrong.
  Look it up in `docs/VERIFY_API_NAMES.md`, put the corrected name in
  `config/api_names_override.yaml` (`KEY: "value"`), and rerun. Do not edit `api_names.py` for this.
- If `report.py` or `analyze.py` exits with code 2 (`BUG: net cooling >= 0.1 K`), stop and report.
  Do not continue to the full variant set.
- A COMSOL run can take minutes. Do not start two COMSOL processes at once (one licence seat).
- Never commit `comsol/models/*.mph`. Commit or push only when the user asks.
- At the end, report: which steps ran, the status of every check C1-C9, the V0/V1 numbers at
  0.4 V from `results/summary.md`, and anything that was skipped or failed.
