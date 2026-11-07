# PIN-diode junction cooling: results summary

_Generated 2026-11-07T16:15:30 by `postprocess/report.py`._

Sign conventions: Q_room > 0 means the room is cooled. dT_max is the sink-minus-room temperature at which Q_room = 0 (Config A); 'none (room heated)' means Q_room < 0 already at dT_sink = 0. For Config-B-only runs (V5, V6), dT_max = T_room - T_end, which is exact for the symmetric 1D bar. Config-C-only runs (V7) are listed in their own table (1b).

## 1. COMSOL results

**PENDING.** No COMSOL results were found in `results/<variant>/`. This table is filled in once you run `python comsol/python/build_model.py` and `python comsol/python/run_variants.py --set core` (or `comsol/java/build_and_run.bat`), then `python postprocess/report.py`.

| Variant | dT_max @0.7 V | best dT_max (VF) | Q_room(dT=0) @0.7 V | COP(dT=0) | COP(dT_max/2) | eta_E @0.7 V | T_end-T_room, Config B |
|---|---|---|---|---|---|---|---|
| V0 | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ |
| V1 | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ |

### 1b. Config C: lateral sink (V7, reference model)

Ends insulated, heat removed sideways from the i-region by h_lat·(P/A)·(T − T_out), except within w_wall of each junction. There is no reservoir colder than T_out, so the ends can only fall below ambient if the local Peltier dip is larger than the overall heating of the bar by P_el, which is about P_el/(h_lat·P·L_sink) (lumped column). T_end − T_out < 0 means the ends are below ambient. The Config A/B columns of the parent device (V0 for V7a, V1 for V7b) are in the table above.

| Variant | device | h_lat (W/m²K) | w_wall (µm) | T_end − T_out @0.7 V | T_centre − T_out | dip = T_end − T_centre | lumped P_el/(h_lat·P·L_sink) | lowest T_end − T_out over VF | reference T_end − T_out |
|---|---|---|---|---|---|---|---|---|---|
| V7a_h_lat=1e3Wperm2K_w_wall=0um | V0 (uniform) | 1e+03 | 0 | +98.179 mK | +98.412 mK | -0.234 mK | 98.334 mK | never below ambient | - mK |
| V7a_h_lat=1e3Wperm2K_w_wall=50um | V0 (uniform) | 1e+03 | 50 | +109.142 mK | +109.343 mK | -0.201 mK | 109.260 mK | never below ambient | - mK |
| V7a_h_lat=1e3Wperm2K_w_wall=200um | V0 (uniform) | 1e+03 | 200 | +163.858 mK | +163.959 mK | -0.101 mK | 163.890 mK | never below ambient | - mK |
| V7a_h_lat=1e4Wperm2K_w_wall=0um | V0 (uniform) | 1e+04 | 0 | +9.678 mK | +9.910 mK | -0.233 mK | 9.833 mK | never below ambient | - mK |
| V7a_h_lat=1e4Wperm2K_w_wall=50um | V0 (uniform) | 1e+04 | 50 | +10.782 mK | +10.981 mK | -0.200 mK | 10.926 mK | never below ambient | - mK |
| V7a_h_lat=1e4Wperm2K_w_wall=200um | V0 (uniform) | 1e+04 | 200 | +16.296 mK | +16.397 mK | -0.101 mK | 16.389 mK | never below ambient | - mK |
| V7a_h_lat=1e5Wperm2K_w_wall=0um | V0 (uniform) | 1e+05 | 0 | +0.834 mK | +1.055 mK | -0.222 mK | 0.983 mK | never below ambient | - mK |
| V7a_h_lat=1e5Wperm2K_w_wall=50um | V0 (uniform) | 1e+05 | 50 | +0.949 mK | +1.142 mK | -0.194 mK | 1.093 mK | never below ambient | - mK |
| V7a_h_lat=1e5Wperm2K_w_wall=200um | V0 (uniform) | 1e+05 | 200 | +1.540 mK | +1.641 mK | -0.101 mK | 1.639 mK | never below ambient | - mK |
| V7b_h_lat=1e3Wperm2K_w_wall=0um | V1 (rz on) | 1e+03 | 0 | +204.565 mK | +206.200 mK | -1.636 mK | 205.343 mK | never below ambient | - mK |
| V7b_h_lat=1e3Wperm2K_w_wall=50um | V1 (rz on) | 1e+03 | 50 | +227.410 mK | +228.977 mK | -1.566 mK | 228.159 mK | never below ambient | - mK |
| V7b_h_lat=1e3Wperm2K_w_wall=200um | V1 (rz on) | 1e+03 | 200 | +341.480 mK | +342.839 mK | -1.359 mK | 342.238 mK | never below ambient | - mK |
| V7b_h_lat=1e4Wperm2K_w_wall=0um | V1 (rz on) | 1e+04 | 0 | +19.759 mK | +21.386 mK | -1.627 mK | 20.534 mK | never below ambient | - mK |
| V7b_h_lat=1e4Wperm2K_w_wall=50um | V1 (rz on) | 1e+04 | 50 | +22.014 mK | +23.574 mK | -1.560 mK | 22.816 mK | never below ambient | - mK |
| V7b_h_lat=1e4Wperm2K_w_wall=200um | V1 (rz on) | 1e+04 | 200 | +33.339 mK | +34.696 mK | -1.357 mK | 34.224 mK | never below ambient | - mK |
| V7b_h_lat=1e5Wperm2K_w_wall=0um | V1 (rz on) | 1e+05 | 0 | +1.318 mK | +2.863 mK | -1.545 mK | 2.053 mK | never below ambient | - mK |
| V7b_h_lat=1e5Wperm2K_w_wall=50um | V1 (rz on) | 1e+05 | 50 | +1.503 mK | +3.003 mK | -1.500 mK | 2.282 mK | never below ambient | - mK |
| V7b_h_lat=1e5Wperm2K_w_wall=200um | V1 (rz on) | 1e+05 | 200 | +2.533 mK | +3.872 mK | -1.339 mK | 3.422 mK | never below ambient | - mK |

