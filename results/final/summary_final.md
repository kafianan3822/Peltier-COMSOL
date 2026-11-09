# Final device: extended sweep 0.6-1.5 V

_Generated 2026-11-09T14:54:45 by `postprocess/final_report.py`._

Design and all differences from V1: `docs/FINAL_DEVICE.md`. FINAL = 25 µm / 0.3 µs central recombination zone, carrier-carrier (Fletcher) scattering, corrected heat source. V1x = V1 unchanged, on the same extended sweep.

> **COMSOL results not found.** Everything below is the COMSOL-independent reference model. Run `python comsol/python/run_final.py`, then this script again.

## 1. Headline numbers

| Device | source | dT at 0.7 V | peak dT (VF) | Q_room at peak | COP at peak | P_el at peak | J at 1.5 V |
|---|---|---|---|---|---|---|---|
| FINAL | reference | 1.369 mK | 32.454 mK (0.92 V) | 19.213 mW | 0.203 | 94.4 mW | 295.8 A/cm² |
| V1x | reference | 0.943 mK | 28.419 mK (0.93 V) | 16.824 mW | 0.199 | 84.7 mW | 252.7 A/cm² |

## FINAL (reference model)

| VF (V) | J (A/cm²) | I (mA) | V_j (V) | V_i (V) | P_el (mW) | Q_room (mW) | dT = T_room − T_end (mK) | COP | eta_E | validity |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.60 | 0.02331 | 0.2331 | 0.520 | 0.080 | 0.1399 | +0.1405 | +0.2373 | 1 | 1.0000 | ok |
| 0.70 | 0.1612 | 1.612 | 0.620 | 0.080 | 1.128 | +0.8105 | +1.369 | 0.718 | 1.0000 | ok |
| 0.75 | 0.4239 | 4.239 | 0.670 | 0.080 | 3.18 | +1.918 | +3.241 | 0.603 | 1.0000 | ok |
| 0.80 | 1.114 | 11.14 | 0.720 | 0.080 | 8.91 | +4.468 | +7.548 | 0.501 | 1.0000 | ok |
| 0.85 | 2.906 | 29.06 | 0.769 | 0.081 | 24.7 | +9.952 | +16.81 | 0.403 | 1.0000 | ok |
| 0.90 | 7.306 | 73.06 | 0.814 | 0.086 | 65.75 | +18.03 | +30.46 | 0.274 | 1.0000 | ok |
| 0.95 | 16.26 | 162.6 | 0.849 | 0.101 | 154.5 | +12.62 | +21.31 | 0.0817 | 1.0000 | ok |
| 1.00 | 30.25 | 302.5 | 0.871 | 0.129 | 302.5 | -33.44 | -56.48 | -0.111 | 1.0000 | ok |
| 1.10 | 69.63 | 696.3 | 0.897 | 0.203 | 765.9 | -264.5 | -446.9 | -0.345 | 1.0000 | ok |
| 1.20 | 118.8 | 1188 | 0.912 | 0.288 | 1426 | -644.3 | -1088 | -0.452 | 1.0000 | self-heating 1.1 K |
| 1.30 | 174 | 1740 | 0.922 | 0.378 | 2263 | -1138 | -1922 | -0.503 | 1.0000 | self-heating 1.9 K |
| 1.40 | 233.4 | 2334 | 0.930 | 0.470 | 3268 | -1725 | -2913 | -0.528 | 1.0000 | self-heating 2.9 K |
| 1.50 | 295.8 | 2958 | 0.936 | 0.564 | 4436 | -2393 | -4043 | -0.539 | 1.0000 | self-heating 4 K |

- **Energy balance (corrected heat source):** eta_E in [1.0000, 1.0000] over the valid range, required [0.98, 1.02]: **PASS**.
- **Junction cooling (Qjn < 0):** present from 0.30 to 1.50 V.
- **Plausibility:** largest cooling 32.454 mK (< 100 mK required): **PASS**.
- **One-way coupling:** valid up to 1.18 V; above that the device self-heats by more than 1 K and n_i (about +8 %/K) is no longer that of 300 K, so currents and heats there are indicative only.

## V1x (reference model)

