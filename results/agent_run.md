# Agent run, 2026-11-17 (solver-tolerance diagnosis, then full variant set)

**Outcome:** The C2 failure from 2026-11-16 was caused by an unconverged stationary solver
at low bias, not by physics. `sweeps.rtol` was tightened from 1e-6 to 1e-8, the one config change
the owner authorised. The core gate then passed, and all variant groups ran.
Two V7 runs failed and were skipped.
On the full set, C2 is **FAIL** again, but only for V2a/V2b and V5 at Wi = 2 mm. V0 and V1 pass.
This needs a decision by the owner (see "Open issues").

## Steps

| Step | Command | Result |
|---|---|---|
| Part 1 | in-memory diagnosis (scratch script, model not saved): V0 and V1, Study 1 at rtol 1e-6 / 1e-8 / 1e-10 | rtol 1e-8 makes C2 pass; 0.4 V values unchanged (table below) |
| Part 2 | `config/params_base.yaml`: `sweeps.rtol` 1e-6 -> 1e-8 | done (loosest of the tested values that passes) |
| Part 2 | `write_params_txt.py`, `sync_java_api_names.py` | OK (`comsol/java/model_config.txt` regenerated; Java API names already up to date) |
| Part 2 | `python -m pytest -q` | PASS: 43 passed, 1 skipped |
| Part 2 | `build_model.py` | PASS: stages 1-8, exit 0 (known warnings only: Tref skipped, `ht.tfluxx` fallback) |
| Part 2 | `run_variants.py --set core`, `report.py` | exit 0, no BUG |
| Gate | C1, C2, C3, C4, C5, C7, C8, C9 for V0/V1, no BUG | **PASS** |
| 5 | `--ids V4`, report | exit 0 / 0 (2098 s) |
| 5 | `--ids V2a,V2b,V3a,V3b`, report | exit 0 / 0 (4834 s) |
| 5 | `--ids V6`, report | exit 0 / 0 (12 runs, 2852 s) |
| 5 | `--ids V5`, report | exit 0 / 0 (12 runs, 2870 s) |
| 5 | `--ids V7a,V7b`, report | exit 0 / 0 (18 runs, 2 failed, 5522 s) |

report.py never exited with code 2, so no check reported BUG.

## Part 1: diagnosis (V0 and V1, Study 1, model not saved)

V_bi = 0.67890 V, taken from V_ifield(VF = 0). Units: J.E and J(VF - V_bi) in W/m^2. Continuity is
max over x of | |J_X(x)| - J | / J.
The solve times (whole VF sweep) were: V0 56 / 60 / 63 s, V1 51 / 61 / 65 s for rtol 1e-6 / 1e-8 / 1e-10.

| V0, VF (V) | rtol | eta_E - (1 - Vt/VF) | J.E integral | J(VF - V_bi) | continuity |
|---|---|---|---|---|---|
| 0.15 | 1e-6 | +0.2215 | -13.906 | -14.841 | 4.1e-1 |
| 0.20 | 1e-6 | +0.2175 | -35.952 | -39.545 | 5.8e-1 |
| 0.225 | 1e-6 | +0.2090 | -59.053 | -65.872 | 6.7e-1 |
| 0.2375 | 1e-6 | +0.2010 | -76.621 | -85.909 | 7.0e-1 |
| 0.25 | 1e-6 | +0.0000 | -113.06 | -113.05 | 3.0e-5 |
| 0.40 | 1e-6 | +0.0000 | -8045.2 | -8044.6 | 3.0e-7 |
| 0.15 | 1e-8 | -0.0002 | -14.839 | -14.841 | 4.0e-4 |
| 0.20 | 1e-8 | -0.0000 | -39.545 | -39.545 | 1.4e-4 |
| 0.225 | 1e-8 | +0.0000 | -65.877 | -65.872 | 6.4e-5 |
| 0.2375 | 1e-8 | -0.0000 | -85.911 | -85.909 | 5.5e-5 |
| 0.25 | 1e-8 | +0.0000 | -113.06 | -113.05 | 3.0e-5 |
| 0.40 | 1e-8 | +0.0000 | -8045.2 | -8044.6 | 3.0e-7 |
| all | 1e-10 | identical to 1e-8 to the digits shown | | | |

- At 1e-6 the solver accepted solutions for V0 at VF <= 0.2375 V in which the current density varies by 40-70 %
  along the bar. J.E then differs from J(VF - V_bi), and the heat integral is too large by
  about 0.2 P_el. At 1e-8 the current is continuous to about 1e-4 and C2 closes to within 2e-4.
- **This corrects my diagnosis of 2026-11-16.** The "0.32 eV per contact pair at 0.2 V" figure came from the same
  unconverged 1e-6 solution. The contact-heat term (Eg + 3kT per pair) is not the cause.
- V1 at 1e-6 was also slightly unconverged at low bias (continuity 0.5-2 %, C2 dev up to +0.0073).
  At 1e-8 that becomes 1e-5 and +0.0031.
- 0.4 V check: J, the J.E integral, Q_tot and C2 are identical for V0 and V1 at all three tolerances. After the
  rebuild and core rerun, every column of `global_vs_VF.csv` and `float_vs_VF.csv` at 0.4 V was
  compared with the 2026-11-16 export. The largest relative change was 1.4e-10.
- 1e-7 was not tested. 1e-8 is the loosest of the three tolerances you specified.

## Checks C1-C9 (full set, final report)

