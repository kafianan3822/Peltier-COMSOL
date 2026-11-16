# PIN-diode junction cooling: COMSOL simulation package

A reproducible COMSOL Multiphysics 6.3 study of a forward-biased **germanium** n⁺-i-p⁺ diode
(2 µm | 1 mm | 2 µm, 1 mm²). It asks whether the bipolar Peltier effect at the junctions can
cool a "room" while the recombination heat is dumped in the intrinsic region. It implements
`CLAUDE_CODE_SPEC_PIN_Peltier_COMSOL.md`, which was written for silicon; the material is now
germanium. Every germanium value and its justification is in
[`docs/GERMANIUM_PARAMETERS.md`](docs/GERMANIUM_PARAMETERS.md). Deviations and interpretations are
listed in [`CHANGES.md`](CHANGES.md). To run the whole pipeline with an AI agent, see
[`docs/AGENT_SETUP.md`](docs/AGENT_SETUP.md).

**Physics caveat.** Junction cooling is real (J·E < 0 against the built-in field, plus the
contact Peltier heat). With an engineered central recombination zone the junction ends cool
below the sink, but only by **tens of milli-kelvin**: about 56 mK at 0.4 V in the reference
model, which includes carrier leakage into the contacts. Without the zone the room is heated.
Stacking modules does not fix this. Parallel modules multiply watts, not ΔT, and a series
cascade needs about 200 stages and about 10^95 × the electrical power for
10 K ([`results/cascade.md`](results/cascade.md)).

**New to COMSOL scripting? Start with the step-by-step [user manual](docs/USER_MANUAL.md).**

Current status: [`results/summary.md`](results/summary.md). The COMSOL columns stay PENDING
until the drivers have been run on a machine with a COMSOL licence.

---

## 1. Prerequisites

| Item | Needed for |
|---|---|
| COMSOL Multiphysics **6.3** with the **Semiconductor Module**. 1D Heat Transfer in Solids works with the base package; the Heat Transfer Module is licensed here too. | Drivers A and B |
| Python ≥ 3.11 with `pip install mph numpy scipy pandas matplotlib pyyaml pytest` | Driver A, reference model, post-processing, tests |
| Java: none extra. `comsol compile` brings its own JDK. A system `javac` is only used by the offline compile test. | Driver B |
| MATLAB LiveLink | not used (Driver C not requested) |

The environment answers of spec §2 are recorded in [`config/user_env.yaml`](config/user_env.yaml).
COMSOL is located from the `COMSOL63_PATH` environment variable, then `comsol.install_path` in that file, then
`C:\Program Files\COMSOL\COMSOL63\Multiphysics` (or the Linux/macOS standard folders).

```bat
set COMSOL63_PATH=C:\Program Files\COMSOL\COMSOL63\Multiphysics
```

The germanium material is the explicit table `material_fallback` in `config/params_base.yaml`. That is
the recommended setup, because the reference model uses the same numbers. Optionally you can save the
COMSOL library material (*Materials > Add Material from Library > Semiconductors > Ge - Germanium*, then
*File > Save As* `comsol/materials/Ge_library.mph`); the builders then copy it instead. The mobility is
always the user-defined doping-dependent model M2: the Arora, Slotboom and Fletcher models are
silicon-calibrated and are not used.

## 2. Quick start (Driver A: Python + MPh)

```bash
python reference/reference_model.py
```
Runs the COMSOL-independent reference model for V0, V1, V5 and V6 in about 2 min, and writes `results/reference/`.

```bash
python reference/cascade_calculator.py
```
Writes `results/cascade.md`.

```bash
python comsol/python/build_model.py
```
Runs stages 1-8 and writes `comsol/models/stage1.mph` … `stage8.mph` and `pin_peltier_base.mph`.

```bash
python comsol/python/run_variants.py --set core
```
Solves V0 and V1 and writes `results/V0/`, `results/V1/`. Use `--set full` for the whole matrix (49 runs).

```bash
python postprocess/report.py
```
Runs the checks (C1-C9) and the figures, and writes `results/summary.md`.

Useful options:

- `build_model.py --until 4` stops after a stage.
- `build_model.py --dry-run` and `run_variants.py --dry-run` work without COMSOL.
- `run_variants.py --ids V4,V3a` runs selected variants. A parent id such as `V5` expands to all of its runs.

Tests (no COMSOL needed):

```bash
python -m pytest -q
```

## 3. Java-only path (Driver B)

> **Out of date.** Driver B lacks the COMSOL 6.3 fixes and the contact-recombination heat
> (CHANGES.md G15). Use Driver A until it is brought up to date.

Windows:

```bat
cd comsol\java
build_and_run.bat build
build_and_run.bat run core
build_and_run.bat all full
```

Linux / macOS:

```bash
cd comsol/java
./build_and_run.sh all core
```

`build` runs `comsolcompile BuildPinPeltier.java` and `comsolbatch -inputfile BuildPinPeltier.class -outputfile ..\models\pin_peltier_base.mph`.
`run` does the same for `RunVariants.java` and writes CSVs to `results/<variant>/`.
`all` runs both; the second argument is the variant set.

