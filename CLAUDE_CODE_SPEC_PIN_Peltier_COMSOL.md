# Claude Code Specification — PIN-Diode Junction-Cooling Simulation Package (COMSOL)

> **How to use this file:** put it in an empty project folder and tell Claude Code:
> *"Read CLAUDE_CODE_SPEC_PIN_Peltier_COMSOL.md and implement everything in it. Ask me the questions in §2 first."*

---

## 0. Role and ground rules for Claude Code

You are implementing a reproducible simulation package for a COMSOL Multiphysics electro-thermal study of a forward-biased silicon n⁺–i–p⁺ (PIN) diode. The package must build the COMSOL model **programmatically**, with every parameter, physics node, mesh, study and variant defined below, run the sweeps, export data, and produce figures.

**Rules:**

1. **Never invent COMSOL API names silently.** Several feature-type strings and property names below are marked `⚠VERIFY`. For each one:
   - put it in a single constants block at the top of the builder (`API_NAMES`), and
   - add a comment explaining how the user can confirm it: build that one node in the GUI, then *File → Save As → Model File for Java (.java)* and read the generated tag.
2. Build in **small, testable stages** (§9). Each stage must save an `.mph` file, so a failure points to exactly one node.
3. **Coupling must be one-way** (Semiconductor → Heat Transfer). The semiconductor temperature input is fixed at `T0` and is never linked to `ht.T`. The temperature differences of interest are milli-kelvin.
4. Every number in this spec is intentional. Do not "improve" values without listing the change in `CHANGES.md`.
5. If COMSOL is not installed on this machine, still generate all files. Write the independent Python reference model (§11) and run it, since it needs no COMSOL. Clearly report what could not be executed.
6. The physics expectation is that net cooling is **milli-kelvin** at best. Do not tune the model to make cooling look larger. Results ≥ 0.1 K of cooling indicate a bug (§10).

---

## 1. Scientific background (context for the implementer)

A colleague proposes cooling a room with a forward-biased PIN diode. The junction regions (μm-thick n⁺ and p⁺ layers) would sit inside the room, and the mm-long intrinsic region, where carriers recombine and release heat, would be outside as the heat sink.

**Energy per electron–hole pair (Si, 300 K):**

- The source supplies $qV$.
- Non-radiative recombination releases $\approx E_g + 3k_BT \approx 1.20$ eV.
- The junction and contact regions therefore absorb $\Pi \approx E_g + 3k_BT - qV$ from the lattice. This is the bipolar Peltier effect.

**COMSOL's heat source.** COMSOL's `semi.Q_tot` is a simplified heat source containing Joule heating plus recombination heating, roughly $\mathbf J\cdot\mathbf E + U(E_g+3k_BT)$. In a forward-biased junction the current flows against the residual built-in field, so $\mathbf J\cdot\mathbf E<0$ there. COMSOL therefore *does* capture the junction cooling.

**What the model must add.**

- *Required:* COMSOL's ideal ohmic contacts release no Peltier heat. Add it manually as boundary heat sinks:

$$
Q_{b,n} = -|J|\,\Pi_{n,c},\qquad \Pi_{n,c} = \frac{k_BT}{q}\Big[\ln\frac{N_c}{N_D}+2\Big]
$$

$$
Q_{b,p} = -|J|\,\Pi_{p,c},\qquad \Pi_{p,c} = \frac{k_BT}{q}\Big[\ln\frac{N_v}{N_A}+2\Big]
$$

- *Optional correction:* the exact energy-flux heat source for Boltzmann statistics (Wachutka 1990) uses $U(E_g+4k_BT)$. A "corrected" variant adds $k_BT\cdot U$ to `semi.Q_tot`.

**Key expected outcomes:**

| Case | Result |
|---|---|
| Local heat source at the junctions | Negative. Junction cooling is real. |
| Uniform lifetime (device as drawn) | Recombination heat flows back to the junction ends. Ends become **warmer** than the sink; the room is heated. |
| Engineered central recombination zone | Ends cool below the sink by **≈ 2–10 mK** for $W_i = 1$ mm. |
| Theoretical bound | $\Delta T_{max}\sim nD_a\Pi/k$, which is milli-kelvin for Si. |

**Stacking modules does not help.**

- Thermally parallel modules multiply watts, not ΔT.
- A thermal cascade needs about 2000 stages for 10 K. The electrical power grows as $\prod(1+1/\mathrm{COP}_i)$, which is astronomically large.

The package includes a calculator demonstrating this (§12).

---

## 2. Ask the user BEFORE writing code

Ask these in one message, and record the answers in `config/user_env.yaml`:

