# PIN-diode junction cooling: results summary

_Generated 2026-11-16T11:42:45 by `postprocess/report.py`._

Sign conventions: Q_room > 0 means the room is cooled. dT_max is the sink-minus-room temperature at which Q_room = 0 (Config A); 'none (room heated)' means Q_room < 0 already at dT_sink = 0. For Config-B-only runs (V5, V6), dT_max = T_room - T_end, which is exact for the symmetric 1D bar.

## 1. COMSOL results

**PENDING.** No COMSOL results were found in `results/<variant>/`. This table is filled in once you run `python comsol/python/build_model.py` and `python comsol/python/run_variants.py --set core` (or `comsol/java/build_and_run.bat`), then `python postprocess/report.py`.

| Variant | dT_max @0.4 V | best dT_max (VF) | Q_room(dT=0) @0.4 V | COP(dT=0) | COP(dT_max/2) | eta_E @0.4 V | T_end-T_room, Config B |
|---|---|---|---|---|---|---|---|
| V0 | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ |
| V1 | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ |

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
| C1 | Zero bias | PENDING | needs COMSOL results (results/<variant>/) |
| C2 | Energy balance | PENDING | needs COMSOL results (results/<variant>/) |
| C3 | Junction cooling exists | PENDING | needs COMSOL results (results/<variant>/) |
| C4 | Junction-cooling magnitude | PENDING | needs COMSOL results (results/<variant>/) |
| C5 | I-V benchmark (V0) | PENDING | needs COMSOL results (results/<variant>/) |
| C6 | Mesh convergence | PENDING | needs COMSOL results for V1 and V4 |
| C7 | Plausibility (|dT_max| < 0.1 K) | PENDING | needs COMSOL results (results/<variant>/) |
| C8 | Reverse bias | PENDING | needs COMSOL results (results/<variant>/) |
| C9 | COMSOL vs reference model | PENDING | needs COMSOL results for V0 and V1 |

### Reference-model sanity checks

| # | Check | Status | Detail |
|---|---|---|---|
| R1 | Zero bias (J = 0, T = T_room) | PASS | J(0) = 0.00e+00 A/m^2, T_P1 - T_room = 0.00e+00 K |
| R2 | Energy closure (eta_E = 1 for full bookkeeping) | PASS | max |eta_E - 1| = 0.00e+00 (need < 5e-3) |
| R3 | Plausibility (|dT_max| < 0.1 K) | PASS | reference: largest |dT_max| = 69.774 mK |
| R4 | Qualitative outcome (V0 ends warmer, V1 ends cooler) | PASS | Config B T_end - T_room at 0.4 V: V0 +2.115 mK, V1 -64.227 mK |

## 4. Figures

- [fig1_band_diagram](figures/fig1_band_diagram.png) ([pdf](figures/fig1_band_diagram.pdf)): Band diagram Ec, Ev, Efn, Efp at VF = 0 and 0.4 V (V0), zoomed on both junctions (placeholder: COMSOL results not available) _[none]_
- [fig2_carriers](figures/fig2_carriers.png) ([pdf](figures/fig2_carriers.pdf)): Electron and hole densities, V0 vs V1, VF = 0.4 V _[reference model]_
- [fig3_heat_source](figures/fig3_heat_source.png) ([pdf](figures/fig3_heat_source.pdf)): Q_tot(x) zoomed on 0-10 um and the mirror region with J·E and Q_rec, V0, VF = 0.4 V _[reference model]_
- [fig4_temperature_configB](figures/fig4_temperature_configB.png) ([pdf](figures/fig4_temperature_configB.pdf)): KEY FIGURE: T(x) - T_room in mK, Config B, V0 vs V1, VF = 0.4 V _[reference model]_
- [fig5_Qroom_vs_dTsink](figures/fig5_Qroom_vs_dTsink.png) ([pdf](figures/fig5_Qroom_vs_dTsink.pdf)): Q_room vs dT_sink (Config A), V0 vs V1, VF = 0.3/0.35/0.4 V, with dT_max markers _[reference model]_
- [fig6_dTmax_COP_vs_VF](figures/fig6_dTmax_COP_vs_VF.png) ([pdf](figures/fig6_dTmax_COP_vs_VF.pdf)): dT_max and COP vs VF (COP at dT = 0 and dT_max/2) _[reference model]_
- [fig7_V5_scaling](figures/fig7_V5_scaling.png) ([pdf](figures/fig7_V5_scaling.pdf)): V5: dT_max vs Wi for each tau_long, with the analytic bound n D_a Pi / k _[reference model]_
- [fig8_V6_heatmap](figures/fig8_V6_heatmap.png) ([pdf](figures/fig8_V6_heatmap.pdf)): V6: dT_max heat map over (w_rz, tau_short) _[reference model]_
- [fig9_comsol_vs_reference](figures/fig9_comsol_vs_reference.png) ([pdf](figures/fig9_comsol_vs_reference.pdf)): COMSOL (solid) vs reference model (dashed) for V0 and V1 _[reference model only]_
- [fig10_thermophotonic_map](figures/fig10_thermophotonic_map.png) ([pdf](figures/fig10_thermophotonic_map.pdf)): V10 thermophotonic stub: net cooling per pair eta_EQE*hw - qV over EQE and qV/hw (analytic) _[analytic]_

