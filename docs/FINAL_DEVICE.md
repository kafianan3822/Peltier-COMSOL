# Final device and extended sweep (0.6–1.5 V)

Files:

| File | Purpose |
|---|---|
| `config/final_device.yaml` | Run definitions (FINAL, V1x, FINAL_scan) and the extended sweeps |
| `comsol/python/run_final.py` | COMSOL driver (Driver A, MPh). Same base model and export code as `run_variants.py` |
| `reference/reference_model.py --set final` | COMSOL-independent reference curves (about 35 s) |
| `postprocess/final_report.py` | `results/final/summary_final.md` and figures F1–F7 in `results/final/figures/` |

Commands, from the project folder with the same Python environment as before:

```
python comsol/python/run_final.py --dry-run      # check: lists FINAL and V1x
python comsol/python/run_final.py                # FINAL + V1x in COMSOL (about 1-3 h)
python comsol/python/run_final.py --set all      # optional: + 6 zone-scan runs (Config B only)
python postprocess/final_report.py               # report + figures
```

`build_model.py` does **not** need to be run again; the base model `comsol/models/pin_peltier_base.mph` is reused.

---

## 1. Why this design

The 51-run matrix gave four findings that decide the design:

1. **Where the carriers recombine decides whether the device cools.** Without a recombination zone (V0) the room is heated. With one (V1) it is cooled.
2. **The zone has an optimum strength.** At 0.7 V the COMSOL V6 map peaked at 25 µm / 1 µs (1.18 mK, against 0.45 mK for V1). Too weak a zone lets recombination drift back to the junctions. Too strong a zone empties the i-region, which then turns resistive.
3. **The best ΔT was at the top of the old sweep** (V1: 2.38 mK at 0.8 V), so the true optimum was not resolved. Run over the full bias range, the reference model puts the optimum at 0.9–1.0 V. There, a **stronger** zone wins, because the zone has to compete with Auger recombination in the bulk, which grows as n³:

   | zone (reference model) | ΔT at 0.7 V | peak ΔT over VF |
   |---|---|---|
   | 100 µm / 1 µs (V1) | 0.94 mK | 28.4 mK at 0.93 V |
   | 25 µm / 1 µs (V6 best at 0.7 V) | 1.98 mK | 20.8 mK at 0.87 V |
   | **25 µm / 0.3 µs (FINAL)** | 1.37 mK | **32.4 mK at 0.92 V** |
   | 25 µm / 0.1 µs | 0.66 mK | 37.4 mK at 0.97 V |
   | 50 µm / 0.3 µs | 0.77 mK | 34.3 mK at 0.96 V |

   The peak landscape is flat (28–37 mK). COMSOL penalises strong zones more than the reference model does: the COMSOL/reference ratio is 0.35–0.41 for 0.1 µs zones and 0.59–0.63 for weak ones. 25 µm / 0.3 µs is therefore the compromise: within 13 % of the best reference point, with the lowest bias and power of the designs above 30 mK. `FINAL_scan` checks this choice in COMSOL itself.
4. **Modelling choices that change the answer by less than 10 %** (mesh 0.19 %, heat-source form 0.5 %, mobility model 8 %) do not change the design. Heavy-doping physics (FD + BGN, −14 %) is kept out for the reason given in §3.

**The trade made:** FINAL is *worse* than the V6 optimum at 0.7 V (reference 1.37 vs 1.98 mK) but better at its own optimum bias. The figure of merit is now the **peak** cooling over the bias range, not the cooling at 0.7 V.

---

## 2. Differences between V1 and FINAL

### 2.1 Device architecture