1. COMSOL version (6.2 / 6.3 / 6.4 / other) and install path (to locate the `comsol` executable).
2. Licensed modules: Semiconductor Module? Heat Transfer Module? (Heat Transfer in Solids in 1D also works with the base package.) LiveLink for MATLAB?
3. Preferred driver:
   - **(A) Python + MPh** (recommended: `pip install mph`, which talks to a local COMSOL server)
   - **(B) Pure Java API** (`comsol compile` + `comsol batch`, no Python needed)
   - **(C) MATLAB LiveLink**
   - Generate all three if the user says "all"; the default is A + B.
4. OS (Windows / Linux / macOS) and Python version.
5. Run the full variant matrix (§7), or only the core variants V0 and V1 first?

If the user is unavailable, use these defaults:

- COMSOL 6.3
- Semiconductor + Heat Transfer modules
- Drivers A + B
- Windows
- Python 3.11
- Core variants first, then the full matrix

---

## 3. Deliverables (repository layout)

```
pin_peltier_comsol/
├── README.md                       # how to run everything, prerequisites, troubleshooting
├── CHANGES.md                      # any deviation from this spec, with reason
├── config/
│   ├── params_base.yaml            # §5 parameters (single source of truth)
│   ├── variants.yaml               # §7 variant matrix
│   └── user_env.yaml               # answers from §2
├── comsol/
│   ├── java/
│   │   ├── BuildPinPeltier.java    # builds + saves pin_peltier_base.mph (driver B)
│   │   ├── RunVariants.java        # loads base .mph, applies variants, solves, exports CSV
│   │   └── build_and_run.(bat|sh)  # comsol compile / comsol batch wrappers
│   ├── python/
│   │   ├── build_model.py          # driver A: builds the same model through MPh (model.java API)
│   │   ├── run_variants.py         # loops over variants.yaml, solves, exports
│   │   └── api_names.py            # ⚠VERIFY constants (shared names, one place)
│   ├── matlab/                     # only if driver C requested
│   │   └── build_pin_peltier.m
│   └── params.txt                  # Parameters node import file (name  expr  "desc")
├── postprocess/
│   ├── analyze.py                  # Q_room, ΔT_max, COP, energy balance, junction integrals
│   ├── plots.py                    # all figures in §8.4
│   └── report.py                   # writes results/summary.md with tables + figure links
├── reference/
│   ├── reference_model.py          # COMSOL-independent ambipolar + heat model (§11)
│   └── cascade_calculator.py       # many-modules analysis (§12)
├── tests/
│   ├── test_reference_model.py     # pytest: analytic limits
│   └── test_postprocess.py         # pytest: formulas on synthetic data
├── results/                        # CSV exports, figures, summary.md (generated)
└── docs/
    └── GUI_build_steps.md          # human-readable click-by-click equivalent of the builder
```

---

## 4. Model definition (physics-level, independent of API)

### 4.1 Geometry (1D)

- Points, in order: `0`, `Wn`, `Xc`, `Wn+Wi`, `Ltot`.
- This gives 4 domains: n⁺ | left i-half | right i-half | p⁺.

| Point | Location | Use |
|---|---|---|
| P1 | x = 0 | n⁺ ohmic contact |
| P3 | x = Xc | centre; interior thermal-sink point |
| P5 | x = Ltot | p⁺ ohmic contact |

- Cross-sectional area `Ac` is set in both physics interfaces (1D "cross-sectional area" setting).

### 4.2 Material (Si, 300 K)

**Preferred:** load *Si – Silicon* from the Semiconductor material library.

**Fallback (if library loading via API is awkward):** create a blank material with these explicit properties:

| Property | Value | COMSOL property group / name |
|---|---|---|
| Relative permittivity | 11.7 | `def` / `relpermittivity` ⚠VERIFY |
| Band gap $E_{g0}$ | 1.12 V | `SemicondMaterial` / `Eg0` ⚠VERIFY |
| Electron affinity $\chi_0$ | 4.05 V | `SemicondMaterial` / `chi0` ⚠VERIFY |
| $N_c$ | 2.86e19 cm⁻³ ·(T/300)^1.5 | `SemicondMaterial` / `Nc` ⚠VERIFY |
| $N_v$ | 3.10e19 cm⁻³ ·(T/300)^1.5 | `SemicondMaterial` / `Nv` ⚠VERIFY |
| Electron mobility (lattice) | 1448 cm²/(V·s) | `SemicondMaterial` / `mun` ⚠VERIFY |
| Hole mobility (lattice) | 473 cm²/(V·s) | `SemicondMaterial` / `mup` ⚠VERIFY |
| Thermal conductivity | `k_Si` = 148 W/(m·K) | `def` / `thermalconductivity` |
| Density | `rho_Si` = 2329 kg/m³ | `def` / `density` |
| Heat capacity | `Cp_Si` = 700 J/(kg·K) | `def` / `heatcapacity` |