Flags: V2a: Q_tot inside doped layers less reliable with BGN; V2b: Q_tot inside doped layers less reliable with BGN.

## 2. Reference model (COMSOL-independent, spec §11)

Ambipolar high-injection model of the i-region with lumped end sinks. eta_E = 1 by construction, because it books the full E_g + 3k_BT - qV_j per pair. Lifetime convention: `srh_hl` (see CHANGES.md).

| Variant | dT_max @0.7 V | best dT_max (VF) | Q_room(dT=0) @0.7 V | COP(dT=0) | COP(dT_max/2) | eta_E @0.7 V | T_end-T_room, Config B |
|---|---|---|---|---|---|---|---|
| V0 | none (room heated) | 0.002 mK (0.550 V) | -0.058 mW | -0.148 | - | 1.0000 | +0.098 mK |
| V1 | 0.943 mK | 5.138 mK (0.800 V) | 0.558 mW | 0.679 | 0.34 | 1.0000 | -0.943 mK |

<details><summary>V5 / V6 sweeps (reference model)</summary>

| Variant | dT_max @0.7 V | best dT_max (VF) | Q_room(dT=0) @0.7 V | COP(dT=0) | COP(dT_max/2) | eta_E @0.7 V | T_end-T_room, Config B |
|---|---|---|---|---|---|---|---|
| V5_Wi=0.25mm_tau_long=0.1ms | 1.069 mK | 4.538 mK (0.800 V) | 2.532 mW | 0.371 | 0.185 | 1.0000 | -1.069 mK |
| V5_Wi=0.25mm_tau_long=1ms | 1.132 mK | 4.950 mK (0.800 V) | 2.680 mW | 0.39 | 0.195 | 1.0000 | -1.132 mK |
| V5_Wi=0.25mm_tau_long=5ms | 1.138 mK | 4.988 mK (0.800 V) | 2.694 mW | 0.391 | 0.196 | 1.0000 | -1.138 mK |
| V5_Wi=0.5mm_tau_long=0.1ms | 1.022 mK | 5.086 mK (0.800 V) | 1.210 mW | 0.511 | 0.256 | 1.0000 | -1.022 mK |
| V5_Wi=0.5mm_tau_long=1ms | 1.257 mK | 6.564 mK (0.800 V) | 1.488 mW | 0.587 | 0.293 | 1.0000 | -1.257 mK |
| V5_Wi=0.5mm_tau_long=5ms | 1.280 mK | 6.710 mK (0.800 V) | 1.515 mW | 0.594 | 0.297 | 1.0000 | -1.280 mK |
| V5_Wi=1mm_tau_long=0.1ms | 0.393 mK | 1.850 mK (0.800 V) | 0.233 mW | 0.448 | 0.224 | 1.0000 | -0.393 mK |
| V5_Wi=1mm_tau_long=1ms | 0.943 mK | 5.138 mK (0.800 V) | 0.558 mW | 0.679 | 0.34 | 1.0000 | -0.943 mK |
| V5_Wi=1mm_tau_long=5ms | 1.017 mK | 5.597 mK (0.800 V) | 0.602 mW | 0.707 | 0.354 | 1.0000 | -1.017 mK |
| V5_Wi=2mm_tau_long=0.1ms | 0.009 mK | 0.030 mK (0.800 V) | 0.003 mW | 0.279 | 0.139 | 1.0000 | -0.009 mK |
| V5_Wi=2mm_tau_long=1ms | 0.481 mK | 2.612 mK (0.800 V) | 0.142 mW | 0.668 | 0.334 | 1.0000 | -0.481 mK |
| V5_Wi=2mm_tau_long=5ms | 0.671 mK | 3.759 mK (0.800 V) | 0.199 mW | 0.764 | 0.382 | 1.0000 | -0.671 mK |
| V6_w_rz=25um_tau_short=0.1us | 0.655 mK | 3.701 mK (0.800 V) | 0.388 mW | 0.782 | 0.391 | 1.0000 | -0.655 mK |
| V6_w_rz=25um_tau_short=1us | 1.981 mK | 10.415 mK (0.800 V) | 1.173 mW | 0.657 | 0.329 | 1.0000 | -1.981 mK |
| V6_w_rz=25um_tau_short=10us | 0.753 mK | 2.050 mK (0.775 V) | 0.446 mW | 0.429 | 0.214 | 1.0000 | -0.752 mK |
| V6_w_rz=50um_tau_short=0.1us | 0.197 mK | 1.132 mK (0.800 V) | 0.117 mW | 0.85 | 0.425 | 1.0000 | -0.197 mK |
| V6_w_rz=50um_tau_short=1us | 1.627 mK | 8.779 mK (0.800 V) | 0.963 mW | 0.675 | 0.337 | 1.0000 | -1.627 mK |
| V6_w_rz=50um_tau_short=10us | 1.222 mK | 4.841 mK (0.800 V) | 0.724 mW | 0.513 | 0.256 | 1.0000 | -1.222 mK |
| V6_w_rz=100um_tau_short=0.1us | 0.005 mK | 0.010 mK (0.800 V) | 0.003 mW | 1.07 | 0.534 | 1.0000 | -0.005 mK |
| V6_w_rz=100um_tau_short=1us | 0.943 mK | 5.138 mK (0.800 V) | 0.558 mW | 0.679 | 0.34 | 1.0000 | -0.943 mK |
| V6_w_rz=100um_tau_short=10us | 1.612 mK | 7.426 mK (0.800 V) | 0.954 mW | 0.544 | 0.272 | 1.0000 | -1.612 mK |
| V6_w_rz=200um_tau_short=0.1us | 0.001 mK | 0.001 mK (0.800 V) | 0.001 mW | 1 | 0.5 | 1.0000 | -0.001 mK |
| V6_w_rz=200um_tau_short=1us | 0.167 mK | 0.915 mK (0.800 V) | 0.099 mW | 0.696 | 0.348 | 1.0000 | -0.167 mK |
| V6_w_rz=200um_tau_short=10us | 1.572 mK | 7.538 mK (0.800 V) | 0.930 mW | 0.511 | 0.256 | 1.0000 | -1.572 mK |

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
| R3 | Plausibility (|dT_max| < 0.1 K) | PASS | reference: largest |dT_max| = 10.415 mK |
| R4 | Qualitative outcome (V0 ends warmer, V1 ends cooler) | PASS | Config B T_end - T_room at 0.7 V: V0 +0.098 mK, V1 -0.943 mK |

