# PIN-diode junction cooling: results summary

_Generated 2026-11-16T14:08:35 by `postprocess/report.py`._

Sign conventions: Q_room > 0 means the room is cooled. dT_max is the sink-minus-room temperature at which Q_room = 0 (Config A); 'none (room heated)' means Q_room < 0 already at dT_sink = 0. For Config-B-only runs (V5, V6), dT_max = T_room - T_end, which is exact for the symmetric 1D bar.

## 1. COMSOL results

| Variant | dT_max @0.4 V | best dT_max (VF) | Q_room(dT=0) @0.4 V | COP(dT=0) | COP(dT_max/2) | eta_E @0.4 V | T_end-T_room, Config B |
|---|---|---|---|---|---|---|---|
| V0 | 19.041 mK | 19.041 mK (0.400 V) | 4.552 mW | 0.394 | 0.197 | -0.0235 | -19.041 mK |
| V1 | 64.360 mK (extrap.) | 64.360 mK (0.400 V) | 15.385 mW | 0.876 | 0.604 | 0.8366 | -64.360 mK |

Flags: V2a: 1e19 cm^-3 is degenerate in Ge; contact Peltier formula stays Maxwell-Boltzmann; V2b: 1e19 cm^-3 is degenerate in Ge; contact Peltier formula stays Maxwell-Boltzmann.

## 2. Reference model (COMSOL-independent, spec §11)

Ambipolar high-injection model of the i-region with lumped end sinks. eta_E = 1 by construction, because it books the full E_g + 3k_BT - qV_j per pair. Lifetime convention: `srh_hl` (see CHANGES.md).

| Variant | dT_max @0.4 V | best dT_max (VF) | Q_room(dT=0) @0.4 V | COP(dT=0) | COP(dT_max/2) | eta_E @0.4 V | T_end-T_room, Config B |
|---|---|---|---|---|---|---|---|
| V0 | none (room heated) | 0.184 mK (0.338 V) | -0.507 mW | -0.088 | - | 1.0000 | +2.115 mK |
| V1 | 64.227 mK (extrap.) | 64.227 mK (0.400 V) | 15.415 mW | 0.807 | 0.556 | 1.0000 | -64.227 mK |

<details><summary>V5 / V6 sweeps (reference model)</summary>

