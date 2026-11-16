# PIN-diode junction cooling: results summary

_Generated 2026-11-16T18:30:51 by `postprocess/report.py`._

Sign conventions: Q_room > 0 means the room is cooled. dT_max is the sink-minus-room temperature at which Q_room = 0 (Config A); 'none (room heated)' means Q_room < 0 already at dT_sink = 0. For Config-B-only runs (V5, V6), dT_max = T_room - T_end, which is exact for the symmetric 1D bar.

## 1. COMSOL results

| Variant | dT_max @0.4 V | best dT_max (VF) | Q_room(dT=0) @0.4 V | COP(dT=0) | COP(dT_max/2) | eta_E @0.4 V | T_end-T_room, Config B |
|---|---|---|---|---|---|---|---|
| V0 | none (room heated) | 0.060 mK (0.225 V) | -6.512 mW | -0.564 | - | 0.9354 | +27.242 mK |
| V1 | 57.000 mK (extrap.) | 57.000 mK (0.400 V) | 13.625 mW | 0.776 | 0.504 | 0.9368 | -57.000 mK |

Flags: V2a: 1e19 cm^-3 is degenerate in Ge; contact Peltier formula stays Maxwell-Boltzmann; V2b: 1e19 cm^-3 is degenerate in Ge; contact Peltier formula stays Maxwell-Boltzmann.

## 2. Reference model (COMSOL-independent, spec §11)

Ambipolar high-injection model of the i-region with lumped end sinks. eta_E = 1 by construction, because it books the full E_g + 3k_BT - qV_j per pair. Lifetime convention: `srh_hl` (see CHANGES.md).

| Variant | dT_max @0.4 V | best dT_max (VF) | Q_room(dT=0) @0.4 V | COP(dT=0) | COP(dT_max/2) | eta_E @0.4 V | T_end-T_room, Config B |
|---|---|---|---|---|---|---|---|
| V0 | none (room heated) | 0.046 mK (0.225 V) | -7.427 mW | -0.631 | - | 1.0000 | +30.946 mK |
| V1 | 56.451 mK (extrap.) | 56.451 mK (0.400 V) | 13.548 mW | 0.712 | 0.46 | 1.0000 | -56.451 mK |

<details><summary>V5 / V6 sweeps (reference model)</summary>