## 5. Conclusion

In the reference-model results at VF = 0.4 V, the device as drawn (V0, uniform lifetime) heats its junction ends by 2.115 mK relative to the sink in Config B. Config A gives Q_room = -0.507 mW and dT_max = none (room heated). Recombination heat flows back to the ends, so the room is heated. With the engineered central recombination zone (V1) the ends cool by 64.227 mK. Config A gives Q_room(dT=0) = 15.415 mW, COP = 0.81 and dT_max = 64.227 mK (extrap.). dT_max rises to 64.23 mK at VF = 0.400 V, the top of the Study 2 sweep. Junction cooling is therefore real but far below one kelvin, consistent with the estimate dT ~ n_b D_a Pi/k (Fig. 7). Stacking does not change this: see `results/cascade.md` for the number of series stages and the electrical power multiplier needed for 10 K. These numbers come from the COMSOL-independent reference model. The COMSOL results, and with them checks C1-C9, are pending (see 'Not executed').

## 6. Not executed

- COMSOL 6.3 was not reachable on the machine that generated this file, so stages 1-8, V0/V1 and the remaining variant matrix were not solved.
- As a result, checks C1-C9 are PENDING. Figures 1 and 9 are placeholders or reference-only.
- Before the first COMSOL run, the ⚠VERIFY API names must be confirmed (docs/VERIFY_API_NAMES.md).

## References

1. COMSOL Semiconductor Module User's Guide, "Nonisothermal Models" (simplified heat source; `semi.Q_tot`). https://doc.comsol.com/6.4/doc/com.comsol.help.semicond/semicond_ug_modeling.5.18.html
2. COMSOL Application Library, *Thermal Analysis of a Bipolar Transistor* (Semiconductor_Module/Transistors/bipolar_transistor_thermal).
3. G. K. Wachutka, "Rigorous thermodynamic treatment of heat generation and conduction in semiconductor device modeling," *IEEE Trans. CAD* 9(11), 1141-1149 (1990).
4. K. P. Pipe, R. J. Ram, A. Shakouri, "Bias-dependent Peltier coefficient and internal cooling in bipolar devices," *Phys. Rev. B* 66, 125316 (2002).
5. Ioffe Institute, *New Semiconductor Materials: Ge - Germanium* (band structure, electrical, thermal and recombination parameters at 300 K). https://www.ioffe.ru/SVA/NSM/Semicond/Ge/
6. S. M. Sze, K. K. Ng, *Physics of Semiconductor Devices*, 3rd ed., Wiley (2007), Appendix G.
7. C. Hilsum, "Simple empirical relationship between mobility and carrier concentration," *Electron. Lett.* 10, 259 (1974).
8. T. Sadi, I. Radevici, J. Oksanen, "Thermophotonic cooling with light-emitting diodes," *Nature Photonics* 14, 205 (2020).