| VF (V) | J (A/cm²) | I (mA) | V_j (V) | V_i (V) | P_el (mW) | Q_room (mW) | dT = T_room − T_end (mK) | COP | eta_E | validity |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.60 | 0.01697 | 0.1697 | 0.500 | 0.100 | 0.1018 | +0.09767 | +0.165 | 0.959 | 1.0000 | ok |
| 0.70 | 0.1173 | 1.173 | 0.600 | 0.100 | 0.8214 | +0.5581 | +0.9427 | 0.679 | 1.0000 | ok |
| 0.75 | 0.3086 | 3.086 | 0.650 | 0.100 | 2.314 | +1.313 | +2.218 | 0.567 | 1.0000 | ok |
| 0.80 | 0.811 | 8.11 | 0.700 | 0.100 | 6.488 | +3.041 | +5.137 | 0.469 | 1.0000 | ok |
| 0.85 | 2.123 | 21.23 | 0.749 | 0.101 | 18.04 | +6.825 | +11.53 | 0.378 | 1.0000 | ok |
| 0.90 | 5.415 | 54.15 | 0.797 | 0.103 | 48.73 | +13.59 | +22.96 | 0.279 | 1.0000 | ok |
| 0.95 | 12.48 | 124.8 | 0.836 | 0.114 | 118.6 | +15.84 | +26.77 | 0.134 | 1.0000 | ok |
| 1.00 | 24.01 | 240.1 | 0.862 | 0.138 | 240.1 | -9.663 | -16.32 | -0.0402 | 1.0000 | ok |
| 1.10 | 57.3 | 573 | 0.890 | 0.210 | 630.3 | -180.7 | -305.2 | -0.287 | 1.0000 | ok |
| 1.20 | 99.41 | 994.1 | 0.906 | 0.294 | 1193 | -485.1 | -819.5 | -0.407 | 1.0000 | ok |
| 1.30 | 147.1 | 1471 | 0.917 | 0.383 | 1912 | -891.1 | -1505 | -0.466 | 1.0000 | self-heating 1.5 K |
| 1.40 | 198.5 | 1985 | 0.925 | 0.475 | 2779 | -1380 | -2331 | -0.497 | 1.0000 | self-heating 2.3 K |
| 1.50 | 252.7 | 2527 | 0.932 | 0.568 | 3790 | -1940 | -3276 | -0.512 | 1.0000 | self-heating 3.3 K |

- **Energy balance (builtin heat source):** eta_E in [1.0000, 1.0000] over the valid range, required [0.93, 1.01]: **PASS**.
- **Junction cooling (Qjn < 0):** present from 0.30 to 1.50 V.
- **Plausibility:** largest cooling 28.419 mK (< 100 mK required): **PASS**.
- **One-way coupling:** valid up to 1.22 V; above that the device self-heats by more than 1 K and n_i (about +8 %/K) is no longer that of 300 K, so currents and heats there are indicative only.

## Zone scan (Config B, peak over VF)

| w_rz | tau_short | COMSOL peak dT (VF) | reference peak dT (VF) |
|---|---|---|---|
| 25[um] | 0.1[us] | - mK (- V) | 37.302 mK (0.97 V) |
| 25[um] | 0.3[us] | - mK (- V) | 32.454 mK (0.92 V) |
| 25[um] | 1[us] | - mK (- V) | 20.758 mK (0.87 V) |
| 50[um] | 0.1[us] | - mK (- V) | 35.902 mK (1.05 V) |
| 50[um] | 0.3[us] | - mK (- V) | 34.244 mK (0.96 V) |
| 50[um] | 1[us] | - mK (- V) | 26.862 mK (0.90 V) |

## Figures

- [F1_IV](figures/F1_IV.png): Current density vs applied voltage (log scale); dotted line: V_j where Auger recombination overtakes SRH (n* = (C tau_eff)^-1/2) _[reference model]_
- [F2_voltage_split](figures/F2_voltage_split.png): Junction voltage V_j = VF - V_i (thick) and i-region drop V_i (thin) vs VF _[reference model]_
- [F3_dT_vs_VF](figures/F3_dT_vs_VF.png): End cooling T_room - T_end (Config B; equal to dT_max of Config A for the symmetric bar) vs VF; markers: optimum _[reference model]_
- [F4_Qroom_COP](figures/F4_Qroom_COP.png): Q_room(dT_sink = 0) and COP vs VF (Config A) _[reference model]_
- [F5_heat_budget](figures/F5_heat_budget.png): FINAL: electrical power, released heat and junction cooling; energy-balance ratio eta_E for both devices _[reference model]_
- [F6_T_profiles](figures/F6_T_profiles.png): FINAL: temperature along the bar (Config B, centre held at T_room) _[reference model]_
- [F7_zone_scan](figures/F7_zone_scan.png): Peak end cooling (over VF) vs zone lifetime for two zone widths _[reference model]_

Notes: dT = T_room − T_end in Config B equals dT_max of Config A for the symmetric 1D bar. The reference model has no carrier-carrier scattering, no heavy-doping physics and n_i = 9.65e9 cm^-3 (COMSOL library 6.68e9), so it overestimates the cooling by about 2x (matrix runs: COMSOL/reference = 0.35-0.63).