| Item | V1 | FINAL | Reason |
|---|---|---|---|
| i-region length W_i | 1 mm | 1 mm (same) | Geometry as built and shown. Per V5, shorter W_i gives the same ΔT with more heat flux but lower COP. |
| n⁺ / p⁺ layers | 2 µm, 10¹⁹ cm⁻³ | same | |
| Cross-section A_c | 1 mm² | same | |
| i-region background | 10¹² cm⁻³ acceptors | same | |
| Bulk lifetime τ_long | 1 ms | same | High-purity FZ Si. V5 showed only +9 % at 5 ms. |
| **Zone width w_rz** | **100 µm** | **25 µm** | Concentrates recombination in the centre (V6 and the peak scan above) |
| **Zone lifetime τ_short** | **1 µs** | **0.3 µs** | Strong enough to compete with bulk Auger at the 0.9–1.0 V optimum |
| Zone position and shape | centre, rectangle with 10 µm smoothed edges | same | |
| Zone sink strength S = w_rz/(2τ_short) per side | 5 000 cm/s | 4 170 cm/s | Integrated recombination is similar, but in a 4× narrower slab |
| **Mesh** | mesh_factor 1 (about 6 µm elements at the centre) | **mesh_factor 2** (about 3 µm) | A 25 µm zone needs at least 8 elements. V4 showed mesh_factor 2 changes ΔT by only 0.19 %. |

### 2.2 Physics models

| Model | V1 | FINAL | Reason / effect |
|---|---|---|---|
| Carrier statistics | Maxwell–Boltzmann | same | FD needs consistent contact Π formulas (§3) |
| Band-gap narrowing | off | same | Same reason; V2 shows −14 % on ΔT |
| Ionization | complete | same | |
| Lattice/impurity mobility | Arora (COMSOL library, M1) | same | |
| **Carrier–carrier scattering** | **off** | **Fletcher, on** | At the new optimum the i-region holds 10¹⁷–10¹⁸ cm⁻³ electrons *and* holes. Electron–hole scattering then lowers μ and D_a by tens of percent and raises the resistive drop V_i. It cannot be neglected above about 0.85 V. It ran successfully in V2. |
| SRH recombination | τ_n = τ_p = τ(x), mid-gap trap | same | |
| Auger | Dziewior–Schmid, folded exactly into τ_ax | same | Dominant above V_j ≈ 0.78 V |
| Radiative / surface recombination | none | none | Indirect gap; 1D model has no surfaces |
| **Heat source** | builtin `semi.Q_tot` = J·E + U(E_g + 3kT) | **corrected**: + k_B·T0·U | Closes the energy balance (η_E = 1.000 ± 0.002, V3). At high bias the 2 % error would no longer be negligible against the small Q_room. |
| Contact heat (M19) | Π_nc, Π_pc + minority recombination Π_rn, Π_rp | same | |
| Thermal coupling | one-way (semiconductor at T0 = 300 K) | same, **plus a validity flag** | Self-heating of more than 1 K is flagged (n_i rises by about 8 %/K) |
| Thermal conductivity | 148 W/m·K, constant | same | |

### 2.3 Simulation protocol

| Item | Matrix (V1) | FINAL / V1x |
|---|---|---|
| VF sweep, Studies 1, 3 (and 4) | 0 → 0.9 V, step 0.025 V | **0 → 1.5 V, step 0.01 V**, reported 0.6–1.5 V |
| VF sweep, Study 2 (Config A, ΔT_max) | 0 → 0.8 V | **0 → 1.5 V, step 0.01 V** |
| dT_sink list (Study 2) | −20…+20 mK, 17 values | **−50…+50 mK, 11 values** (Q_room is exactly linear in dT_sink, and the expected ΔT_max is up to about 30 mK) |
| Profiles | 0, 0.6, 0.7, 0.75, 0.8 V | 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0, 1.2, 1.5 V |
| Thermal configurations | A, B (C in V7) | A, B (Config C omitted: V7 showed it cannot go below ambient) |
| Reverse bias (C8) | yes | no (unchanged from V1) |
| Non-convergence | segregated, then half step | the same, then **VF_max lowered to 1.3 and then 1.1 V**; the report states the reached maximum |
| Comparison run | — | **V1x** = V1 unchanged, on the same extended sweep |
| Design check | — | **FINAL_scan** (optional): w_rz ∈ {25, 50} µm × τ_short ∈ {0.1, 0.3, 1} µs, Config B, final physics |