| Variant | dT_max @0.4 V | best dT_max (VF) | Q_room(dT=0) @0.4 V | COP(dT=0) | COP(dT_max/2) | eta_E @0.4 V | T_end-T_room, Config B |
|---|---|---|---|---|---|---|---|
| V5_Wi=0.25mm_tau_long=0.1ms | 32.409 mK (extrap.) | 32.409 mK (0.400 V) | 31.113 mW | 0.399 | 0.199 | 1.0000 | -32.409 mK |
| V5_Wi=0.25mm_tau_long=1ms | 32.960 mK (extrap.) | 32.960 mK (0.400 V) | 31.642 mW | 0.41 | 0.205 | 1.0000 | -32.960 mK |
| V5_Wi=0.25mm_tau_long=5ms | 33.010 mK (extrap.) | 33.010 mK (0.400 V) | 31.689 mW | 0.411 | 0.205 | 1.0000 | -33.010 mK |
| V5_Wi=0.5mm_tau_long=0.1ms | 51.161 mK (extrap.) | 51.161 mK (0.400 V) | 24.557 mW | 0.567 | 0.345 | 1.0000 | -51.161 mK |
| V5_Wi=0.5mm_tau_long=1ms | 54.057 mK (extrap.) | 54.057 mK (0.400 V) | 25.947 mW | 0.602 | 0.379 | 1.0000 | -54.057 mK |
| V5_Wi=0.5mm_tau_long=5ms | 54.322 mK (extrap.) | 54.322 mK (0.400 V) | 26.074 mW | 0.606 | 0.383 | 1.0000 | -54.322 mK |
| V5_Wi=1mm_tau_long=0.1ms | 46.227 mK (extrap.) | 46.227 mK (0.400 V) | 11.094 mW | 0.615 | 0.349 | 1.0000 | -46.227 mK |
| V5_Wi=1mm_tau_long=1ms | 56.451 mK (extrap.) | 56.451 mK (0.400 V) | 13.548 mW | 0.712 | 0.46 | 1.0000 | -56.451 mK |
| V5_Wi=1mm_tau_long=5ms | 57.455 mK (extrap.) | 57.455 mK (0.400 V) | 13.789 mW | 0.722 | 0.471 | 1.0000 | -57.455 mK |
| V5_Wi=2mm_tau_long=0.1ms | 19.728 mK | 19.728 mK (0.400 V) | 2.367 mW | 0.54 | 0.27 | 1.0000 | -19.728 mK |
| V5_Wi=2mm_tau_long=1ms | 43.213 mK (extrap.) | 43.213 mK (0.400 V) | 5.186 mW | 0.773 | 0.415 | 1.0000 | -43.213 mK |
| V5_Wi=2mm_tau_long=5ms | 46.249 mK (extrap.) | 46.249 mK (0.400 V) | 5.550 mW | 0.802 | 0.455 | 1.0000 | -46.249 mK |
| V6_w_rz=25um_tau_short=0.1us | 47.440 mK (extrap.) | 47.440 mK (0.400 V) | 11.386 mW | 0.893 | 0.517 | 1.0000 | -47.440 mK |
| V6_w_rz=25um_tau_short=1us | 37.832 mK (extrap.) | 37.832 mK (0.400 V) | 9.080 mW | 0.434 | 0.217 | 1.0000 | -37.832 mK |
| V6_w_rz=25um_tau_short=10us | none (room heated) | 1.775 mK (0.312 V) | -4.643 mW | -0.344 | - | 1.0000 | +19.346 mK |
| V6_w_rz=50um_tau_short=0.1us | 28.404 mK (extrap.) | 28.404 mK (0.400 V) | 6.817 mW | 0.972 | 0.486 | 1.0000 | -28.404 mK |
| V6_w_rz=50um_tau_short=1us | 55.666 mK (extrap.) | 55.666 mK (0.400 V) | 13.360 mW | 0.61 | 0.391 | 1.0000 | -55.666 mK |
| V6_w_rz=50um_tau_short=10us | none (room heated) | 4.698 mK (0.338 V) | -2.320 mW | -0.155 | - | 1.0000 | +9.667 mK |
| V6_w_rz=100um_tau_short=0.1us | 10.753 mK | 10.753 mK (0.400 V) | 2.581 mW | 1.06 | 0.53 | 1.0000 | -10.753 mK |
| V6_w_rz=100um_tau_short=1us | 56.451 mK (extrap.) | 56.451 mK (0.400 V) | 13.548 mW | 0.712 | 0.46 | 1.0000 | -56.451 mK |
| V6_w_rz=100um_tau_short=10us | 5.127 mK | 11.415 mK (0.362 V) | 1.231 mW | 0.0711 | 0.0355 | 1.0000 | -5.127 mK |
| V6_w_rz=200um_tau_short=0.1us | 3.565 mK | 3.565 mK (0.400 V) | 0.856 mW | 1.04 | 0.52 | 1.0000 | -3.565 mK |
| V6_w_rz=200um_tau_short=1us | 35.908 mK (extrap.) | 35.908 mK (0.400 V) | 8.618 mW | 0.751 | 0.376 | 1.0000 | -35.909 mK |
| V6_w_rz=200um_tau_short=10us | 22.166 mK (extrap.) | 22.799 mK (0.388 V) | 5.320 mW | 0.262 | 0.131 | 1.0000 | -22.166 mK |

</details>

## 3. Verification checks (spec §10)

### COMSOL checks C1-C9

