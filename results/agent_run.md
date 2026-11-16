# Agent run, 2026-11-16 (overnight, after pull of a8837ff)

**Outcome: stopped at the gate (step 4).** C2 (energy balance) fails for V0 at the two lowest
bias points (VF = 0.200 V and 0.225 V). The other gated checks (C1, C3, C4, C5, C7, C8, C9)
pass, with no BUG. Following the instructions, the remaining variants (V4, V2a/V2b/V3a/V3b,
V6, V5, V7a/V7b) were **not run**, and no parameter, check window or reference-model code was
changed.

## Steps

| Step | Command | Result |
|---|---|---|
| 1 | `git pull` (fast-forward to a8837ff) | OK |
| 1 | `python -m pytest -q` | PASS: 43 passed, 1 skipped |
| - | `python reference/reference_model.py`, `python reference/cascade_calculator.py` (CLAUDE.md step 3) | OK (exit 0) |
| 2 | `python comsol/python/build_model.py` | PASS: stages 1-8 OK. JN_X = `semi.JnX` and JP_X = `semi.JpX` resolved with their default names; no ApiNameError, no script fixes needed. Stage 4: J(0.4 V) = 2.8844 A/cm^2, I/(Ac\|J_X\|) = 1.0000 |
| 3 | `python comsol/python/run_variants.py --set core` | PASS: V0 (1049 s) and V1 (923 s) exported, no warnings |
| 3 | `python postprocess/report.py` | exit 0, no BUG |
| 4 | Gate (C1, C2, C3, C4, C5, C7, C8, C9 pass, no BUG) | **FAIL (C2)**. Stopped |
| 5 | Remaining variants | **Not run** (gate) |

## Checks C1-C9 (core set)

| # | Check | Status | Detail |
|---|---|---|---|
| C1 | Zero bias | PASS | V0 1.16e-07, V1 6.99e-08 (<1e-6); max\|T-T_room\| = 0 uK |
| C2 | Energy balance | **FAIL** | V0: eta_E - (1 - Vt/VF) in [-0.0000, +0.2175] for VF >= 0.2 (need \|.\| <= 0.03). V1: [+0.0009, +0.0073] (passes) |
| C3 | Junction cooling exists | PASS | V0 Qjn_n/Qjn_p max -2.55e-6 / -2.56e-6 W; V1 -4.68e-5 / -4.54e-5 W |
| C4 | Junction-cooling magnitude | PASS | V0 ratio 0.774-0.925; V1 0.980-0.997 (need 0.7-1.3) |
| C5 | I-V benchmark (V0) | PASS | J/J_ref 0.789-1.028 for 0.3-0.45 V |
| C6 | Mesh convergence | PENDING | needs V4, not run because of the gate |
| C7 | Plausibility | PASS | largest \|dT_max\| = 57.000 mK |
| C8 | Reverse bias | PASS | V0 Q_room = -1.08e-6 W, V1 -5.89e-5 W (need <= 0) |
| C9 | COMSOL vs reference | PASS | V0 27.242 vs 30.946 mK (0.88); V1 -57.000 vs -56.451 mK (1.01) |

Reference-model checks R1-R4: all PASS.

## V0 and V1 at VF = 0.4 V, COMSOL vs reference model

| Quantity | V0 COMSOL | V0 reference | V1 COMSOL | V1 reference |
|---|---|---|---|---|
| J (A/cm^2) | 2.884 | 2.943 | 4.390 | 4.757 |
| dT_max @0.4 V (Config A) | none (room heated) | none (room heated) | 57.000 mK (extrap.) | 56.451 mK (extrap.) |
| best dT_max (VF) | 0.060 mK (0.225 V) | 0.046 mK (0.225 V) | 57.000 mK (0.400 V) | 56.451 mK (0.400 V) |
| Q_room(dT=0) | -6.512 mW | -7.427 mW | 13.625 mW | 13.548 mW |
| COP(dT=0) | -0.564 | -0.631 | 0.776 | 0.712 |
| COP(dT_max/2) | - | - | 0.504 | 0.46 |
| eta_E | 0.9354 | 1.0000 (by construction) | 0.9368 | 1.0000 (by construction) |
| T_end - T_room, Config B | +27.242 mK | +30.946 mK | -57.000 mK | -56.451 mK |