Driver B reads `comsol/params.txt`, `comsol/java/model_config.txt` and `comsol/java/variants_flat.txt`. All three are
generated from the YAML files, so regenerate them after editing `config/*.yaml`:

```bash
python comsol/python/write_params_txt.py
```

```bash
python comsol/python/sync_java_api_names.py
```

The first refreshes the parameter and variant files. The second refreshes the API_NAMES block of the Java files and the verification doc.

Python is then only needed for the post-processing (`postprocess/report.py`).

## 4. Verifying the ⚠VERIFY API names

COMSOL feature-type strings, property names and variable names that could not be confirmed without COMSOL
are collected in one constants block, [`comsol/python/api_names.py`](comsol/python/api_names.py), with
generated copies in the Java files. [`docs/VERIFY_API_NAMES.md`](docs/VERIFY_API_NAMES.md) lists each one with
the GUI action that creates it and where to read the true name in *File > Save As > Model File for Java*.

Corrections go into `config/api_names_override.yaml` (`KEY: "value"`); no code edits are needed. When COMSOL
rejects a name, the build stops with `ApiNameError` naming the constant. Variable names (`U_TOT`, `J_X`,
`I_TERMINAL`, ...) are probed at run time and the working candidate is logged.

A manual GUI build is described in [`docs/GUI_build_steps.md`](docs/GUI_build_steps.md).

## 5. Expected runtime

| Step | Time |
|---|---|
| Reference model, one variant (≈ 90 continuation steps of `solve_bvp`) | ≈ 5 s |
| Reference model, default set (V0, V1, 12 × V5, 12 × V6) | ≈ 2 min |
| COMSOL build, stages 1-8 (1D, about 2000 elements) | ≈ 1-3 min |
| COMSOL, one variant with Configs A + B (41 + 33 × 17 + 41 bias points) | ≈ 1-5 min; the Study 2 parametric sweep dominates |
| COMSOL, full matrix (49 runs) | ≈ 1-3 h |
| `report.py` | ≈ 20 s |

## 6. Troubleshooting

| Problem | Fix |
|---|---|
| Equilibrium failure | Raise `l_dec` to 0.3 µm or ramp the doping |
| Forward sweep stalls | Use a VF step of 0.01 V. The builder already tries the segregated solver and then a halved step automatically |
| Wrong-sign Q_room | Check the boundary-flux sign convention (`ht.tfluxX` is +x; Q_room = Ac[qx(0) - qx(L) + \|J\|(Π_nc+Π_pc)], positive = room cooled) |
| Missing variable names | See `docs/VERIFY_API_NAMES.md`; set `config/api_names_override.yaml` |
| `ApiNameError ...` | The named constant is wrong for your COMSOL version: verify and override it (Section 4) |
| `BUG: net cooling >= 0.1 K` from `analyze.py`/`report.py` | A model or sign error, not a result (spec §0 rule 6). Check the hs1 expression and the boundary sinks |
| `MPh` cannot find COMSOL | Set `COMSOL63_PATH`; on Windows COMSOL must be installed with the Java API (default) |

## 7. Repository layout

```
config/        params_base.yaml (single source of truth), variants.yaml, user_env.yaml
comsol/        params.txt (generated); python/ (Driver A); java/ (Driver B); models/ (generated .mph)
reference/     reference_model.py (§11), cascade_calculator.py (§12)
postprocess/   analyze.py (§8, §10), plots.py (§8.4), report.py (§8.5)
common/        shared parameter evaluator and CSV helpers
tests/         pytest suite, COMSOL test double, Java API stubs
results/       CSVs, figures/, summary.md, cascade.md (generated)
docs/          GUI_build_steps.md, VERIFY_API_NAMES.md (generated)
```

## 8. References

1. COMSOL Semiconductor Module User's Guide, "Nonisothermal Models" (simplified heat source; `semi.Q_tot`). https://doc.comsol.com/6.4/doc/com.comsol.help.semicond/semicond_ug_modeling.5.18.html
2. COMSOL Application Library, *Thermal Analysis of a Bipolar Transistor* (Semiconductor_Module/Transistors/bipolar_transistor_thermal).
3. G. K. Wachutka, "Rigorous thermodynamic treatment of heat generation and conduction in semiconductor device modeling," *IEEE Trans. CAD* 9(11), 1141-1149 (1990).
4. K. P. Pipe, R. J. Ram, A. Shakouri, "Bias-dependent Peltier coefficient and internal cooling in bipolar devices," *Phys. Rev. B* 66, 125316 (2002).
5. Ioffe Institute, *New Semiconductor Materials: Ge - Germanium*. https://www.ioffe.ru/SVA/NSM/Semicond/Ge/
6. S. M. Sze, K. K. Ng, *Physics of Semiconductor Devices*, 3rd ed., Wiley (2007), Appendix G.
7. C. Hilsum, "Simple empirical relationship between mobility and carrier concentration," *Electron. Lett.* 10, 259 (1974).
8. T. Sadi, I. Radevici, J. Oksanen, "Thermophotonic cooling with light-emitting diodes," *Nature Photonics* 14, 205 (2020).