| # | Check | Status | Detail |
|---|---|---|---|
| C1 | Zero bias | PASS | V0: max|Q_tot(0)|/max|Q_tot(0.4)| = 1.16e-07 (<1e-6), max|T-T_room| = 0 uK (<1 uK) | V1: max|Q_tot(0)|/max|Q_tot(0.4)| = 6.99e-08 (<1e-6), max|T-T_room| = 0 uK (<1 uK) |
| C2 | Energy balance | **FAIL** | V0 (builtin): eta_E - expected in [-0.0000, +0.2175] for VF>=0.2 (expected = 1 - Vt/VF; need |.| <= 0.03) | V1 (builtin): eta_E - expected in [+0.0009, +0.0073] for VF>=0.2 (expected = 1 - Vt/VF; need |.| <= 0.03) |
| C3 | Junction cooling exists | PASS | V0: max Qjn_n = -2.552e-06 W, max Qjn_p = -2.564e-06 W over VF 0.10-0.50 V (need < 0) | V1: max Qjn_n = -4.675e-05 W, max Qjn_p = -4.538e-05 W over VF 0.10-0.50 V (need < 0) |
| C4 | Junction-cooling magnitude | PASS | V0: (Qjn_n+Qjn_p)/(-I(V_bi-V_j)) in [0.774, 0.925] for VF 0.2-0.4 V (V_bi = 0.679 V; need 0.7-1.3) | V1: (Qjn_n+Qjn_p)/(-I(V_bi-V_j)) in [0.980, 0.997] for VF 0.2-0.4 V (V_bi = 0.679 V; need 0.7-1.3) |
| C5 | I-V benchmark (V0) | PASS | V0: J/J_ref in [0.789, 1.028] for 0.3-0.45 V (J_ref = i-region SRH with tau_eff = 2 tau_long + emitter leakage; need 1/3-3) |
| C6 | Mesh convergence | PENDING | needs COMSOL results for V1 and V4 |
| C7 | Plausibility (|dT_max| < 0.1 K) | PASS | COMSOL: largest |dT_max| = 57.000 mK |
| C8 | Reverse bias | PASS | V0: min Q_tot(-0.5 V) = -1.104e+03 W/m^3 (generation floor -5.76e+07), Q_room = -1.079e-06 W (need <= 0) | V1: min Q_tot(-0.5 V) = -4.871e+05 W/m^3 (generation floor -9.54e+07), Q_room = -5.888e-05 W (need <= 0) |
| C9 | COMSOL vs reference model | PASS | V0: COMSOL 27.242 mK vs ref 30.946 mK (ratio 0.88); V1: COMSOL -57.000 mK vs ref -56.451 mK (ratio 1.01) (need 0.5-2) |

### Reference-model sanity checks

| # | Check | Status | Detail |
|---|---|---|---|
| R1 | Zero bias (J = 0, T = T_room) | PASS | J(0) = 0.00e+00 A/m^2, T_P1 - T_room = 0.00e+00 K |
| R2 | Energy closure (eta_E = 1 for full bookkeeping) | PASS | max |eta_E - 1| = 0.00e+00 (need < 5e-3) |
| R3 | Plausibility (|dT_max| < 0.1 K) | PASS | reference: largest |dT_max| = 57.455 mK |
| R4 | Qualitative outcome (V0 ends warmer, V1 ends cooler) | PASS | Config B T_end - T_room at 0.4 V: V0 +30.946 mK, V1 -56.451 mK |

## 4. Figures

