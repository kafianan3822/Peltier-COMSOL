# Building the model by hand in the COMSOL 6.3 GUI

This is the click-by-click equivalent of `comsol/python/build_model.py` and
`comsol/java/BuildPinPeltier.java`. The stages are the same as in spec §9. Save
after each stage (*File > Save As > stageN.mph*), so a problem points to one node.
Tags in `monospace` are the ones the scripts use. Keep them, so `run_variants.py`
can drive a hand-built model too.

> **Rule:** the semiconductor temperature is the constant `T0`. Never couple `ht.T`
> into the Semiconductor interface, and do not add a *Nonisothermal* multiphysics
> coupling. The temperature differences of interest are milli-kelvin (one-way coupling, spec §0).

---

## Stage 0: new model

1. *File > New > Model Wizard > 1D*.
2. Add physics: *Semiconductor > Semiconductor (semi)* and *Heat Transfer > Heat Transfer in Solids (ht)*. You can also add `ht` later, at stage 5.
3. Study: *Preset Studies for Selected Physics > Semiconductor Equilibrium*, or Blank Study. The studies are rebuilt in stages 3, 4 and 6.

## Stage 1: parameters, functions, variables, geometry, mesh

1. *Global Definitions > Parameters 1 > Load from File...* > `comsol/params.txt`. Check that 32 parameters
   appear, and that `Pi_nc` ≈ 0.0789 V and `Pi_pc` ≈ 0.0810 V in the *Value* column.
2. *Global Definitions > Functions > Rectangle* (`rect1`): Lower limit `Xc-w_rz/2`, Upper limit `Xc+w_rz/2`,
   *Smoothing > Size of transition zone* `10[um]`.
3. *Component 1 > Definitions > Variables* (`var1`, entire model):
   - `tau_x` = `1/(1/tau_long + rz_on*rect1(x)/tau_short)`
   - `lat_mask` = `(abs(x-Xc) < (Wi/2 - w_wall))`
   - `mun_CT`, `mup_CT`: copy the expressions from `comsol/java/model_config.txt` (needed only for mobility option M2).
4. *Definitions > Nonlocal Couplings > Integration*:
   - `intop_all`: all domains.
   - `intop_i`: domains 2, 3.
   - `pt_n`: point 1. `pt_c`: point 3. `pt_p`: point 5. (Integration over a point returns the point value.)
5. *Geometry 1 > Interval*: *Number of intervals = Many*, Points `0, Wn, Xc, Wn+Wi, Ltot`. *Build All*.
   **Check:** 4 domains, 5 points.
6. *Mesh 1* (User-controlled) > *Edge* (all) with four *Distribution* nodes:

   | Tag | Domain | Settings |
   |---|---|---|
   | `dis_n` | 1 (n+) | Fixed number of elements, 400 |
   | `dis_iL` | 2 | Predefined, 600 elements, element ratio 2000, geometric, **reverse off** |
   | `dis_iR` | 3 | Predefined, 600 elements, element ratio 2000, geometric, **reverse on** |
   | `dis_p` | 4 (p+) | Fixed number of elements, 400 |

   **Check** (*Mesh > Statistics* or plot the mesh): the smallest element of each i-half sits at its junction
   (x = Wn and x = Wn+Wi). If not, toggle *Reverse direction* on that distribution.
   For mesh_factor = 2 (V4), double all four counts.

## Stage 2: material

**Preferred (library):** *Materials > Add Material from Library > Semiconductors > Si - Silicon*, applied to
all domains. Then *File > Save As* `comsol/materials/Si_library.mph`, a model with only this material, tag
`mat1` in `comp1`. The scripts copy every property group from that file (CHANGES.md M4).

**Fallback (blank material `mat1`):**

| Group | Property | Value |
|---|---|---|
| Basic (`def`) | Relative permittivity | 11.7 |
| Semiconductor material | Band gap E_g0 | 1.12[V] |
| | Electron affinity χ0 | 4.05[V] |
| | Nc | `2.86e19[1/cm^3]*(T/300[K])^1.5` |
| | Nv | `3.10e19[1/cm^3]*(T/300[K])^1.5` |
| | μn, μp | 1448, 473 [cm^2/(V*s)] |

In both cases set *Basic*: thermal conductivity `k_Si`, density `rho_Si`, heat capacity `Cp_Si`.

**Read back:** note the values of Nc and Nv at 300 K and enter them as `Nc_si` and `Nv_si` in Parameters.
Check that `Pi_nc` and `Pi_pc` update.

## Stage 3: semiconductor interface and doping

1. *Semiconductor (semi)* settings:
   - *Cross-Sectional Area* `Ac`.
   - Discretization: Finite volume (default).
   - Carrier statistics: Maxwell-Boltzmann.
   - Reference temperature for energy levels: `T0`.
2. *Semiconductor Material Model 1*:
   - *Model Input > Temperature: User defined* `T0` (**one-way coupling**).
   - Band-gap narrowing: Off.
   - Dopant ionization: complete.
   - Mobility: with the library material, add *Arora Mobility Model (LI)* (`mmal1`) and select it for electrons
     and holes (M1). With the fallback material, use *User defined* μn = `mun_CT` and μp = `mup_CT` (M2).