## 4. Figures

- [fig1_band_diagram](figures/fig1_band_diagram.png) ([pdf](figures/fig1_band_diagram.pdf)): Band diagram Ec, Ev, Efn, Efp at VF = 0 and 0.7 V (V0), zoomed on both junctions (placeholder: COMSOL results not available) _[none]_
- [fig2_carriers](figures/fig2_carriers.png) ([pdf](figures/fig2_carriers.pdf)): Electron and hole densities, V0 vs V1, VF = 0.7 V _[reference model]_
- [fig3_heat_source](figures/fig3_heat_source.png) ([pdf](figures/fig3_heat_source.pdf)): Q_tot(x) zoomed on 0-10 um and the mirror region with J·E and Q_rec, V0, VF = 0.7 V _[reference model]_
- [fig4_temperature_configB](figures/fig4_temperature_configB.png) ([pdf](figures/fig4_temperature_configB.pdf)): KEY FIGURE: T(x) - T_room in mK, Config B, V0 vs V1, VF = 0.7 V _[reference model]_
- [fig5_Qroom_vs_dTsink](figures/fig5_Qroom_vs_dTsink.png) ([pdf](figures/fig5_Qroom_vs_dTsink.pdf)): Q_room vs dT_sink (Config A), V0 vs V1, VF = 0.65/0.70/0.75 V, with dT_max markers _[reference model]_
- [fig6_dTmax_COP_vs_VF](figures/fig6_dTmax_COP_vs_VF.png) ([pdf](figures/fig6_dTmax_COP_vs_VF.pdf)): dT_max and COP vs VF (COP at dT = 0 and dT_max/2) _[reference model]_
- [fig7_V5_scaling](figures/fig7_V5_scaling.png) ([pdf](figures/fig7_V5_scaling.pdf)): V5: dT_max vs Wi for each tau_long, with the analytic bound n D_a Pi / k _[reference model]_
- [fig8_V6_heatmap](figures/fig8_V6_heatmap.png) ([pdf](figures/fig8_V6_heatmap.pdf)): V6: dT_max heat map over (w_rz, tau_short) _[reference model]_
- [fig9_comsol_vs_reference](figures/fig9_comsol_vs_reference.png) ([pdf](figures/fig9_comsol_vs_reference.pdf)): COMSOL (solid) vs reference model (dashed) for V0 and V1 _[reference model only]_
- [fig10_thermophotonic_map](figures/fig10_thermophotonic_map.png) ([pdf](figures/fig10_thermophotonic_map.pdf)): V10 thermophotonic stub: net cooling per pair eta_EQE*hw - qV over EQE and qV/hw (analytic) _[analytic]_
- [fig11_V7_lateral](figures/fig11_V7_lateral.png) ([pdf](figures/fig11_V7_lateral.pdf)): V7 (Config C): end temperature relative to ambient vs h_lat and w_wall, with the lumped heating estimate P_el/(h_lat P L_sink) _[reference model]_

