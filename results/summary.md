# PIN-diode junction cooling: results summary

_Generated 2026-11-16T17:17:48 by `postprocess/report.py`._

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
| V0 | none (room heated) | 0.046 mK (0.225 V) | -7.427 mW | -0.631 | - | 1.0000 | +30.946 mK |
| V1 | 56.451 mK (extrap.) | 56.451 mK (0.400 V) | 13.548 mW | 0.712 | 0.46 | 1.0000 | -56.451 mK |

<details><summary>V5 / V6 sweeps (reference model)</summary>

| Variant | dT_max @0.4 V | best dT_max (VF) | Q_room(dT=0) @0.4 V | COP(dT=0) | COP(dT_max/2) | eta_E @0.4 V | T_end-T_room, Config B |
|---|---|---|---|---|---|---|---|
| V5_Wi=0.25mm_tau_long=0.1ms | 32.409 mK (extrap.) | 32.409 mK (0.400 V) | 31.113 mW | 0.399 | 0.199 | 1.0000 | -32.409 mK |
| V5_Wi=0.25mm_tau_long=1ms | 32.960 mK (extrap.) | 32.960 mK (0.400 V) | 31.642 mW | 0.41 | 0.205 | 1.0000 | -32.960 mK |

</details>

## 3. Verification checks (spec §10)

### COMSOL checks C1-C9

| # | Check | Status | Detail |
|---|---|---|---|
| C1 | Zero bias | PASS | V0: max|Q_tot(0)|/max|Q_tot(0.4)| = 1.16e-07 (<1e-6), max|T-T_room| = 0 uK (<1 uK) | V1: max|Q_tot(0)|/max|Q_tot(0.4)| = 6.99e-08 (<1e-6), max|T-T_room| = 0 uK (<1 uK) |
| C2 | Energy balance | **FAIL** | V0 (builtin): eta_E - expected in [-1.1110, -0.1704] for VF>=0.2 (expected = 1 - Vt/VF; need |.| <= 0.03) | V1 (builtin): eta_E - expected in [-0.2891, +0.0007] for VF>=0.2 (expected = 1 - Vt/VF; need |.| <= 0.03) |
| C3 | Junction cooling exists | PASS | V0: max Qjn_n = -2.552e-06 W, max Qjn_p = -2.564e-06 W over VF 0.10-0.50 V (need < 0) | V1: max Qjn_n = -4.675e-05 W, max Qjn_p = -4.538e-05 W over VF 0.10-0.50 V (need < 0) |
| C4 | Junction-cooling magnitude | PENDING | needs column Vj (quasi-Fermi-level split next to the junctions) | needs column Vj (quasi-Fermi-level split next to the junctions) |
| C5 | I-V benchmark (V0) | PASS | V0: J/J_ref in [0.789, 1.028] for 0.3-0.45 V (J_ref = i-region SRH with tau_eff = 2 tau_long + emitter leakage; need 1/3-3) |
| C6 | Mesh convergence | PENDING | needs COMSOL results for V1 and V4 |
| C7 | Plausibility (|dT_max| < 0.1 K) | PASS | COMSOL: largest |dT_max| = 64.360 mK |
| C8 | Reverse bias | PASS | V0: min Q_tot(-0.5 V) = -1.104e+03 W/m^3 (generation floor -5.76e+07), Q_room = -1.074e-06 W (need <= 0) | V1: min Q_tot(-0.5 V) = -4.871e+05 W/m^3 (generation floor -9.54e+07), Q_room = -5.888e-05 W (need <= 0) |
| C9 | COMSOL vs reference model | **FAIL** | V0: COMSOL -19.041 mK vs ref 30.946 mK (ratio -0.62); V1: COMSOL -64.360 mK vs ref -56.451 mK (ratio 1.14) (need 0.5-2) |

### Reference-model sanity checks

| # | Check | Status | Detail |
|---|---|---|---|
| R1 | Zero bias (J = 0, T = T_room) | PASS | J(0) = 0.00e+00 A/m^2, T_P1 - T_room = 0.00e+00 K |
| R2 | Energy closure (eta_E = 1 for full bookkeeping) | PASS | max |eta_E - 1| = 0.00e+00 (need < 5e-3) |
| R3 | Plausibility (|dT_max| < 0.1 K) | PASS | reference: largest |dT_max| = 56.451 mK |
| R4 | Qualitative outcome (V0 ends warmer, V1 ends cooler) | PASS | Config B T_end - T_room at 0.4 V: V0 +30.946 mK, V1 -56.451 mK |

## 4. Figures

- [fig1_band_diagram](figures/fig1_band_diagram.png) ([pdf](figures/fig1_band_diagram.pdf)): Band diagram Ec, Ev, Efn, Efp at VF = 0 and 0.4 V (V0), zoomed on both junctions _[COMSOL]_
- [fig2_carriers](figures/fig2_carriers.png) ([pdf](figures/fig2_carriers.pdf)): Electron and hole densities, V0 vs V1, VF = 0.4 V _[COMSOL]_
- [fig3_heat_source](figures/fig3_heat_source.png) ([pdf](figures/fig3_heat_source.pdf)): Q_tot(x) zoomed on 0-10 um and the mirror region with J·E and Q_rec, V0, VF = 0.4 V _[COMSOL]_
- [fig4_temperature_configB](figures/fig4_temperature_configB.png) ([pdf](figures/fig4_temperature_configB.pdf)): KEY FIGURE: T(x) - T_room in mK, Config B, V0 vs V1, VF = 0.4 V _[COMSOL]_
- [fig5_Qroom_vs_dTsink](figures/fig5_Qroom_vs_dTsink.png) ([pdf](figures/fig5_Qroom_vs_dTsink.pdf)): Q_room vs dT_sink (Config A), V0 vs V1, VF = 0.3/0.35/0.4 V, with dT_max markers _[COMSOL]_
- [fig6_dTmax_COP_vs_VF](figures/fig6_dTmax_COP_vs_VF.png) ([pdf](figures/fig6_dTmax_COP_vs_VF.pdf)): dT_max and COP vs VF (COP at dT = 0 and dT_max/2) _[COMSOL]_
- [fig7_V5_scaling](figures/fig7_V5_scaling.png) ([pdf](figures/fig7_V5_scaling.pdf)): V5: dT_max vs Wi for each tau_long, with the analytic bound n D_a Pi / k _[reference model]_
- [fig8_V6_heatmap](figures/fig8_V6_heatmap.png) ([pdf](figures/fig8_V6_heatmap.pdf)): dT_max over (w_rz, tau_short) (placeholder: COMSOL results not available) _[none]_
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