3. Three *Analytic Doping Model* nodes, all domains, *Distribution: Box*:

   | Tag | Impurity | Base x | Width | Concentration | Profile outside box |
   |---|---|---|---|---|---|
   | `dop_bg` | Acceptor | 0 | `Ltot` | `N_bg` | (box covers the bar) |
   | `dop_n` | Donor | 0 | `Wn` | `Nd_p` | Gaussian, profile length scale `l_dec` |
   | `dop_p` | Acceptor | `Ltot-Wp` | `Wp` | `Na_p` | Gaussian, profile length scale `l_dec` |
4. *Study 1* (`std_eq_iv`, label "Study 1: I-V and heat-source map"), step *Semiconductor Equilibrium*, physics
   `semi` only. Compute. **Check:** the signed net doping ranges from -1e19 to +1e19 cm⁻³.

## Stage 4: recombination, contacts, Study 1 sweep

1. *Trap-Assisted Recombination* (`srh1`), all domains: τn = τp = `tau_x` (User defined); trap level at midgap (default).
2. *Auger Recombination* (`auger1`): Cn = `Cn_aug`, Cp = `Cp_aug` (User defined). No radiative recombination.
3. *Metal Contact* `mc_n` (point 1): Ideal ohmic, Terminal type Voltage, V0 = `0[V]`.
   *Metal Contact* `mc_p` (point 5): Ideal ohmic, Voltage, V0 = `VF`.
4. Study 1 > add *Stationary* step (`stat`): *Study Extensions > Auxiliary sweep* VF = `range(0,0.025,0.9)` V,
   continuation on VF. *Solver Configurations > Stationary Solver 1 > Relative tolerance* `1e-6`. Compute.
   **Checks:** the I-V curve is monotonic, and J(0.7 V) for V0 lies between 0.02 and 1 A/cm². The reference model gives 0.056 A/cm².
5. Note the true names of: total recombination rate (`U_TOT`), total current density x (`J_X`),
   terminal current of `mc_p` (`I_TERMINAL`). See `docs/VERIFY_API_NAMES.md`.

## Stage 5: heat transfer, heat sources, Config B

1. *Heat Transfer in Solids (ht)*:
   - *Cross-Sectional Area* `Ac`.
   - *Discretization > Compute boundary fluxes* on.
   - *Initial Values* T = `T_room`.
   - *Solid 1* uses the material.
2. *Heat Source* `hs1`, all domains: Q = `semi.Q_tot`. For variant `qsrc=corrected` use
   `semi.Q_tot + k_B_const*T0*<U_TOT>`.
3. *Boundary Heat Source* `bhs_n`, point 1: Q_b = `-abs(<J_X>)*Pi_nc`.
   *Boundary Heat Source* `bhs_p`, point 5: Q_b = `-abs(<J_X>)*Pi_pc`.
   These are the contact Peltier sinks that ideal ohmic contacts do not release (spec §1).
4. *Temperature* `temp_sinkB`, point 3: T = `T_room`.
5. Study 1: in the Stationary step tick `semi` and `ht`. In the equilibrium step tick `semi` only. Compute.
   **Check:** T(VF = 0) = T_room everywhere (to 1 µK).

## Stage 6: Config A/C nodes, Studies 2-4, model configurations

1. *Temperature* `temp_ends`, points 1 and 5: `T_room`. *Temperature* `temp_sinkA`, point 3: `T_room+dT_sink`.
2. *Heat Source* `hs_lat`, domains 2 and 3: Q = `-h_lat*Plat_over_A*(T-T_out)*lat_mask`.
3. In every study step, tick *Modify model configuration for study step* and disable the thermal nodes of
   the other configurations:

   | Study | Configuration | Thermal nodes active (others disabled) | VF sweep |
   |---|---|---|---|
   | Study 1 `std_eq_iv` (both steps) | A at dT_sink = 0 | `temp_ends`, `temp_sinkA` | 0:0.025:0.9 |
   | Study 2 `std_room` | A | `temp_ends`, `temp_sinkA` | 0:0.025:0.8 + *Parametric Sweep* dT_sink = `range(-0.02,0.0025,0.02)` K |
   | Study 3 `std_float` | B | `temp_sinkB` | 0:0.025:0.9 |
   | Study 4 `std_lat` | C | `hs_lat` | 0:0.025:0.9 |

   `hs1`, `bhs_n` and `bhs_p` stay active everywhere.
4. Convergence fallback: *Stationary Solver 1 > Segregated*, with group 1 = semi variables (V, N, P) and group 2 = T.
   If that also fails, halve the VF step.

## Stages 7-8: export and variants

Use *Results > Derived Values > Global Evaluation* with the expressions of spec §6.1, for example
`Ac*intop_all(semi.Q_tot)`, `pt_n(ht.tfluxX)` and `pt_n(T)`. Use *Export > Data* for the profiles of §6.2.
Running `python comsol/python/run_variants.py` on a model saved as `comsol/models/pin_peltier_base.mph` is
faster. It needs `comsol/models/build_info.json`; copy the template written by the builder, or let the builder create the model.

Variants (`config/variants.yaml`) are parameter and switch changes only: `rz_on`, `mesh_factor`, `Wi`,
`tau_long`, `w_rz`, `tau_short`, `h_lat`, `w_wall`, carrier statistics, BGN, mobility, and the `hs1` expression.