| # | Check | Status | Detail |
|---|---|---|---|
| C1 | Zero bias | PASS | V0 1.16e-07, V1 6.99e-08; max\|T-T_room\| = 0 uK |
| C2 | Energy balance | **FAIL** | V0 [-0.0001, +0.0000], V1 [+0.0009, +0.0031], V3a/V3b/V4/V6/V7 within 0.009. **Fails:** V2a [-0.134, -0.054], V2b [-0.131, -0.053], V5 Wi=2mm tau_long=1ms [+0.012, +0.042], V5 Wi=2mm tau_long=5ms [+0.013, +0.043] (V5 Wi=2mm 0.1ms passes at +0.027) |
| C3 | Junction cooling exists | PASS | V0 max Qjn -2.68e-6 W, V1 -4.54e-5 W |
| C4 | Junction-cooling magnitude | PASS | V0 0.774-0.961, V1 0.980-0.998 |
| C5 | I-V benchmark (V0) | PASS | J/J_ref 0.789-1.028 |
| C6 | Mesh convergence | PASS | V4 vs V1: dT_max 0.01 %, Qjn_n 0.04 %, Qjn_p 0.04 % (need < 2 %) |
| C7 | Plausibility | PASS | largest \|dT_max\| = 65.072 mK (V2b) |
| C8 | Reverse bias | PASS | V0 Q_room -1.08e-6 W, V1 -5.89e-5 W |
| C9 | COMSOL vs reference | PASS | V0 27.242 vs 30.946 mK (0.88); V1 -57.000 vs -56.451 mK (1.01) |

Reference-model checks R1-R4: all PASS. At the gate (core set only), C2 passed for both V0 and V1.

## V0 and V1 at VF = 0.4 V, COMSOL vs reference model

| Quantity | V0 COMSOL | V0 reference | V1 COMSOL | V1 reference |
|---|---|---|---|---|
| J (A/cm^2) | 2.884 | 2.943 | 4.390 | 4.757 |
| dT_max @0.4 V (Config A) | none (room heated) | none (room heated) | 57.000 mK (extrap.) | 56.451 mK (extrap.) |
| best dT_max (VF) | 0.062 mK (0.225 V) | 0.046 mK (0.225 V) | 57.000 mK (0.400 V) | 56.451 mK (0.400 V) |
| Q_room(dT=0) | -6.512 mW | -7.427 mW | 13.625 mW | 13.548 mW |
| COP(dT=0) | -0.564 | -0.631 | 0.776 | 0.712 |
| COP(dT_max/2) | - | - | 0.504 | 0.46 |
| eta_E | 0.9354 | 1.0000 (by construction) | 0.9368 | 1.0000 (by construction) |
| T_end - T_room, Config B | +27.242 mK | +30.946 mK | -57.000 mK | -56.451 mK |

The only change from 2026-11-16 is V0's best dT_max: 0.060 mK became 0.062 mK. That point is at 0.225 V, a low-bias point that is now converged.

## Failed variants

| Variant | Failure |
|---|---|
| V7a_h_lat=1e3Wperm2K_w_wall=200um | std_lat (Config C) failed at the first sweep parameter. Newton: max iterations. Segregated fallback: "relative residual (1.1e-06) is greater than the relative tolerance". Halved-step fallback failed the same way. Logged and skipped |
| V7b_h_lat=1e3Wperm2K_w_wall=200um | same failure, same residual 1.1e-6 |

Both failed variants have an empty results folder, which is not committed. The other 16 V7 runs and all
V2-V6 runs exported. A residual of 1.1e-6 would have been accepted at the old rtol of 1e-6. The new
tolerance is therefore the likely trigger, combined with a linear-solver warning. This was not verified,
because these two variants were not rerun at 1e-6.

## Open issues for the owner (nothing changed)

1. **C2 fails for V2a/V2b** (1e19 cm^-3 emitters): eta_E is 0.05-0.13 below 1 - Vt/VF. report.py already
   flags 1e19 cm^-3 as degenerate in Ge, while the contact Peltier coefficient (Qc_contacts) still
   uses the Maxwell-Boltzmann formula. That is a plausible cause, not verified.
2. **C2 fails for V5 at Wi = 2 mm with tau_long = 1 or 5 ms** (deviation up to +0.043). The deviation
   grows with Wi. A longer bar with high injection may still be less converged, or have a larger
   ohmic or contact share. Not diagnosed.
3. The two V7 Config C runs at h_lat = 1e3 W/m^2K, w_wall = 200 um did not converge at rtol 1e-8
   (see above).

## Files changed in this run

| File | Why |
|---|---|
| `config/params_base.yaml` | `sweeps.rtol` 1e-6 -> 1e-8 (authorised; Part 1 diagnosis) |
| `comsol/java/model_config.txt` | regenerated by `write_params_txt.py` (`sweep.rtol 1e-8`) |
| `results/V0/*`, `results/V1/*` | core-set rerun at rtol 1e-8 (0.4 V unchanged; low-bias points now converged) |
| `results/V2a`, `V2b`, `V3a`, `V3b`, `V4`, `V5_*` (12), `V6_*` (12), `V7a_*`/`V7b_*` (16) | new variant exports |
| `results/summary.md`, `results/analysis.json`, `results/figures/*` | report.py after each group |
| `results/agent_run.md` | this report |

`comsol/params.txt` and `comsol/java/variants_flat.txt` were also rewritten but are unchanged in content.
There were no script, test, check or reference-model changes, and `config/api_names_override.yaml` is unchanged.
`comsol/models/*.mph` were rebuilt locally and are not committed.