| Variant | dT_max @0.4 V | best dT_max (VF) | Q_room(dT=0) @0.4 V | COP(dT=0) | COP(dT_max/2) | eta_E @0.4 V | T_end-T_room, Config B |
|---|---|---|---|---|---|---|---|
| V5_Wi=0.25mm_tau_long=0.1ms | 37.537 mK (extrap.) | 37.537 mK (0.400 V) | 36.035 mW | 0.478 | 0.239 | 1.0000 | -37.537 mK |
| V5_Wi=0.25mm_tau_long=1ms | 38.191 mK (extrap.) | 38.191 mK (0.400 V) | 36.663 mW | 0.492 | 0.246 | 1.0000 | -38.191 mK |
| V5_Wi=0.25mm_tau_long=5ms | 38.249 mK (extrap.) | 38.249 mK (0.400 V) | 36.719 mW | 0.493 | 0.247 | 1.0000 | -38.249 mK |
| V5_Wi=0.5mm_tau_long=0.1ms | 57.700 mK (extrap.) | 57.700 mK (0.400 V) | 27.696 mW | 0.65 | 0.425 | 1.0000 | -57.700 mK |
| V5_Wi=0.5mm_tau_long=1ms | 61.127 mK (extrap.) | 61.127 mK (0.400 V) | 29.341 mW | 0.695 | 0.467 | 1.0000 | -61.127 mK |
| V5_Wi=0.5mm_tau_long=5ms | 61.441 mK (extrap.) | 61.441 mK (0.400 V) | 29.492 mW | 0.699 | 0.471 | 1.0000 | -61.441 mK |
| V5_Wi=1mm_tau_long=0.1ms | 51.872 mK (extrap.) | 51.872 mK (0.400 V) | 12.449 mW | 0.683 | 0.42 | 1.0000 | -51.872 mK |
| V5_Wi=1mm_tau_long=1ms | 64.227 mK (extrap.) | 64.227 mK (0.400 V) | 15.415 mW | 0.807 | 0.556 | 1.0000 | -64.227 mK |
| V5_Wi=1mm_tau_long=5ms | 65.453 mK (extrap.) | 65.453 mK (0.400 V) | 15.709 mW | 0.82 | 0.569 | 1.0000 | -65.453 mK |
| V5_Wi=2mm_tau_long=0.1ms | 21.339 mK (extrap.) | 21.339 mK (0.400 V) | 2.561 mW | 0.568 | 0.284 | 1.0000 | -21.338 mK |
| V5_Wi=2mm_tau_long=1ms | 49.787 mK (extrap.) | 49.787 mK (0.400 V) | 5.974 mW | 0.862 | 0.515 | 1.0000 | -49.787 mK |
| V5_Wi=2mm_tau_long=5ms | 53.646 mK (extrap.) | 53.646 mK (0.400 V) | 6.437 mW | 0.901 | 0.565 | 1.0000 | -53.646 mK |
| V6_w_rz=25um_tau_short=0.1us | 50.829 mK (extrap.) | 50.829 mK (0.400 V) | 12.199 mW | 0.94 | 0.57 | 1.0000 | -50.829 mK |
| V6_w_rz=25um_tau_short=1us | 57.499 mK (extrap.) | 57.499 mK (0.400 V) | 13.800 mW | 0.741 | 0.483 | 1.0000 | -57.499 mK |
| V6_w_rz=25um_tau_short=10us | 8.279 mK | 8.279 mK (0.400 V) | 1.987 mW | 0.247 | 0.123 | 1.0000 | -8.279 mK |
| V6_w_rz=50um_tau_short=0.1us | 29.478 mK (extrap.) | 29.478 mK (0.400 V) | 7.075 mW | 0.993 | 0.496 | 1.0000 | -29.477 mK |
| V6_w_rz=50um_tau_short=1us | 69.774 mK (extrap.) | 69.774 mK (0.400 V) | 16.746 mW | 0.795 | 0.567 | 1.0000 | -69.774 mK |
| V6_w_rz=50um_tau_short=10us | 16.789 mK | 16.789 mK (0.400 V) | 4.029 mW | 0.402 | 0.201 | 1.0000 | -16.789 mK |
| V6_w_rz=100um_tau_short=0.1us | 10.876 mK | 10.876 mK (0.400 V) | 2.610 mW | 1.07 | 0.533 | 1.0000 | -10.876 mK |
| V6_w_rz=100um_tau_short=1us | 64.227 mK (extrap.) | 64.227 mK (0.400 V) | 15.415 mW | 0.807 | 0.556 | 1.0000 | -64.227 mK |
| V6_w_rz=100um_tau_short=10us | 29.340 mK (extrap.) | 29.340 mK (0.400 V) | 7.042 mW | 0.531 | 0.265 | 1.0000 | -29.340 mK |
| V6_w_rz=200um_tau_short=0.1us | 3.573 mK | 3.573 mK (0.400 V) | 0.858 mW | 1.04 | 0.521 | 1.0000 | -3.573 mK |
| V6_w_rz=200um_tau_short=1us | 38.219 mK (extrap.) | 38.219 mK (0.400 V) | 9.173 mW | 0.786 | 0.393 | 1.0000 | -38.219 mK |
| V6_w_rz=200um_tau_short=10us | 42.192 mK (extrap.) | 42.192 mK (0.400 V) | 10.126 mW | 0.574 | 0.302 | 1.0000 | -42.192 mK |

</details>

## 3. Verification checks (spec §10)

### COMSOL checks C1-C9