After the material is created, the builder must **read back** $N_c$ and $N_v$. It then recomputes `Pi_nc` and `Pi_pc` (§5) and logs both values.

### 4.3 Semiconductor interface (`semi`)

**Interface settings**

| Setting | Value |
|---|---|
| Discretization | Finite volume (default) |
| Carrier statistics | Maxwell–Boltzmann (baseline); Fermi–Dirac in the "realistic" variant |
| Temperature reference for energy levels | `T0` |
| Cross-sectional area | `Ac` |

**Semiconductor Material Model 1**

| Setting | Value |
|---|---|
| Temperature input | **User defined `T0`** (one-way coupling) |
| Band-gap narrowing | Off (baseline); Slotboom (realistic variant) |
| Incomplete ionization | Off |

**Mobility**

- **Option M1 (default):** Arora Mobility Model (LI), library parameters.
- **Option M2 (fallback, fully explicit):** user-defined Caughey–Thomas, with $N_{tot} = N_D^+ + N_A^-$:

$$
\mu = \mu_{min} + \frac{\mu_{max}-\mu_{min}}{1+(N_{tot}/N_{ref})^{\alpha}}
$$

| Carrier | μ_min | μ_max | N_ref | α |
|---|---|---|---|---|
| Electrons | 68.5 cm²/Vs | 1414 cm²/Vs | 9.20e16 cm⁻³ | 0.711 |
| Holes | 44.9 cm²/Vs | 470.5 cm²/Vs | 2.23e17 cm⁻³ | 0.719 |

- **Optional add-on (realistic variant):** Fletcher Mobility Model (C), for carrier–carrier scattering.

**Doping (Analytic Doping Model ×3, Box distribution)**

| Node | Type | Box start | Box width | Concentration | Profile outside box |
|---|---|---|---|---|---|
| dop_bg | Acceptor | 0 | Ltot | N_bg | none |
| dop_n | Donor | 0 | Wn | Nd_p | Gaussian, length scale `l_dec` |
| dop_p | Acceptor | Ltot−Wp | Wp | Na_p | Gaussian, length scale `l_dec` |

**Recombination**

| Node | Settings |
|---|---|
| Trap-Assisted (SRH) | τn = τp = `tau_x` (variable, §5.2); trap level midgap |
| Auger | Cn = `Cn_aug`, Cp = `Cp_aug` |

No radiative recombination in Si variants.

**Contacts**

| Node | Point | Type | Terminal | Value |
|---|---|---|---|---|
| mc_n | P1 | Ideal ohmic | Voltage | 0 V |
| mc_p | P5 | Ideal ohmic | Voltage | `VF` |

### 4.4 Heat Transfer in Solids (`ht`)

**Interface and domain**

| Item | Value |
|---|---|
| Cross-sectional area | `Ac` |
| Compute boundary fluxes | ON |
| Solid | properties from material |
| Initial value | `T_room` |

**Heat sources**

| Node | Selection | Expression |
|---|---|---|
| hs1 | all domains | `semi.Q_tot` (variant `qsrc=builtin`) **or** `semi.Q_tot + k_B_const*T0*U_TOT` (variant `qsrc=corrected`) |
| bhs_n | P1 | `-abs(J_X)*Pi_nc` |
| bhs_p | P5 | `-abs(J_X)*Pi_pc` |

`U_TOT` and `J_X` are ⚠VERIFY names:

- `U_TOT` is the total net recombination rate variable (search the semi variable list for "total recombination").
- `J_X` is the total current density x-component (often `semi.JX`).

**Thermal boundary nodes** (create all; enable per configuration, §7):

| Tag | Selection | Value | Used in |
|---|---|---|---|
| temp_ends | P1, P5 | `T_room` | Config A |
| temp_sinkA | P3 | `T_room + dT_sink` | Config A |
| temp_sinkB | P3 | `T_room` | Config B |
| hs_lat | i-region domains (2, 3) | `-h_lat*Plat_over_A*(T - T_out)` | Config C |

`hs_lat` is a lateral convective sink, active only in Config C. Optionally restrict it to `abs(x-Xc) < (Wi/2 - w_wall)`, so that a wall segment of length `w_wall` next to each junction is insulated.

### 4.5 Mesh (1D edge distributions)

| Domain | Distribution |
|---|---|
| n⁺ | fixed 400 elements |
| p⁺ | fixed 400 elements |
| left i-half | 600 elements, geometric, element ratio 2000, **fine end at the junction (x = Wn)** |
| right i-half | 600 elements, geometric, element ratio 2000, **fine end at x = Wn+Wi** |