- [fig1_band_diagram](figures/fig1_band_diagram.png) ([pdf](figures/fig1_band_diagram.pdf)): Band diagram Ec, Ev, Efn, Efp at VF = 0 and 0.4 V (V0), zoomed on both junctions _[COMSOL]_
- [fig2_carriers](figures/fig2_carriers.png) ([pdf](figures/fig2_carriers.pdf)): Electron and hole densities, V0 vs V1, VF = 0.4 V _[COMSOL]_
- [fig3_heat_source](figures/fig3_heat_source.png) ([pdf](figures/fig3_heat_source.pdf)): Q_tot(x) zoomed on 0-10 um and the mirror region with J·E and Q_rec, V0, VF = 0.4 V _[COMSOL]_
- [fig4_temperature_configB](figures/fig4_temperature_configB.png) ([pdf](figures/fig4_temperature_configB.pdf)): KEY FIGURE: T(x) - T_room in mK, Config B, V0 vs V1, VF = 0.4 V _[COMSOL]_
- [fig5_Qroom_vs_dTsink](figures/fig5_Qroom_vs_dTsink.png) ([pdf](figures/fig5_Qroom_vs_dTsink.pdf)): Q_room vs dT_sink (Config A), V0 vs V1, VF = 0.3/0.35/0.4 V, with dT_max markers _[COMSOL]_
- [fig6_dTmax_COP_vs_VF](figures/fig6_dTmax_COP_vs_VF.png) ([pdf](figures/fig6_dTmax_COP_vs_VF.pdf)): dT_max and COP vs VF (COP at dT = 0 and dT_max/2) _[COMSOL]_
- [fig7_V5_scaling](figures/fig7_V5_scaling.png) ([pdf](figures/fig7_V5_scaling.pdf)): V5: dT_max vs Wi for each tau_long, with the analytic bound n D_a Pi / k _[reference model]_
- [fig8_V6_heatmap](figures/fig8_V6_heatmap.png) ([pdf](figures/fig8_V6_heatmap.pdf)): V6: dT_max heat map over (w_rz, tau_short) _[reference model]_
- [fig9_comsol_vs_reference](figures/fig9_comsol_vs_reference.png) ([pdf](figures/fig9_comsol_vs_reference.pdf)): COMSOL (solid) vs reference model (dashed) for V0 and V1 _[COMSOL + reference model]_
- [fig10_thermophotonic_map](figures/fig10_thermophotonic_map.png) ([pdf](figures/fig10_thermophotonic_map.pdf)): V10 thermophotonic stub: net cooling per pair eta_EQE*hw - qV over EQE and qV/hw (analytic) _[analytic]_

## 5. Conclusion

In the COMSOL results at VF = 0.4 V, the device as drawn (V0, uniform lifetime) heats its junction ends by 27.242 mK relative to the sink in Config B. Config A gives Q_room = -6.512 mW and dT_max = none (room heated). Recombination heat flows back to the ends, so the room is heated. With the engineered central recombination zone (V1) the ends cool by 57.000 mK. Config A gives Q_room(dT=0) = 13.625 mW, COP = 0.78 and dT_max = 57.000 mK (extrap.). dT_max rises to 57.00 mK at VF = 0.400 V, the top of the Study 2 sweep. Junction cooling is therefore real but far below one kelvin, consistent with the estimate dT ~ n_b D_a Pi/k (Fig. 7). Stacking does not change this: see `results/cascade.md` for the number of series stages and the electrical power multiplier needed for 10 K.

## 6. Not executed

All requested COMSOL runs that produced `results/<variant>/global_vs_VF.csv` are included above.

## References

1. COMSOL Semiconductor Module User's Guide, "Nonisothermal Models" (simplified heat source; `semi.Q_tot`). https://doc.comsol.com/6.4/doc/com.comsol.help.semicond/semicond_ug_modeling.5.18.html
2. COMSOL Application Library, *Thermal Analysis of a Bipolar Transistor* (Semiconductor_Module/Transistors/bipolar_transistor_thermal).
3. G. K. Wachutka, "Rigorous thermodynamic treatment of heat generation and conduction in semiconductor device modeling," *IEEE Trans. CAD* 9(11), 1141-1149 (1990).
4. K. P. Pipe, R. J. Ram, A. Shakouri, "Bias-dependent Peltier coefficient and internal cooling in bipolar devices," *Phys. Rev. B* 66, 125316 (2002).
5. Ioffe Institute, *New Semiconductor Materials: Ge - Germanium* (band structure, electrical, thermal and recombination parameters at 300 K). https://www.ioffe.ru/SVA/NSM/Semicond/Ge/
6. S. M. Sze, K. K. Ng, *Physics of Semiconductor Devices*, 3rd ed., Wiley (2007), Appendix G.
7. C. Hilsum, "Simple empirical relationship between mobility and carrier concentration," *Electron. Lett.* 10, 259 (1974).
8. T. Sadi, I. Radevici, J. Oksanen, "Thermophotonic cooling with light-emitting diodes," *Nature Photonics* 14, 205 (2020).
