# Step-by-step user manual: running the PIN-diode cooling simulations

This manual is for someone who has **never run a COMSOL script or a Python program before**.
Follow the steps in order. Each step says what to type, what you should see, and what to do if
something goes wrong. Some steps you only need to do once; they are marked **(once)**.

Your setup (from `config/user_env.yaml`): **Windows**, **COMSOL 6.3** with the Semiconductor and
Heat Transfer modules, **Python 3.11 or newer**.

---

## Contents

0. [The big picture: what you are going to do](#0-the-big-picture)
1. [Get the project files onto your computer (once)](#1-get-the-project-files-once)
2. [Install Python and the packages (once)](#2-install-python-and-the-packages-once)
3. [Tell the scripts where COMSOL is (once)](#3-tell-the-scripts-where-comsol-is-once)
4. [Warm-up without COMSOL: tests and the reference model](#4-warm-up-without-comsol)
5. [Save the silicon library material (once, recommended)](#5-save-the-silicon-library-material-once-recommended)
6. [Build the COMSOL model stage by stage](#6-build-the-comsol-model-stage-by-stage)
7. [When a stage fails: fixing a COMSOL name](#7-when-a-stage-fails-fixing-a-comsol-name)
8. [Look at the model in the COMSOL window](#8-look-at-the-model-in-the-comsol-window)
9. [Run the first two simulations (V0 and V1)](#9-run-the-first-two-simulations-v0-and-v1)
10. [Make the report and the figures](#10-make-the-report-and-the-figures)
11. [Read and judge your results](#11-read-and-judge-your-results)
12. [Run the rest of the variant matrix](#12-run-the-rest-of-the-variant-matrix)
13. [Alternative route: Java only, no Python (Driver B)](#13-alternative-route-java-only-driver-b)
14. [Troubleshooting](#14-troubleshooting)
15. [Glossary](#15-glossary)
16. [One-page checklist](#16-one-page-checklist)

---

## 0. The big picture

The project contains **two independent ways** of computing the same physics:

| Part | Needs COMSOL? | What it does |
|---|---|---|
| **Reference model** (`reference/`) | No | A fast, simplified Python model. It has already been run; its results are in `results/reference/`. You use it as a yardstick. |
| **COMSOL model** (`comsol/`) | Yes | The full drift-diffusion + heat model. A script *builds* it for you, node by node, then *solves* it for each "variant". |

The work flow is:

```
 build_model.py  ──►  comsol/models/pin_peltier_base.mph   (the model file)
        │
 run_variants.py ──►  results/V0/*.csv, results/V1/*.csv   (numbers)
        │
 report.py       ──►  results/summary.md + results/figures/  (tables, checks, plots)
```

You run three commands, in that order. Everything else in this manual is preparation and
explanation.

> **Important expectation.** Several COMSOL internal names in the scripts could not be checked
> without COMSOL (they are marked ⚠VERIFY). It is **normal** that the first build stops once or
> a few times with a clear message such as `COMSOL rejected API name SEMI_AREA_PROP`. Section 7
> shows you how to fix this in a few minutes, without programming. Expect to spend 30-90 minutes
> on your first full build; later builds take 1-3 minutes.

---

## 1. Get the project files (once)

You need the files of the branch `claude/amazing-wright-8jucjb` of the GitHub repository
`kafianan3822/Peltier-COMSOL`.

**Option A: download a ZIP (easiest)**

1. Open the repository page on GitHub in your browser.
2. Use the branch selector (top left, usually says `main`) and choose **`claude/amazing-wright-8jucjb`**.
3. Click the green **Code** button > **Download ZIP**.
4. Unzip it to a short path **without spaces**, for example `C:\pin_peltier`.
   After unzipping, the folder `C:\pin_peltier` should directly contain `README.md`, `config`,
   `comsol`, `reference`, and so on. If you see one more folder level (for example
   `C:\pin_peltier\Peltier-COMSOL-claude-amazing-wright-8jucjb\`), move its contents up one level or
   just use that inner folder as your project folder.

**Option B: with Git** (if you have Git for Windows installed)

```bat
git clone -b claude/amazing-wright-8jucjb https://github.com/kafianan3822/Peltier-COMSOL.git C:\pin_peltier
```

In the rest of this manual, **project folder** means `C:\pin_peltier` (or wherever you put it).

---

## 2. Install Python and the packages (once)

### 2.1 Open a Command Prompt in the project folder

1. Open File Explorer and go to `C:\pin_peltier`.
2. Click into the address bar at the top, type `cmd`, press **Enter**.
   A black window opens whose prompt ends with `C:\pin_peltier>`. This is the **Command Prompt**.
   All commands in this manual are typed there, followed by **Enter**.

### 2.2 Install Python

1. Check whether Python is already there:
   ```bat
   python --version
   ```
   If it prints `Python 3.11.x` or higher (3.12, 3.13 are fine), skip to 2.3.
2. Otherwise download Python from https://www.python.org/downloads/windows/ (any 3.11 or newer
   version).
3. In the installer, **tick "Add python.exe to PATH"** at the bottom of the first screen, then
   click *Install Now*.
4. **Close the Command Prompt and open a new one** (step 2.1), then run `python --version` again.

### 2.3 Create a private Python environment and install the packages

A "virtual environment" keeps the packages for this project separate from everything else.

```bat
python -m venv .venv
```

```bat
.venv\Scripts\activate
```

The prompt now starts with `(.venv)`. **Every time you open a new Command Prompt for this
project, run `.venv\Scripts\activate` again.**

```bat
python -m pip install --upgrade pip
```

```bat
pip install mph numpy scipy pandas matplotlib pyyaml pytest
```

This takes 1-3 minutes. Packages: `mph` lets Python control COMSOL; the others do numerics, plots
and tests.

---

## 3. Tell the scripts where COMSOL is (once)

1. Find your COMSOL installation folder. The default for 6.3 is
   `C:\Program Files\COMSOL\COMSOL63\Multiphysics`. It must contain a `bin` folder.
2. If yours is in the default place, the scripts find it automatically. Otherwise, or to be safe,
   store the path in an environment variable:
   ```bat
   setx COMSOL63_PATH "C:\Program Files\COMSOL\COMSOL63\Multiphysics"
   ```
   `setx` only affects **new** windows: close the Command Prompt, open a new one (step 2.1) and
   activate the environment again (`.venv\Scripts\activate`).
3. Make sure COMSOL itself starts and your licence works: open COMSOL 6.3 from the Start menu
   once, then close it.
4. Test that Python can talk to COMSOL:
   ```bat
   python -c "import mph; c = mph.start(cores=1); print('COMSOL', c.version)"
   ```
   After 10-60 seconds it should print `COMSOL 6.3...`. If it fails, see
   [Troubleshooting](#14-troubleshooting), "MPh cannot start COMSOL".

---

## 4. Warm-up without COMSOL

These steps prove that Python and the project files work before COMSOL is involved.

### 4.1 Run the tests

```bat
python -m pytest -q
```

Expected: a row of dots and `43 passed`. If Java's `javac` is not installed you will see
`42 passed, 1 skipped` instead; that is fine (the skipped test only compiles the Java files).

### 4.2 (Optional) Re-run the reference model

The reference results are already in `results/reference/`. To regenerate them:

```bat
python reference/reference_model.py
```

It takes about 2 minutes and prints one line per run. The two lines that matter:

```
V0   J(0.7V)= 0.0562 A/cm2  Q_room(dT=0)= -0.0582 mW  dTmax= -0.098 mK  T_end-T_room(B)=  0.098 mK
V1   J(0.7V)= 0.1173 A/cm2  Q_room(dT=0)=  0.5581 mW  dTmax=  0.943 mK  T_end-T_room(B)= -0.943 mK
```

Meaning: with uniform lifetime (V0) the junction ends get **warmer**; with the engineered
recombination zone (V1) they get **about 1 mK colder**. Keep these numbers in mind; your COMSOL
results should be of the same order (within a factor of 2, check C9).

### 4.3 Dry run of the COMSOL scripts

```bat
python comsol/python/build_model.py --dry-run
```

```bat
python comsol/python/run_variants.py --set core --dry-run
```

These print the plan without starting COMSOL. If they run without an error, your Python setup is
complete.

---

## 5. Save the silicon library material (once, recommended)

Without this file the scripts use a simplified silicon. With it, you get the COMSOL library
silicon, the Arora mobility model (the spec's default) and you can run variants V2a/V2b.

1. Open COMSOL 6.3.
2. **Model Wizard** > **1D** > select no physics, click **Done** (or *Blank Model*, then right-click
   *Model > Add Component > 1D*). The component must be called **Component 1** (`comp1`).
3. In the Model Builder tree right-click **Materials** > **Add Material from Library**.
4. In the window that opens: **Semiconductors** > **Si - Silicon** > click **Add to Component**. It
   appears as *Si - Silicon (mat1)*. The tag must be **mat1** (the default for the first material).
5. **File > Save As** > go to your project folder > `comsol\materials\` > file name
   **`Si_library.mph`** > Save.
6. Close the file.

To check the tags: in the Model Builder toolbar click the eye icon (*Model Builder Node Label*)
> *Show Name and Tag*, or look at the node's Settings.

---

## 6. Build the COMSOL model stage by stage

The builder creates the model in **8 stages**. After every stage it saves
`comsol\models\stageN.mph` and runs a small automatic check ("smoke test"). Run it stage by stage
the first time, so that if something fails you know exactly where.

Each command below starts from an empty model and builds up to the given stage, so a run with
`--until 3` repeats stages 1 and 2. That is intended.

### 6.1 Stage 1: parameters, geometry, mesh

```bat
python comsol/python/build_model.py --until 1
```

Good signs in the output:

```
geometry: 4 domains, 5 points
mesh dis_iL: h(junction)=... m, h(centre)=... m
mesh: 400+600+600+400 elements (mesh_factor=1)
stage 1 OK
```

### 6.2 Stage 2: material

```bat
python comsol/python/build_model.py --until 2
```

Look for:

```
material: copied library material 'Si - Silicon'      (or: explicit fallback properties)
Pi_nc = 0.079.. V, Pi_pc = 0.081.. V
```

If you did section 5 and it still says *fallback*, the file `comsol\materials\Si_library.mph` was not
found: check the name and folder.

### 6.3 Stage 3: semiconductor physics and doping (first solve)

```bat
python comsol/python/build_model.py --until 3
```

Look for `net doping range: -1e+25 .. 1e+25 1/m^3` (that is -1e19 ... +1e19 cm⁻³) and `stage 3 OK`.

### 6.4 Stage 4: recombination, contacts, current-voltage sweep

```bat
python comsol/python/build_model.py --until 4
```

Look for lines `API name ... (verified by evaluation)` and

```
J(0.7 V) = 0.0xxx A/cm^2 (spec V0 window 0.02-1)
consistency |I_TERMINAL| / (Ac*|J_X|) = 1.0000 .. 1.0000
```

### 6.5 Stage 5: heat transfer

```bat
python comsol/python/build_model.py --until 5
```

Look for `max|T(VF=0) - T_room| = 0 K` (or a tiny number like `1e-12`).

### 6.6 Stages 6 to 8: studies, exports, final model

```bat
python comsol/python/build_model.py
```

(No `--until` means all 8 stages.) At the end you should see

```
saved ...\comsol\models\pin_peltier_base.mph
stage 8 OK
```

and the folder `comsol\models\` contains `stage1.mph` ... `stage8.mph`, `pin_peltier_base.mph`,
`build_info.json` and `build.log`. **`build.log` keeps the full output**, which is useful if the
window scrolled too fast.

If any stage stops with an error, go to section 7, fix it, and re-run the **same** command.

---

## 7. When a stage fails: fixing a COMSOL name

### 7.1 What the error looks like

```
ERROR COMSOL rejected API name SEMI_AREA_PROP = 'A'. GUI: semi > Settings > Cross-Sectional
Area > A (value Ac). Verify via File > Save As > Model File for Java and search for:
physics("semi").prop("d").set("<HERE>", "Ac"); then set it in config/api_names_override.yaml.
See docs/VERIFY_API_NAMES.md#semi_area_prop.
COMSOL said: Unknown property ...
```

It tells you **which name** (`SEMI_AREA_PROP`), **the value the script tried** (`'A'`), **where in
the GUI** that setting lives, and **what to search for**.

### 7.2 Find the correct name in the GUI (about 5 minutes)

1. Open COMSOL and open the last saved stage, for example `comsol\models\stage2.mph` if stage 3
   failed (the failing stage did not get saved).
2. In the Model Builder, make the **same setting by hand**, following the "GUI" hint in the error
   (here: click *Semiconductor (semi)* and type `Ac` into *Cross-Sectional Area*). If the node
   does not exist yet, create it (right-click the interface > the node name). The full click list
   for every stage is in `docs/GUI_build_steps.md`.
3. **File > Save As**, set *Save as type* to **Model File for Java (\*.java)**, save it anywhere
   (for example on the Desktop as `check.java`).
4. Open `check.java` with Notepad. Press **Ctrl+F** and search for a distinctive word from the hint,
   for example `"Ac"`. You will find a line such as

   ```java
   model.component("comp1").physics("semi").prop("CrossSection").set("A", "Ac");
   ```

5. Compare with the hint `physics("semi").prop("d").set("<HERE>", "Ac")`. In this example, the
   real names are `CrossSection` (the group) and `A` (the property).

Faster alternative: in COMSOL, *Developer* tab > **Record Method**, make the setting, **Stop
Recording**; the recorded Java lines appear in the Application Builder's method editor.

### 7.3 Tell the scripts the correct name

1. In the project folder, open `config\` and create a new text file called
   **`api_names_override.yaml`** (with Notepad: *Save as type: All files*, so it does not become
   `.yaml.txt`).
2. Write one line per corrected name, using the constant name from the error message:

   ```yaml
   SEMI_AREA_GROUP: "CrossSection"
   SEMI_AREA_PROP: "A"
   ```

3. Save. **Python reads this file automatically**; nothing else to do for Driver A. (For the Java
   route also run `python comsol/python/sync_java_api_names.py`.)
4. Re-run the build command that failed.

Repeat until all 8 stages pass. Every fix is permanent: you will not see the same error again.

### 7.4 Names that fix themselves

Result variable names (`semi.U_tot`, `semi.JX`, `semi.I0_2`, ...) are **tried automatically**
from a list of candidates. A message like

```
WARNING API name U_TOT: 'semi.U_tot' not found, using 'semi.R_tot'
```

is not an error; the script picked a working alternative. Only if *none* works does the build
stop, saying `none of the candidates [...] evaluates`; then find the variable in the GUI
(*Results* > any plot > *Replace Expression* > browse the Semiconductor list; hovering shows its
name) and add it to `api_names_override.yaml` the same way.

### 7.5 Errors that are not names

| Message | Meaning | What to do |
|---|---|---|
| `stage 1 smoke test failed: expected 4 domains / 5 points` | Geometry points wrong | Check `Wn`, `Wi`, `Wp` in `config/params_base.yaml` are unchanged |
| `stage 3 smoke test failed: net doping ...` | Doping profile set wrong | Open `stage2.mph`, add one Analytic Doping Model by hand, compare names (section 7.2) |
| `stage 4 smoke test failed: J(0.7 V) = ... not in 0.02-1` | Current far from expectation | Usually a lifetime or recombination setting that did not apply. Open `stage3.mph`, add *Trap-Assisted Recombination* by hand and compare the names (section 7.2) |
| `failed (...) -> fallback 1: segregated solver` | Solver struggled; script retries | Nothing, unless all fallbacks fail; then see section 14 |

---

## 8. Look at the model in the COMSOL window

Open `comsol\models\pin_peltier_base.mph` in COMSOL and check, as a sanity check:

1. **Global Definitions > Parameters 1**: 32 parameters; `Pi_nc` ≈ 0.079 V, `Pi_pc` ≈ 0.081 V.
2. **Semiconductor > Semiconductor Material Model 1 > Model Input**: Temperature = *User defined*,
   `T0`. This is the **one-way coupling**: the electrical model never sees the computed temperature.
3. **Heat Transfer in Solids**: `hs1` (Q = `semi.Q_tot`), `bhs_n`, `bhs_p` (contact Peltier
   sinks), `temp_ends`, `temp_sinkA`, `temp_sinkB`, `hs_lat`.
4. **Mesh 1**: click *Build All*; zoom in near x = 2 µm and x = 1.002 mm: elements are tiny there
   and grow towards the centre.
5. **Study 1 ... Study 4**: four studies. In each Stationary step, *Physics and Variables
   Selection* shows the disabled thermal nodes of the other configurations.

You may run *Study 1* by hand (*Compute*) to look at plots; you do not have to.

---

## 9. Run the first two simulations (V0 and V1)

```bat
python comsol/python/run_variants.py --set core
```

What happens: for **V0** (device as drawn) and **V1** (with the central recombination zone) the
script loads the base model, sets the variant, solves Study 1, Study 3 (Config B), Study 2
(Config A with the `dT_sink` sweep) and a reverse-bias run, and writes CSV files.

Time: roughly 2-10 minutes per variant (Study 2 is the longest). Progress lines look like
`solved std_room in 85.3 s` and `variant V0 exported to ...\results\V0`.

Result files (one folder per variant, e.g. `results\V0\`):

| File | Content |
|---|---|
| `global_vs_VF.csv` | One row per bias VF: current, heat integrals, junction cooling, room heat balance, energy-balance ratio |
| `profiles_VF0.7.csv` (and 0, 0.6, 0.75, 0.8) | Position-resolved bands, carrier densities, heat source, temperature |
| `room_sweep.csv` | Room heat `Q_room` for every VF and every sink temperature offset |
| `float_vs_VF.csv` | End temperatures in Config B |
| `reverse_bias_*.csv` | Run at VF = -0.5 V (check C8) |

The CSV files open in Excel. Lines starting with `#` at the top describe the run (variant, COMSOL
version, units); Excel shows them as text in the first rows.

The log of this step is `results\run_variants.log`.

---

## 10. Make the report and the figures

```bat
python postprocess/report.py
```

This (1) computes ΔT_max, COP and the energy balance, (2) runs the automatic checks C1-C9,
(3) draws all figures, and (4) writes **`results\summary.md`**.

How to view it:

- **Figures**: open `results\figures\` in File Explorer; the `.png` files open with any image
  viewer, the `.pdf` files are for publication (300 dpi, vector).
- **summary.md**: a Markdown file. It is readable in Notepad, but nicer in
  **Visual Studio Code** (free; open the file, press **Ctrl+Shift+V** for the preview) or by
  uploading it to GitHub, which displays it formatted.

If `report.py` ends with **`BUG: net cooling >= 0.1 K`**, stop and read section 11.3.

---

## 11. Read and judge your results

### 11.1 The numbers in the summary table

| Column | What it means | Reference-model value (V0 / V1 at 0.7 V) |
|---|---|---|
| `dT_max @0.7 V` | How much warmer than the room the heat sink may be while the room is still cooled (Config A) | none (room heated) / 0.94 mK |
| `Q_room(dT=0)` | Heat pulled out of the room when sink = room temperature. **Positive = room cooled** | -0.058 mW / +0.56 mW |
| `COP` | Q_room divided by electrical power | negative / 0.68 |
| `eta_E` | Energy balance: heat accounted for / electrical power | COMSOL expects 0.95-0.97 (builtin source) |
| `T_end-T_room, Config B` | Temperature of the junction ends relative to the centre sink | +0.10 mK / -0.94 mK |

**Expected physics:** V0 heats the ends (positive), V1 cools them by a few tenths to a few mK.
The cooling grows with VF (about 5 mK at 0.8 V in the reference model). Milli-kelvin is the
correct order of magnitude; it is not a failure of the simulation.

### 11.2 The checks C1-C9

| Check | Plain-language meaning | If it FAILS |
|---|---|---|
| C1 | At zero bias nothing heats or cools | Look for a heat source not proportional to current; check `bhs_n/bhs_p` |
| C2 | Energy is conserved (η_E in the expected window) | Wrong heat-source variable or units; check `Q_TOT`, `I_TERMINAL` |
| C3 | The junctions really absorb heat (negative integrals) | Check the `Qjn` windows and the sign of `semi.Q_tot` |
| C4 | The size of the junction cooling matches theory within ±30% | Often the i-region field (`E_X`) name; compare with Fig. 3 |
| C5 | V0's current matches the textbook formula within ×3 | Lifetime or recombination nodes not applied |
| C6 | Doubling the mesh changes results by < 2% | Needs variant V4 (section 12); PENDING until then |
| C7 | No cooling ≥ 0.1 K anywhere | **BUG**: see 11.3 |
| C8 | Reverse bias does not cool | Sign error in a heat source |
| C9 | COMSOL and the reference model agree within a factor of 2 | Compare Fig. 9; the reference is simplified, small differences are expected |

`PENDING` means "the data for this check do not exist yet" (for example C6 before V4 has run).

### 11.3 If you see BUG

Cooling of 0.1 K or more is physically implausible for this device (spec §0 rule 6). It means a
setup error, never a discovery. The usual causes, in order:

1. The boundary sinks `bhs_n/bhs_p` have the wrong unit (W instead of W/m²) or wrong sign.
2. The temperature input of the semiconductor is **not** `T0` (two-way coupling crept in).
3. `semi.Q_tot` was replaced by a different variable.

Do not use the numbers until the BUG is gone.

### 11.4 The figures

| Figure | What to look for |
|---|---|
| fig1 band diagram | Bands flatten under forward bias; quasi-Fermi levels split by about the junction voltage |
| fig2 carriers | V1 has a dip of n, p in the centre (the recombination zone) |
| fig3 heat source | **Negative dip** of Q_tot right at each junction: the junction cooling |
| fig4 temperature (key figure) | V0 ends above 0, V1 ends below 0, in mK |
| fig5 Q_room vs dT_sink | Straight lines; where each crosses zero is ΔT_max (dots) |
| fig6 ΔT_max and COP vs VF | ΔT_max grows with VF; COP falls |
| fig7, fig8 | Need V5 and V6 (section 12) |
| fig9 | COMSOL (solid) vs reference (dashed) should be close |
| fig10 | Thermophotonic map (analytic, no simulation needed) |

---

## 12. Run the rest of the variant matrix

After V0 and V1 look right, run the other variants. You can run everything at once
(`--set full`, 51 runs, roughly 1-3 hours), but it is easier to follow in groups:

| Order | Command | What it tests | Approx. time |
|---|---|---|---|
| 1 | `python comsol/python/run_variants.py --ids V4` | Mesh convergence (enables check C6) | 10 min |
| 2 | `python comsol/python/run_variants.py --ids V3a,V3b` | Corrected (Wachutka) heat source | 15 min |
| 3 | `python comsol/python/run_variants.py --ids V8a,V8b` | Alternative mobility model | 15 min |
| 4 | `python comsol/python/run_variants.py --ids V5` | Scaling with length and lifetime (12 runs, Fig. 7) | 20-40 min |
| 5 | `python comsol/python/run_variants.py --ids V6` | Recombination-zone design (12 runs, Fig. 8) | 20-40 min |
| 6 | `python comsol/python/run_variants.py --ids V7a,V7b` | Lateral sink, Config C (18 runs) | 30-60 min |
| 7 | `python comsol/python/run_variants.py --ids V2a,V2b` | Realistic transport; **needs section 5** | 15 min |

After each group run `python postprocess/report.py` again; the summary and figures update.

To change a physical parameter for your own study, edit `config/params_base.yaml` (values are in
COMSOL syntax, e.g. `"1[mm]"`), then run `python comsol/python/write_params_txt.py` and rebuild
(section 6). To add your own variant, copy an entry in `config/variants.yaml` and give it a new
ID. Write every such change into `CHANGES.md` so your results stay traceable.

---

## 13. Alternative route: Java only (Driver B)

Use this if Python cannot connect to COMSOL. It does the same work with COMSOL's own Java tools.

1. Open a Command Prompt in `C:\pin_peltier\comsol\java` (File Explorer > that folder > type `cmd`
   in the address bar).
2. Build the model (stages 1-8):
   ```bat
   build_and_run.bat build
   ```
3. Run V0 and V1:
   ```bat
   build_and_run.bat run core
   ```
4. Logs: `comsol\models\build_batch.log` and `results\run_batch.log`. Name errors look the same as
   in section 7.1. After editing `config\api_names_override.yaml`, regenerate the Java constants
   (this one step needs Python):
   ```bat
   python ..\python\sync_java_api_names.py
   ```
   then repeat step 2.
5. The report (section 10) still needs Python.

---

## 14. Troubleshooting

| Problem | Solution |
|---|---|
| `'python' is not recognized` | Python is not on PATH. Reinstall with "Add python.exe to PATH" ticked, or use `py` instead of `python`. Open a new Command Prompt afterwards. |
| `No module named mph` (or numpy, ...) | The environment is not active. Run `.venv\Scripts\activate` (prompt shows `(.venv)`), then repeat the command. |
| MPh cannot start COMSOL / "Could not locate COMSOL" | Set `COMSOL63_PATH` (section 3), open a new window. Check that COMSOL starts from the Start menu. Try `python -c "import mph; print(mph.discovery.backend())"` to see what MPh finds. |
| Licence error (`License error -...`) | Close other COMSOL sessions (a licence may be used up); check that the Semiconductor Module is licensed: in COMSOL, *Help > Licensed and Used Products*. |
| `COMSOL rejected API name ...` | Section 7. |
| Solver does not converge (all fallbacks failed) | In `config/params_base.yaml` raise `l_dec` to `"0.3[um]"`, or in `sweeps` use a VF step of `0.01`. Rebuild. Record the change in `CHANGES.md`. |
| `Wrong-sign Q_room` (V1 heats the room in COMSOL but cools in the reference) | Check the flux variable `TFLUX_X` (`ht.tfluxX` is positive in +x direction) and the boundary sinks. |
| `V2a needs the library material ... skipped` | Do section 5, rebuild (section 6), run V2a/V2b again. |
| The run is very slow | Close other programs; set `cores` in `config/user_env.yaml` (`mph: cores:`) to your number of CPU cores. |
| The computer froze / out of memory | Unlikely for 1D. Restart, run one variant at a time with `--ids`. |
| Everything is broken and you want to start over | Delete the folder `comsol\models\` and the result folders `results\V0`, `results\V1` (not `results\reference`), then section 6 again. Your `api_names_override.yaml` stays. |

Exit codes (shown if you type `echo %errorlevel%` right after a command): `0` OK, `1` setup
problem (missing file or package), `2` BUG (cooling ≥ 0.1 K), `3` a COMSOL name was rejected,
`4` some variants failed (see the log).

---

## 15. Glossary

| Term | Meaning |
|---|---|
| **VF** | Forward bias voltage applied to the p⁺ contact (V). Swept from 0 to 0.9 V. |
| **Config A** | Both junction ends held at room temperature, centre sink at room + `dT_sink`. Used to compute the room heat balance. |
| **Config B** | Junction ends insulated, centre held at room temperature. Shows how far the ends cool or warm by themselves. |
| **Config C** | Ends insulated, heat removed sideways from the i-region by convection (`h_lat`). |
| **Q_room** | Heat extracted from the room (W). Positive = cooling. |
| **ΔT_max** | Largest sink-minus-room temperature at which the room is still cooled. |
| **COP** | Coefficient of performance = cooling power / electrical power. |
| **η_E** | Energy-balance ratio; checks that heat in the model adds up to electrical power. |
| **Variant (V0, V1, ...)** | A set of parameter/physics changes from `config/variants.yaml`. |
| **Reference model** | The simplified Python model used as an independent cross-check. |
| **⚠VERIFY name** | A COMSOL internal name that must be confirmed against your COMSOL version (section 7). |
| **Stage** | One step of the automatic model build; saved as `stageN.mph`. |
| **One-way coupling** | Electrical model uses a fixed temperature `T0`; the heat model uses the electrical heat but never feeds back. |

---

## 16. One-page checklist

- [ ] Project files in `C:\pin_peltier` (branch `claude/amazing-wright-8jucjb`)
- [ ] Python ≥ 3.11 installed, `.venv` created, packages installed
- [ ] `COMSOL63_PATH` set; `mph.start()` test prints the COMSOL version
- [ ] `python -m pytest -q` passes
- [ ] (Recommended) `comsol\materials\Si_library.mph` saved
- [ ] `build_model.py --until 1` ... `--until 5`, then full build: `stage 8 OK`
- [ ] Any rejected names fixed in `config\api_names_override.yaml`
- [ ] Model opened in the GUI and the five sanity points of section 8 checked
- [ ] `run_variants.py --set core` finished; `results\V0`, `results\V1` exist
- [ ] `report.py` run; no BUG; C1-C5, C7-C9 reviewed in `results\summary.md`
- [ ] V4 run (C6), then the remaining groups of section 12
- [ ] Any change of parameters or settings recorded in `CHANGES.md`