- Mesh-refinement variant: multiply all counts by `mesh_factor` ∈ {1, 2}.
- After meshing, assert in code that the smallest element in each i-half sits at the junction end. Use the "reverse direction" flag as needed.

### 4.6 Studies

**std_eq_iv — Study 1: I–V and heat-source map**

1. Semiconductor Equilibrium step, physics `semi` only.
2. Stationary step, physics `semi` + `ht`.
   - Auxiliary sweep `VF` = `range(0, 0.025, 0.9)`, continuation ON.
   - Relative tolerance 1e-6.

**std_room — Study 2: Config A, ΔT_max search**

- Stationary step, `semi` + `ht`.
- Auxiliary sweep `VF` = `range(0, 0.025, 0.8)`.
- Parametric sweep over `dT_sink` = `range(-0.02, 0.0025, 0.02)`.

**std_float — Study 3: Config B**

- Stationary step, `semi` + `ht`.
- Auxiliary sweep `VF` = `range(0, 0.025, 0.9)`.

**std_lat — Study 4: Config C (lateral sink)**

- Stationary step, `semi` + `ht`.
- Auxiliary sweep as in Study 3.

**All studies**

- Variant parameters (rz_on, etc.) are applied by the driver (§7), *not* by nested parametric sweeps. This keeps one dataset per variant and makes exports simple.
- Each study step uses **"Modify model configuration for study step"** to disable the thermal nodes of the other configurations (⚠VERIFY property names, typically `useadvanceddisable` / `disabledphysics`).
- If a stationary step fails to converge, apply the fallback automatically: Segregated solver with group 1 = semi variables and group 2 = `T`; then halve the VF step.

---

## 5. Parameters (single source of truth → `config/params_base.yaml` and `comsol/params.txt`)

### 5.1 Global parameters

| Name | Expression | Description |
|---|---|---|
| T0 | 300[K] | Lattice/reference temperature (semiconductor) |
| T_room | 300[K] | Room reservoir temperature |
| dT_sink | 0[K] | Sink minus room temperature (Config A sweep) |
| T_out | 300[K] | Ambient for lateral sink (Config C) |
| Wn | 2[um] | n⁺ thickness |
| Wp | 2[um] | p⁺ thickness |
| Wi | 1[mm] | intrinsic length |
| Ltot | Wn+Wi+Wp | total length |
| Xc | Ltot/2 | centre |
| Nd_p | 1e19[1/cm^3] | n⁺ donor peak |
| Na_p | 1e19[1/cm^3] | p⁺ acceptor peak |
| N_bg | 1e12[1/cm^3] | i-region background acceptors |
| l_dec | 0.1[um] | Gaussian decay length |
| tau_long | 1[ms] | SRH lifetime, high-purity Si |
| tau_short | 1[us] | SRH lifetime in recombination zone |
| w_rz | 100[um] | recombination-zone width |
| rz_on | 0 | 0 = uniform lifetime, 1 = engineered zone |
| Cn_aug | 2.8e-31[cm^6/s] | Auger, electrons (Dziewior & Schmid 1977) |
| Cp_aug | 9.9e-32[cm^6/s] | Auger, holes |
| Ac | 1[mm^2] | cross-sectional area |
| k_Si | 148[W/(m*K)] | thermal conductivity |
| rho_Si | 2329[kg/m^3] | density |
| Cp_Si | 700[J/(kg*K)] | heat capacity |
| VF | 0.7[V] | forward bias (swept) |
| Nc_si | 2.86e19[1/cm^3] | for Π calc (overwrite with library value) |
| Nv_si | 3.10e19[1/cm^3] | for Π calc (overwrite with library value) |
| Pi_nc | k_B_const*T0/e_const*(log(Nc_si/Nd_p)+2) | n-contact Peltier coefficient (≈0.079 V) |
| Pi_pc | k_B_const*T0/e_const*(log(Nv_si/Na_p)+2) | p-contact Peltier coefficient (≈0.081 V) |
| h_lat | 1e4[W/(m^2*K)] | lateral heat-transfer coefficient (Config C) |
| Plat_over_A | 4000[1/m] | perimeter/area of 1 mm × 1 mm bar |
| w_wall | 50[um] | insulated wall length next to each junction (Config C) |
| mesh_factor | 1 | mesh refinement multiplier |

### 5.2 Functions and variables

- **Rectangle function `rect1`:** lower limit `Xc-w_rz/2`, upper limit `Xc+w_rz/2`, smoothing transition zone `10[um]`.
- **Variable:**

  ```
  tau_x = 1/(1/tau_long + rz_on*rect1(x)/tau_short)
  ```

  This combines recombination *rates*, which is physically correct.
