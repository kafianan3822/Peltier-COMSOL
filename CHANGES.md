# CHANGES: deviations from and interpretations of the specification

Spec: `CLAUDE_CODE_SPEC_PIN_Peltier_COMSOL.md`. **No numerical value of §5 was changed.**
`config/params_base.yaml` reproduces §5.1 exactly; `tests/test_postprocess.py::test_params_values_spec5`
and `test_params_txt_in_sync` guard this. Everything below is either an interpretation where the spec
leaves a choice open, or an addition. Each item gives the reason.

## Repository layout

| # | Change | Reason |
|---|---|---|
| L1 | The repository root *is* `pin_peltier_comsol/` (§3); there is no extra sub-folder. | The repository was created for this package. |
| L2 | Added `common/` (`params.py`: COMSOL-expression/unit evaluator and variant expansion; `csvio.py`: CSV with `#` header). | One parameter evaluator shared by the reference model, post-processing and the drivers, so the YAML stays the single source of truth. |
| L3 | Added `comsol/python/write_params_txt.py`. It generates `comsol/params.txt`, `comsol/java/variants_flat.txt` and `comsol/java/model_config.txt` from the YAML. | Java has no YAML parser. The generated flat files keep Driver B in sync with the YAML (tested). |
| L4 | Added `comsol/python/sync_java_api_names.py`. It regenerates the `API_NAMES` block in both Java files, the `SHARED` helper block in `RunVariants.java`, and `docs/VERIFY_API_NAMES.md`. | §0 rule 1 asks for *one* constants block. The Java copies are generated from `api_names.py`, never edited by hand (tested). |
| L5 | Added `config/api_names_override.yaml` support (the file is optional and not shipped). | Corrected ⚠VERIFY names can be applied without editing code. |
| L6 | Added `comsol/python/env.py` (finds COMSOL from `user_env.yaml` / `COMSOL63_PATH`). | §2 / §9.2: drivers and wrappers use the path recorded in `user_env.yaml`. |
| L7 | Added `tests/fake_comsol.py`, `tests/test_driver_mock.py`, `tests/test_java_compiles.py` and `tests/java_stubs/`. | COMSOL is not available on the build machine. The test double runs every Python path of Driver A, and the stubs compile Driver B (Java 8 source level). Neither shows that the ⚠VERIFY names are right. |
| L8 | `build_and_run.sh` is provided next to `build_and_run.bat`. | §9.2 asks for both. |
| L9 | Driver C (MATLAB) was not generated. | Not requested (`user_env.yaml`: drivers A + B). |

## Model / study interpretation (COMSOL builders)

| # | Change | Reason |
|---|---|---|
| M1 | **Study 1 runs thermal Config A at `dT_sink = 0`.** The `T_P1, T_P5, T_P3` columns of `global_vs_VF.csv` come from Study 3 (Config B, merged on VF; also written separately to `float_vs_VF.csv`). `T` and `tfluxX` in `profiles_VF*.csv` also come from Config B. | §6.1 mixes Config A quantities (`qx_0`, `qx_L`, `Q_room`: "Config A only") with point temperatures that are trivial in Config A (both ends at T_room). With one-way coupling the semiconductor solution is identical in every study, so merging is exact. The CSV headers state the source of each column. |
| M2 | `Qtot_int`, `Qjn_n`, `Qjn_p` integrate the **active** heat-source expression of `hs1` (`semi.Q_tot`, or `semi.Q_tot + k_B_const*T0*U_TOT` for `qsrc=corrected`). | Otherwise the C2 window for `corrected` (0.98-1.02) could not be reached. For `builtin` this is identical to the spec. |
| M3 | Config C = `hs_lat` only (ends insulated with their Peltier point sinks, no Dirichlet node). | §4.4/§7 name no temperature node for Config C. The lateral convective sink alone makes the problem well-posed. |
| M4 | **Material.** `material_source=auto`: if `comsol/materials/Si_library.mph` exists (saved once from the GUI library, see `docs/GUI_build_steps.md`), all its property groups are copied. Otherwise the §4.2 fallback table is used. | The COMSOL Java API has no call that "loads from the material library". GUI-generated code writes the library values out literally. Copying from a user-saved file avoids typing library numbers that are not in the spec. |
| M5 | With the fallback material, the **base mobility becomes M2** (Caughey-Thomas, §4.3). V2a/V2b (Slotboom BGN, Fletcher) are skipped with a clear message. Every CSV header records the material and mobility actually used. | The Arora (M1), BGN and Fletcher models read their parameters from the library material, and the spec gives no numbers for them. Inventing them is ruled out by §0 rule 4. |
| M6 | Thermal properties are always `k_Si`, `rho_Si`, `Cp_Si`, even with the library material. | §4.2 table / §5.1. |
| M7 | The mesh is created in stage 1 (geometry-only dependency) and rebuilt by the variant driver for every run (`mesh_factor`, V5 `Wi`). | Smoke test of §4.5 (fine end at the junction) needs only geometry. V5 changes the geometry. |
| M8 | Geometry: `Interval` with `intervals=many`, `p=[...]` (⚠VERIFY). On rejection the builder retries the spec form `specify=coord`, `coord=[...]`. | The spec form is marked "expected call pattern". Both are tried. |
| M9 | Each driver run reloads `pin_peltier_base.mph` and resets all §5 parameters before applying the variant (keeping the read-back `Nc_si`, `Nv_si`). | Nothing can leak from one variant to the next. |
| M10 | Check C8 runs an extra Study 1 sweep `range(0,-0.025,-0.5)` (continuation from 0 V) for V0 and V1 only, and writes `reverse_bias_global.csv` and `reverse_bias_profile.csv`. | §6 has no reverse-bias export, but C8 needs one. |
| M11 | Extra column `V_ifield = -intop_i(E_X)` (i-region voltage drop = I·R_i) in `global_vs_VF.csv`. | Needed for C4 (`V_j = VF - I R_i`). |
| M12 | The study 2 room sweep is read from the Parametric-Sweep dataset (`outersolnum`). If that fails, the driver loops over `dT_sink` itself (same numbers). | The parametric dataset layout is ⚠VERIFY. Q_room is linear in dT_sink, so both routes agree. |
| M13 | Variable names (`U_TOT`, `J_X`, `I_TERMINAL`, `Ec`, ...) are probed at run time from candidate lists, and the choice is logged and stored in `build_info.json`. | §0 rule 1 forbids silent invention. Probing replaces a guess with an evaluation by COMSOL, and the build fails fast if no candidate works. |
| M14 | Variant ids: V2 → V2a/V2b, V3 → V3a/V3b, V7 → V7a (from V0) / V7b (from V1), V8 → V8a/V8b. Sweep runs are named `V5_Wi=0.25mm_tau_long=0.1ms`, etc. | The spec rows describe pairs. Explicit ids keep one result folder per run. |