## Diagnosis of the C2 failure

eta_E = (Qtot_int + Qc_contacts + Q_sr) / P_el, with Q_sr = Ac (Eg + 3kT)/q (|J_p(0)| + |J_n(Ltot)|),
the contact-recombination heat added in a8837ff. Per bias point (V0):

| VF (V) | J (A/cm^2) | eta_E | 1 - Vt/VF | deviation | Q_sr/P_el |
|---|---|---|---|---|---|
| 0.200 | 0.00826 | 1.0883 | 0.8707 | **+0.2175** | 0.388 |
| 0.225 | 0.0145 | 1.0941 | 0.8851 | **+0.2090** | 0.515 |
| 0.250 | 0.0264 | 0.8966 | 0.8966 | +0.0000 | 0.667 |
| 0.300 to 0.500 | 0.10 to 45.9 | | | +0.0000 (all points) | 0.59 to 1.11 |

- The failure is confined to V0 at VF = 0.200 and 0.225 V. From 0.250 V upward the balance closes
  to 4 digits. V1 passes at every point, because only 0.6-1.1 % of its power is contact
  recombination at 0.2-0.25 V (V0: 39-67 %).
- The sign is positive: at the lowest biases Q_sr **over-counts** the heat. Quantified from the
  earlier diagnosis run (V0, 0.2 V, same model): the energy actually missing from semi.Q_tot was
  2.81 W/m^2, while (|J_p(0)| + |J_n(Ltot)|)(Eg + 3kT)/q = 6.41 W/m^2. The 3.6 W/m^2 excess
  divided by P_el = 16.5 W/m^2 is 0.218, the deviation C2 reports. At 0.4 and 0.5 V the same
  comparison matched to 4 digits (11 064 vs 11 064 and 134 900 vs 134 900 W/m^2).
- So the energy released per minority carrier recombining at an ohmic contact is about
  Eg + 3kT in high injection, but only about 0.32 eV (2.81 W/m^2 / 8.68 A/m^2), roughly 0.44 of
  Eg + 3kT, at VF = 0.2 V. A likely reason (not verified): at low bias the minority current reaching
  the contacts is a diffusion current in the 2 um n+/p+ layers with quasi-Fermi levels pinned at
  the contact. The heat released there is set by the local quasi-Fermi-level split and band
  offsets, not by the full Eg + 3kT that the fixed E_pair assumes. A bias- or
  position-dependent energy per pair, or evaluating the contact heat from COMSOL's energy flux
  at the contact boundaries, would test this.
- Not the cause: the skipped Tref (semi temperature is fixed to T0) and semi.Un (hs1 =
  semi.Q_tot for V0/V1; U only enters the 'corrected' heat source).
- Not changed, per instructions: C2_tol (0.03), C2_VF_min (0.2), E_pair, the reference model.
  Possible decisions for the owner: correct the contact heat model for low injection, or decide
  whether C2 should apply from VF = 0.25 V. Either is a model or check change, so it was left
  to you.

## Failed variants

None. Only V0 and V1 ran; the other variants were not started because of the gate.

## Files changed in this run

| File | Why |
|---|---|
| `results/V0/*`, `results/V1/*` | COMSOL core-set export after the rebuild |
| `results/reference/**` | reference_model.py rerun (CLAUDE.md step 3). The V5/V6 reference folders, deleted in a8837ff, are regenerated by the current reference model; summary.md (V5/V6 tables, figs 7-8) is built from them |
| `results/cascade.md` | cascade_calculator.py rerun |
| `results/summary.md`, `results/analysis.json`, `results/figures/*` | report.py |
| `results/agent_run.md` | this report |

No changes to `config/`, `comsol/python/`, `postprocess/`, `reference/` or tests in this run.
`config/api_names_override.yaml` is unchanged (JN_X/JP_X needed no override).
`comsol/models/*.mph` were rebuilt locally and are not committed.