- **Variable (Config C mask):**

  ```
  lat_mask = (abs(x-Xc) < (Wi/2 - w_wall))
  ```

  Then use `-h_lat*Plat_over_A*(T-T_out)*lat_mask`.

---

## 6. Outputs to export (per variant run)

Write CSVs to `results/<variant_id>/`. Every file begins with a header comment containing the variant parameters and COMSOL version.

### 6.1 `global_vs_VF.csv`

One row per VF. Columns:

| Column | Definition |
|---|---|
| VF | applied bias, V |
| I | terminal current, A (from contact terminal current; ⚠VERIFY name) |
| J | `I/Ac`, A/m² |
| P_el | `I*VF`, W |
| Qtot_int | `Ac*∫ semi.Q_tot dx`, W |
| Qjn_n | `Ac*∫_{0}^{Wn+5um} semi.Q_tot dx`, W (expected < 0) |
| Qjn_p | `Ac*∫_{Ltot-Wp-5um}^{Ltot} semi.Q_tot dx`, W (expected < 0) |
| Qc_contacts | `-|J|*Ac*(Pi_nc+Pi_pc)`, W |
| qx_0, qx_L | `ht.tfluxX` at P1 and P5, W/m² |
| T_P1, T_P5, T_P3 | point temperatures, K |
| Q_room | `Ac*(qx_0 - qx_L + |J|*(Pi_nc+Pi_pc))`, W (Config A only; positive = room cooled) |
| eta_E | `(Qtot_int + Qc_contacts)/P_el` (energy-balance ratio) |

### 6.2 `profiles_VF{v}.csv`

For VF ∈ {0, 0.6, 0.7, 0.75, 0.8}, and x on the mesh nodes. Columns:

```
x, Ec, Ev, Efn, Efp, n, p, Ndop, JdotE, Q_tot, Q_rec(=Q_tot−JdotE), T, tfluxX
```

### 6.3 `room_sweep.csv` (Study 2)

Columns: `VF, dT_sink, Q_room`.

---

## 7. Variant matrix (`config/variants.yaml`)

| ID | Purpose | Changes from base |
|---|---|---|
| **V0** | Device as drawn | rz_on=0, MB stats, no BGN, mobility M1, qsrc=builtin |
| **V1** | Engineered recombination zone | rz_on=1 |
| V2a / V2b | Realistic transport | V0 / V1 + Fermi–Dirac, Slotboom BGN, Fletcher. *Flag in report: Q_tot inside doped layers less reliable with BGN.* |
| V3a / V3b | Corrected heat source | V0 / V1 with qsrc=corrected |
| V4 | Mesh convergence | V1 with mesh_factor=2 |
| V5 | Scaling study | V1 with Wi ∈ {0.25, 0.5, 1, 2} mm × tau_long ∈ {0.1, 1, 5} ms (12 runs; Config B only) |
| V6 | Recombination-zone design | V1 with w_rz ∈ {25, 50, 100, 200} μm × tau_short ∈ {0.1, 1, 10} μs (Config B only) |
| V7 | Lateral sink (Config C) | V0 and V1, h_lat ∈ {1e3, 1e4, 1e5}, w_wall ∈ {0, 50, 200} μm |
| V8 | Mobility fallback | V0/V1 with mobility M2 (Caughey–Thomas), to confirm insensitivity |

**Thermal configurations to run for each variant** (unless the variant says otherwise):

- Config A (Study 2)
- Config B (Study 3)
- Study 1 always (I–V and profiles)

**Optional (only if the user asks):**

- **V9:** 2D U-shaped couple. Two i-region legs bent through an insulating wall; junction faces on an isothermal "room" plate; convective outer sink (h = 1e3–1e4 W/m²K). Build in 2D with the same physics. This is a stretch goal.
- **V10:** thermophotonic GaAs/AlGaAs double heterostructure with Optical Transitions. **Analytic stub only** in `reference/` (§11.4), unless the user requests a full COMSOL build.

---

## 8. Post-processing (`postprocess/`)

### 8.1 Room heat balance (Config A)

$$
Q_{room} = A_c\big[q_x(0^+) - q_x(L^-) + |J|(\Pi_{n,c}+\Pi_{p,c})\big]
$$

- Positive $Q_{room}$ means the room is cooled.
- $\Delta T_{max}(V_F)$ is the `dT_sink` where $Q_{room}=0$. Find it by linear interpolation; report "none (room heated)" if $Q_{room}<0$ at `dT_sink = 0`.

### 8.2 COP

$$
\mathrm{COP}(V_F,\Delta T)=Q_{room}/(I\,V_F)
$$

Report it at ΔT = 0 and at ΔT_max/2.

### 8.3 Energy balance

$$
\eta_E = \frac{Q_{tot,int}+Q_{c,contacts}}{I\,V_F}
$$