## 5. Conclusion

In the reference-model results at VF = 0.7 V, the device as drawn (V0, uniform lifetime) heats its junction ends by 0.098 mK relative to the sink in Config B. Config A gives Q_room = -0.058 mW and dT_max = none (room heated). Recombination heat flows back to the ends, so the room is heated. With the engineered central recombination zone (V1) the ends cool by 0.943 mK. Config A gives Q_room(dT=0) = 0.558 mW, COP = 0.68 and dT_max = 0.943 mK. dT_max rises to 5.14 mK at VF = 0.800 V, the top of the Study 2 sweep. Junction cooling is therefore real but milli-kelvin in size, consistent with the estimate dT ~ n_b D_a Pi/k (Fig. 7). With only a lateral sink (Config C, V7) the junction ends sit between +0.834 mK (V7a_h_lat=1e5Wperm2K_w_wall=0um) and +341.480 mK (V7b_h_lat=1e3Wperm2K_w_wall=200um) relative to the ambient T_out at 0.7 V. None of them is below ambient, because the whole electrical power has to leave through the same sink that defines the ambient, and the bar heats up by about P_el/(h_lat P L_sink). That is more than the local Peltier dip at the ends. Stacking does not change this: see `results/cascade.md` (about 2000 series stages for 10 K, with an electrical power multiplier of about 10^1556 at COP = 0.2 per stage). These numbers come from the COMSOL-independent reference model. The COMSOL results, and with them checks C1-C9, are pending (see 'Not executed').

## 6. Not executed

- COMSOL 6.3 was not reachable on the machine that generated this file, so stages 1-8, V0/V1 and the remaining variant matrix were not solved.
- As a result, checks C1-C9 are PENDING. Figures 1 and 9 are placeholders or reference-only.
- Before the first COMSOL run, the ⚠VERIFY API names must be confirmed (docs/VERIFY_API_NAMES.md).

## References

1. COMSOL Semiconductor Module User's Guide, "Nonisothermal Models" (simplified heat source; `semi.Q_tot`). https://doc.comsol.com/6.4/doc/com.comsol.help.semicond/semicond_ug_modeling.5.18.html
2. COMSOL Application Library, *Thermal Analysis of a Bipolar Transistor* (Semiconductor_Module/Transistors/bipolar_transistor_thermal).
3. G. K. Wachutka, "Rigorous thermodynamic treatment of heat generation and conduction in semiconductor device modeling," *IEEE Trans. CAD* 9(11), 1141-1149 (1990).
4. K. P. Pipe, R. J. Ram, A. Shakouri, "Bias-dependent Peltier coefficient and internal cooling in bipolar devices," *Phys. Rev. B* 66, 125316 (2002).
5. J. Dziewior, W. Schmid, "Auger coefficients for highly doped and highly excited silicon," *Appl. Phys. Lett.* 31, 346 (1977).
6. D. M. Caughey, R. E. Thomas, "Carrier mobilities in silicon empirically related to doping and field," *Proc. IEEE* 55, 2192 (1967).
7. T. Sadi, I. Radevici, J. Oksanen, "Thermophotonic cooling with light-emitting diodes," *Nature Photonics* 14, 205 (2020).