---

## 3. All assumptions of the final model

**Geometry and contacts**

1. 1D: current and heat flow only along x, uniform over A_c = 1 mm². No edges, no surface recombination, no current crowding.
2. Ideal ohmic contacts at x = 0 and x = L: zero contact resistance, infinite surface recombination velocity, no metal layer modelled.
3. Contact Peltier heat is added by hand (CHANGES M19). The Π values assume Boltzmann statistics and no BGN. This is why FD + BGN stays off: with FD + BGN this bookkeeping is wrong by about 5 % of P_el (V2, C2 fail).

**Carrier transport**

4. Drift–diffusion with Maxwell–Boltzmann statistics, complete ionization and no band-gap narrowing.
5. Mobility: Arora (lattice + impurity) plus Fletcher carrier–carrier scattering. No velocity saturation. The highest field is about 0.56 V/1 mm ≈ 6 V/cm, far below saturation.
6. SRH with a mid-gap trap and τ_n = τ_p = τ(x): bulk 1 ms, centre zone 0.3 µs over 25 µm with 10 µm smoothed edges. Auger with C_n = 2.8×10⁻³¹ and C_p = 9.9×10⁻³² cm⁶/s. No radiative recombination, no trap-assisted tunnelling.
7. Library silicon: N_c = 2.8×10¹⁹, N_v = 1.04×10¹⁹ cm⁻³ → n_i = 6.68×10⁹ cm⁻³ at 300 K, E_g = 1.12 eV.

**Heat**

8. Steady state (DC).
9. Heat source Q = J·E + U·(E_g + 3k_BT) + k_B·T0·U (corrected), plus the contact sinks of item 3. No Thomson heat.
10. One-way coupling. The semiconductor is solved at T0 = 300 K; the heat equation uses its heat source. Valid while |T − T_room| ≤ 1 K, which holds up to about 1.2 V in the reference model. Above that, currents and heats are indicative only.
11. Constant k = 148 W/m·K. Ideal isothermal sinks: Config A ends at T_room with the centre sink at T_room + dT_sink; Config B centre at T_room with insulated ends. No radiation or convection.

**Numerics**

12. Relative tolerance 10⁻⁶; continuation in VF from equilibrium.

---

## 4. What to expect, and how to read it

The reference model (`results/final/summary_final.md` before the COMSOL run) gives:

| | FINAL | V1x |
|---|---|---|
| ΔT at 0.7 V | 1.37 mK | 0.94 mK |
| **Peak ΔT** | **32.4 mK at 0.92 V** | 28.4 mK at 0.93 V |
| Q_room / COP / P_el at the peak | 19.2 mW / 0.20 / 94 mW | 16.8 mW / 0.20 / 85 mW |
| Cooling turns into heating at | ≈ 0.97 V | ≈ 0.98 V |
| J at 1.5 V | ≈ 300 A/cm² (3 A for 1 mm²) | ≈ 250 A/cm² |
| V_j at 1.5 V | 0.94 V (the junctions saturate; V_i takes the rest) | 0.93 V |

**COMSOL expectation:** the reference model overestimates by about 2× (n_i, and no Fletcher or heavy-doping physics). Expect a COMSOL peak of roughly **10–20 mK near 0.9–0.95 V**, with heating above about 1 V. Anything at or above 100 mK is flagged as a bug (plausibility check).

**Physics of the curve (Fig. F3):**
- Below the optimum, ΔT grows about as n_b ∝ e^{qV_j/2kT}.
- At the optimum, the Joule heat J²ρW grows faster than the Peltier term J·(V_bi − V_j). Two things drive this: Auger caps the carrier density, so the i-region resistance stops falling, and the junction barrier V_bi − V_j shrinks.
- Above about 1 V the device is simply a resistor that heats itself.

**Fig. F2** shows where the applied voltage goes. V_j saturates near 0.93 V, below V_bi, so every extra volt drops across the i-region.

The Java driver (Driver B) has not been extended to the final device. Use Driver A (Python), as for the matrix.