Expected value: $\eta_E \approx 1-\dfrac{k_BT/q}{V_F}$, i.e. 0.95–0.97 for qsrc=builtin. For qsrc=corrected, expect ≈ 1.00 ± 0.02.

### 8.4 Figures (PNG at 300 dpi + PDF; matplotlib; SI units; labelled axes)

1. Band diagram (Ec, Ev, Efn, Efp) at VF = 0 and 0.7 V. Use a broken x-axis or insets zoomed on each junction.
2. n(x), p(x) on a log scale, V0 vs V1 at VF = 0.7 V.
3. Q_tot(x) zoomed to 0–10 μm and the mirror region, showing the negative dip, with J·E and Q_rec as separate curves.
4. **Key figure:** T(x) − T_room in mK, Config B, V0 vs V1, at VF = 0.7 V.
5. Q_room vs dT_sink (Config A), V0 vs V1, at VF ∈ {0.65, 0.70, 0.75}, with ΔT_max markers.
6. ΔT_max and COP vs VF.
7. V5 scaling: ΔT_max vs Wi for each tau_long, with the analytic bound $nD_a\Pi/k$ overlaid.
8. V6: ΔT_max heat-map over (w_rz, tau_short).
9. Comparison COMSOL vs reference model (§11) for V0 and V1.

### 8.5 `results/summary.md`

Must contain:

- a table of ΔT_max, Q_room at ΔT = 0, COP and η_E for every variant;
- the verification-check pass/fail list (§10);
- links to the figures;
- a short auto-generated conclusion paragraph that states the numbers. No hype.

---

## 9. Implementation plan and staged build (both drivers)

Each stage saves `stageN.mph` and runs a smoke test.

| Stage | Contents | Smoke test |
|---|---|---|
| 1 | Parameters, functions, variables, geometry | 5 points, 4 domains |
| 2 | Material | Read back Eg0, Nc, Nv; log Pi_nc, Pi_pc |
| 3 | `semi` interface + doping | Equilibrium solve converges; net doping plot ranges −1e19 … +1e19 |
| 4 | Recombination + contacts + Study 1 (semi only) | I–V monotonic; J(0.7 V) within 0.02–1 A/cm² for V0 |
| 5 | `ht` interface + heat sources + Config B nodes | T(VF=0) ≡ T_room |
| 6 | Config A nodes + Studies 2–4 + model-configuration toggles | — |
| 7 | Export routines | — |
| 8 | Variant driver loop | — |

### 9.1 Driver A (Python + MPh)

```python
import mph
client = mph.start(cores=4)
model  = client.create('pin_peltier')
j = model.java          # full COMSOL Java API object
```

- Then mirror the Java calls exactly. Keep the shared tag and feature-type names in `api_names.py`.
- Use `model.parameter(name, value)` for variants and `model.solve(study)` to run.
- Use `model.evaluate(expr, unit, dataset)`, or exports, to pull data.

### 9.2 Driver B (Java API)

Expected call patterns to implement. All feature type strings are ⚠VERIFY.

```java
Model model = ModelUtil.create("Model");
model.param().set("Wi", "1[mm]", "intrinsic length");          // loop over params table
model.component().create("comp1", true);
model.component("comp1").geom().create("geom1", 1);
model.component("comp1").geom("geom1").create("i1", "Interval");
model.component("comp1").geom("geom1").feature("i1").set("specify", "coord");
model.component("comp1").geom("geom1").feature("i1")
     .set("coord", new String[]{"0","Wn","Xc","Wn+Wi","Ltot"});
model.component("comp1").geom("geom1").run();
model.component("comp1").physics().create("semi", "Semiconductor", "geom1");      // ⚠VERIFY
model.component("comp1").physics().create("ht", "HeatTransfer", "geom1");         // ⚠VERIFY
// semi features: "AnalyticDopingModel", "TrapAssistedRecombination",
//                "AugerRecombination", "MetalContact"                            // ⚠VERIFY all
// ht features:   "HeatSource", "BoundaryHeatSource", "TemperatureBoundary"       // ⚠VERIFY all
// studies:       "SemiconductorEquilibrium", "Stationary", "Parametric"          // ⚠VERIFY
model.save("pin_peltier_base.mph");
```

Wrapper scripts:

- Compile: `comsol compile BuildPinPeltier.java`
- Run: `comsol batch -inputfile BuildPinPeltier.class -outputfile pin_peltier_base.mph`
- Provide Windows `.bat` and Linux `.sh` versions using the path from `user_env.yaml`.

### 9.3 Driver C (MATLAB LiveLink, optional)

Same calls via `mphstart` / `ModelUtil.create`, mirroring the Java builder line by line.

### 9.4 Name-verification helper