## Reference model (§11)

| # | Change | Reason |
|---|---|---|
| R1 | **Net recombination** `R = (n - n_i)/(s·tau) + C_a n (n² - n_i²)` instead of `n/tau + C_a n³`. | With the literal form R ≠ 0 at V_j = 0, which contradicts the spec's own test "At V_j = 0, J = 0 and T ≡ T_room" (§11.5). At high injection (n ≫ n_i) both forms agree. |
| R2 | **Lifetime convention `srh_hl` (default): s = 2**, i.e. high-injection lifetime τ_n + τ_p = 2·tau_x. `--convention spec_literal` gives s = 1 (the literal `n/tau`). | For n = p, τ_n = τ_p = τ and a midgap trap, the SRH rate that COMSOL evaluates is exactly (n - n_i)/(2τ). The reference model is a cross-check of COMSOL (C9), so it uses the same rate. The cosh test (§11.5) passes for both conventions with L_a = sqrt(D_a·s·τ). |
| R3 | The heat equation is integrated exactly (cumulative quadrature of the heat flux on each half) rather than with a finite-difference matrix. | This is the exact Green's-function solution of k T'' = -H on the same graded grid. Energy conservation is exact, which the 0.5% test needs. |
| R4 | Reference heat domain = i-region (length W_i), not L_tot. | The doped layers are lumped into the end sinks (§11.2). The length difference is 4 µm (0.4%). |
| R5 | Splitting of the lumped end sink for the §6 CSV schema: `Qjn_n = -Ac (J/q)(Π_tot/2 - qΠ_nc)` and `Qjn_p` likewise; `Qc_contacts = -|J| Ac (Π_nc+Π_pc)`. | Gives the same column set as COMSOL, and the totals are unchanged. With this bookkeeping η_E = 1 exactly (the reference books E_g + 3k_BT per pair in full). |
| R6 | `rect1` smoothing in the reference = C²-continuous quintic step over the full 10 µm transition zone. | COMSOL uses its own C² smoothed Heaviside. The difference is confined to a 10 µm band and is irrelevant for C9 (factor 2). |
| R7 | Reference CSVs carry extra columns `Vj, n_b, V_ohm, Pi_tot`. | Used by Fig. 7 and diagnostics. |
| R8 | `thermophotonic_cop(EQE, hw_eV, qV_eV)` returns the net cooling per pair (eV), as §11.4 defines; `thermophotonic_cools()` returns the condition. | The name comes from the spec. The function returns what the spec says it returns. |

## Post-processing (§8, §10)

| # | Change | Reason |
|---|---|---|
| P1 | If the Q_room = 0 crossing lies outside the ±20 mK `dT_sink` sweep, dT_max is extrapolated with the linear fit and marked "(extrap.)". | Q_room is exactly linear in dT_sink (one-way coupling, constant k), so the extrapolation is exact. Large-bias V1 points exceed the sweep. |
| P2 | Config-B-only runs (V5, V6) report dT_max = T_room - T_end (Config B). | For the symmetric 1D bar this equals the Config A dT_max exactly (proved in `tests/test_reference_model.py::test_configA_dTmax_equals_configB_end_drop`). |
| P3 | C5 uses τ_eff = 2·tau_long and n_i = 1e10 cm⁻³ (the value stated in C4). | See R2. |
| P4 | C7 also flags Config-B end cooling ≥ 0.1 K. `analyze.py`/`report.py` exit with code 2 and print **BUG**. | §0 rule 6 and the user instruction ("flag any net cooling exceeding 0.1 K as an immediate bug"). |
| P5 | Reference-model sanity checks R1-R4 are reported separately from C1-C9. | C1-C9 are defined on COMSOL output. Without COMSOL they are PENDING rather than faked. |
| P6 | Figures 1 and 9 are written as labelled placeholders / reference-only until COMSOL data exist. Fig. 3 shows the reference i-region source and states that the junction dip needs COMSOL. | The reference model does not compute band edges or the distributed junction dip. Fake curves are not drawn. |
| P7 | Fig. 7 plots the estimate n_b D_a Π_side / k at each run's own V_j, plus the Auger-limited upper bound (2/W_i)·sqrt(D_a/C_a). | §11.3 gives both. Using one V_j for every W_i would misplace the estimate, since short bars have a smaller ohmic drop. |