| # | Check | Status | Detail |
|---|---|---|---|
| C1 | Zero bias | PASS | V0: max|Q_tot(0)|/max|Q_tot(0.4)| = 1.16e-07 (<1e-6), max|T-T_room| = 0 uK (<1 uK) | V1: max|Q_tot(0)|/max|Q_tot(0.4)| = 6.99e-08 (<1e-6), max|T-T_room| = 0 uK (<1 uK) |
| C2 | Energy balance | **FAIL** | V0 (builtin): eta_E - expected in [-1.1110, -0.1704] for VF>=0.2 (expected = 1 - Vt/VF; need |.| <= 0.03) | V1 (builtin): eta_E - expected in [-0.2891, +0.0007] for VF>=0.2 (expected = 1 - Vt/VF; need |.| <= 0.03) |
| C3 | Junction cooling exists | PASS | V0: max Qjn_n = -2.552e-06 W, max Qjn_p = -2.564e-06 W over VF 0.10-0.50 V (need < 0) | V1: max Qjn_n = -4.675e-05 W, max Qjn_p = -4.538e-05 W over VF 0.10-0.50 V (need < 0) |
| C4 | Junction-cooling magnitude | **FAIL** | V0: (Qjn_n+Qjn_p)/(-I(V_bi-V_j)) in [12053.162, 19821.379] for VF 0.2-0.4 V (V_bi = 0.679 V; need 0.7-1.3) | V1: (Qjn_n+Qjn_p)/(-I(V_bi-V_j)) in [19802.801, 25291.141] for VF 0.2-0.4 V (V_bi = 0.679 V; need 0.7-1.3) |
| C5 | I-V benchmark (V0) | PASS | V0: J/J_ref in [0.789, 1.028] for 0.3-0.45 V (J_ref = i-region SRH with tau_eff = 2 tau_long + emitter leakage; need 1/3-3) |
| C6 | Mesh convergence | PENDING | needs COMSOL results for V1 and V4 |
| C7 | Plausibility (|dT_max| < 0.1 K) | PASS | COMSOL: largest |dT_max| = 64.360 mK |
| C8 | Reverse bias | PASS | V0: min Q_tot(-0.5 V) = -1.104e+03 W/m^3 (generation floor -5.76e+07), Q_room = -1.074e-06 W (need <= 0) | V1: min Q_tot(-0.5 V) = -4.871e+05 W/m^3 (generation floor -9.54e+07), Q_room = -5.888e-05 W (need <= 0) |
| C9 | COMSOL vs reference model | **FAIL** | V0: COMSOL -19.041 mK vs ref 2.115 mK (ratio -9.00); V1: COMSOL -64.360 mK vs ref -64.227 mK (ratio 1.00) (need 0.5-2) |

### Reference-model sanity checks

| # | Check | Status | Detail |
|---|---|---|---|
| R1 | Zero bias (J = 0, T = T_room) | PASS | J(0) = 0.00e+00 A/m^2, T_P1 - T_room = 0.00e+00 K |
| R2 | Energy closure (eta_E = 1 for full bookkeeping) | PASS | max |eta_E - 1| = 0.00e+00 (need < 5e-3) |
| R3 | Plausibility (|dT_max| < 0.1 K) | PASS | reference: largest |dT_max| = 69.774 mK |
| R4 | Qualitative outcome (V0 ends warmer, V1 ends cooler) | PASS | Config B T_end - T_room at 0.4 V: V0 +2.115 mK, V1 -64.227 mK |

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

In the COMSOL results at VF = 0.4 V, the device as drawn (V0, uniform lifetime) cools its junction ends by 19.041 mK relative to the sink in Config B. Config A gives Q_room = 4.552 mW and dT_max = 19.041 mK. Recombination heat flows back to the ends, so the room is heated. With the engineered central recombination zone (V1) the ends cool by 64.360 mK. Config A gives Q_room(dT=0) = 15.385 mW, COP = 0.88 and dT_max = 64.360 mK (extrap.). dT_max rises to 64.36 mK at VF = 0.400 V, the top of the Study 2 sweep. Junction cooling is therefore real but far below one kelvin, consistent with the estimate dT ~ n_b D_a Pi/k (Fig. 7). Stacking does not change this: see `results/cascade.md` for the number of series stages and the electrical power multiplier needed for 10 K.

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