Generate `docs/VERIFY_API_NAMES.md`. It must list every ⚠VERIFY item and give, for each one:

- the GUI action that creates it, and
- where to read the true tag in the "Save as Java" output.

The builders must fail fast with a clear message naming the offending constant when COMSOL rejects a name.

---

## 10. Verification checks (automated in `analyze.py`; results go to summary.md)

| # | Check | Pass criterion |
|---|---|---|
| C1 | Zero bias | max\|Q_tot\| < 1e-6 of its VF=0.7 V value; max\|T−T_room\| < 1 μK |
| C2 | Energy balance | η_E ∈ [0.93, 0.99] (builtin) or [0.98, 1.02] (corrected) for VF ≥ 0.5 V |
| C3 | Junction cooling exists | Qjn_n < 0 and Qjn_p < 0 for all 0.3 ≤ VF ≤ 1.0 V |
| C4 | Junction-cooling magnitude | (Qjn_n+Qjn_p) ≈ −I·(V_bi − V_j) within ±30%, where V_bi = (kT/q)ln(Nd_p·Na_p/n_i²), n_i = 1e10 cm⁻³, and V_j = VF − I·R_i (estimate R_i from the i-region field integral) |
| C5 | I–V benchmark (V0) | J within ×3 of q·n_i·exp(qV/2kT)·Wi/τ_eff for 0.6–0.8 V |
| C6 | Mesh convergence | V4 vs V1: ΔT_max and Qjn change < 2% |
| C7 | Plausibility | \|ΔT_max\| < 0.1 K for all Si variants (else flag BUG) |
| C8 | Reverse bias | VF = −0.5 V: no negative heat-source region beyond numerical noise; Q_room ≤ 0 |
| C9 | COMSOL vs reference model | ΔT (Config B) within a factor of 2 for V0 and V1 |

---

## 11. Independent reference model (`reference/reference_model.py`, no COMSOL)

**Purpose:** a fast semi-analytic cross-check, also runnable on machines without COMSOL. Use numpy and scipy only.

### 11.1 Carrier model (i-region only, high injection, n ≈ p)

$$
D_a\,n'' - \frac{n}{\tau(x)} - C_a\,n^3 = 0,\qquad 0<x<W_i
$$

**Inputs**

| Quantity | Value |
|---|---|
| $D_a$ | $2D_nD_p/(D_n+D_p)$, with $D=\mu k_BT/q$, μn = 1414 and μp = 470.5 cm²/Vs, giving $D_a\approx 18$ cm²/s |
| $C_a$ | $C_n + C_p$ |
| $\tau(x)$ | as in §5.2 (shift x by Wn) |
| Boundary conditions | $n(0)=n(W_i)=n_b=n_i\exp(qV_j/2k_BT)$, with $n_i = 9.65\times10^{9}$ cm⁻³ |

Solve with `scipy.integrate.solve_bvp` on a graded grid. Use continuation in $V_j$.

### 11.2 Current and heat

| Quantity | Expression |
|---|---|
| Recombination rate | $R(x)=n/\tau+C_a n^3$ |
| Current | $J = q\int_0^{W_i}R\,dx$ |
| Conductivity | $\sigma(x)=q\,n(\mu_n+\mu_p)$ |
| Ohmic drop | $V_\Omega = \int J/\sigma\,dx$ |
| Terminal voltage | $V_F = V_j + V_\Omega$ |
| i-region heat source | $H(x) = R(x)(E_g+3k_BT) + J^2/\sigma(x)$ |
| Total absorbed per pair | $\Pi_{tot} = E_g+3k_BT-qV_j$ |
| Point sink at each end | $-(J/q)\,\Pi_{tot}/2$ (symmetric split; ends include contacts and the μm doped layers, lumped) |

**Heat equation:** $k\,T''=-H$. Solve with finite differences for:

- Config A: $T(0)=T(W_i)=T_{room}$, $T(W_i/2)=T_{room}+\Delta T_{sink}$, giving $Q_{room}$ and $\Delta T_{max}$.
- Config B: insulated ends with point sinks, $T(W_i/2)=T_{room}$, giving $T(0)-T_{room}$.

**Outputs:** the same CSV schema as §6, so `plots.py` can overlay the two models.

### 11.3 Analytic bound

Implement and plot:

$$
\Delta T_{max}^{bound}\approx \frac{n_b D_a \Pi_{side}}{k},\qquad n_b \le \frac{2}{W_i}\sqrt{\frac{D_a}{C_a}}
$$

The second inequality is the Auger-limited carrier density.

### 11.4 Thermophotonic stub (V10)

A function `thermophotonic_cop(EQE, hw_eV, qV_eV)` returning net cooling per injected pair:

$$
\eta_{EQE}\hbar\omega - qV
$$

and the condition $\eta_{EQE} > qV/\hbar\omega$. Plot the cooling map over EQE ∈ [0.5, 1] and qV/ħω ∈ [0.5, 1]. Mark typical Si (EQE ≪ 1e-2) and state-of-the-art III–V LEDs (EQE ≳ 0.7–0.9) as annotations only. Do not invent specific device data.

### 11.5 Tests (`tests/test_reference_model.py`)

- With uniform τ and no Auger, the analytic solution $n=n_b\cosh((x-W_i/2)/L_a)/\cosh(W_i/2L_a)$ is reproduced within 1%.
- At $V_j=0$, J = 0 and T ≡ T_room.
- The energy balance closes to within 0.5%: total heat equals $J\,V_F$.

---

## 12. Many-modules calculator (`reference/cascade_calculator.py`)

**Inputs:** per-stage ΔT lift `dT_stage` (default 5 mK), per-stage COP (default 0.2), target lift `dT_target` (default 10 K), cooling load `Q_load` (default 100 W), interface thermal contact resistance `R_c` (default 1e-5 m²K/W), and per-stage heat flux.

**Outputs:**

| Quantity | Expression |
|---|---|
| Stages needed | $N=\lceil\Delta T_{target}/\delta T\rceil$ |
| Power multiplier | $\prod(1+1/\mathrm{COP})$, reported as log10 |
| Interface ΔT | $R_c\,q''$ per interface, compared with dT_stage |
| Parallel case | $Q_{total}=N_{mod}Q_1$ while $\Delta T_{max}$ is unchanged |

Print a short plain-language verdict, and write `results/cascade.md`.

---

## 13. README requirements

The README must cover:

1. Prerequisites: COMSOL modules, Python packages (`mph numpy scipy pandas matplotlib pyyaml pytest`), and Java/MATLAB if used.
2. Quick start:
   - `python reference/reference_model.py` (no COMSOL)
   - then `python comsol/python/build_model.py`
   - then `python comsol/python/run_variants.py --set core`
   - then `python postprocess/report.py`
3. Java-only path commands.
4. How to verify the ⚠VERIFY names (link to `docs/VERIFY_API_NAMES.md`).
5. Expected runtime per variant. 1D runs should take seconds to minutes.
6. Troubleshooting table:

| Problem | Fix |
|---|---|
| Equilibrium failure | Raise `l_dec` to 0.3 μm or ramp the doping |
| Forward sweep stalls | Use a VF step of 0.01 V |
| Wrong-sign Q_room | Check the boundary-flux sign convention |
| Missing variable names | See `docs/VERIFY_API_NAMES.md` |

7. The physics caveat in two sentences: cooling is real but milli-kelvin, and stacking does not fix it.

---

## 14. Acceptance checklist (Claude Code must report each item at the end)

- [ ] All files in §3 created
- [ ] Parameters identical to §5 (or deviations listed in CHANGES.md)
- [ ] Reference model and tests run and pass
- [ ] Cascade calculator runs and writes `results/cascade.md`
- [ ] COMSOL builders generated for the requested drivers; each ⚠VERIFY name isolated in one constants block
- [ ] If COMSOL is available: stages 1–8 executed, V0 and V1 solved, checks C1–C9 reported
- [ ] `results/summary.md` produced (or a template with placeholders if COMSOL was not run)
- [ ] `docs/GUI_build_steps.md` written for manual building

---

## 15. References (cite in README and summary.md)

1. COMSOL Semiconductor Module User's Guide, "Nonisothermal Models" (simplified heat source; `semi.Q_tot`). https://doc.comsol.com/6.4/doc/com.comsol.help.semicond/semicond_ug_modeling.5.18.html
2. COMSOL Application Library, *Thermal Analysis of a Bipolar Transistor* (Semiconductor_Module/Transistors/bipolar_transistor_thermal).
3. G. K. Wachutka, "Rigorous thermodynamic treatment of heat generation and conduction in semiconductor device modeling," *IEEE Trans. CAD* 9(11), 1141–1149 (1990).
4. K. P. Pipe, R. J. Ram, A. Shakouri, "Bias-dependent Peltier coefficient and internal cooling in bipolar devices," *Phys. Rev. B* 66, 125316 (2002).
5. J. Dziewior, W. Schmid, "Auger coefficients for highly doped and highly excited silicon," *Appl. Phys. Lett.* 31, 346 (1977).
6. D. M. Caughey, R. E. Thomas, "Carrier mobilities in silicon empirically related to doping and field," *Proc. IEEE* 55, 2192 (1967).
7. T. Sadi, I. Radevici, J. Oksanen, "Thermophotonic cooling with light-emitting diodes," *Nature Photonics* 14, 205 (2020).
