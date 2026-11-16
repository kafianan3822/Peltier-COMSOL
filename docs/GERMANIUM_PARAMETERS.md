# Germanium parameters: values and justification

The device is a germanium n⁺-i-p⁺ diode. All numbers below live in
`config/params_base.yaml`; nothing material-specific is hard-coded in the scripts. Geometry,
doping and lifetimes are unchanged from the original (silicon) specification. Only the material
and the bias window were changed.

Sources: **[I]** Ioffe Institute NSM archive, *Ge - Germanium*
(https://www.ioffe.ru/SVA/NSM/Semicond/Ge/); **[S]** Sze & Ng, *Physics of Semiconductor Devices*,
3rd ed., Appendix G; **[H]** Hilsum, *Electron. Lett.* 10, 259 (1974). The Ioffe pages could not
be opened from the machine that wrote this file, so the values were entered from memory of
those tables. Please compare them once against the sources before publishing.

## 1. Material (germanium, 300 K)

| Parameter | Value | Source | Verdict |
|---|---|---|---|
| Band gap `Eg0` | 0.661 eV | [I]; [S] gives 0.66 | Justified |
| Electron affinity `chi0` | 4.0 eV | [I], [S] | Justified. It cancels in a homojunction with ideal ohmic contacts |
| Relative permittivity | 16.2 | [I]; [S] gives 16.0 | Justified |
| `Nc` | 1.0e19 cm⁻³ × (T/300 K)^1.5 | [I]; [S] gives 1.04e19 | Justified |
| `Nv` | 5.0e18 cm⁻³ × (T/300 K)^1.5 | [I]; [S] gives 6.0e18 | Justified. The literature spread is about 20 % |
| Intrinsic density n_i | 1.98e13 cm⁻³ | Computed: sqrt(Nc·Nv)·exp(−Eg/2kT) | Justified. Matches the literature value 2.0e13 [I], and is what COMSOL computes from the same Nc, Nv, Eg |
| Lattice mobility `mun`, `mup` | 3900, 1900 cm²/(V·s) | [I], [S] | Justified |
| Doping-dependent mobility (M2) | μ = μ_L / (1 + sqrt(N / 1e17 cm⁻³)) | [H] | Electrons: justified (Hilsum fitted n-Ge). Holes: **assumption**, the same form is used. It gives 173 cm²/(V·s) at 1e19 cm⁻³. Only the 2 µm contact layers are affected |
| Auger `Cn_aug` + `Cp_aug` | 5e-31 + 5e-31 = 1e-30 cm⁶/s | [I] gives "about 1e-30" for the total | **Least certain value.** Published totals range from about 2e-31 to 1e-30; the equal split is an assumption. The upper value is used, which is conservative for cooling. Auger matters above about 0.4 V |
| Thermal conductivity `k_th` | 60 W/(m·K) | [I] gives 58; handbooks 60 | Justified |
| Density `rho_m` | 5323 kg/m³ | [I], [S] | Justified. Not used by the stationary study |
| Heat capacity `Cp_m` | 320 J/(kg·K) | [I] gives 310; handbooks 320 | Justified. Not used by the stationary study |

## 2. Device (unchanged from the specification)

| Parameter | Value | Verdict for germanium |
|---|---|---|
| `Wn`, `Wp` | 2 µm | Kept. See section 4, item 2 |
| `Wi` | 1 mm | Justified. Shorter than the ambipolar diffusion length sqrt(D_a·2τ) = 3.6 mm |
| `Nd_p`, `Na_p` | 1e19 cm⁻³ | **Degenerate in Ge** (Nd = Nc, Na = 2·Nv). See section 4, item 1 |
| `N_bg` | 1e12 cm⁻³ | Justified. Below n_i, so the i-region is truly intrinsic. Detector-grade Ge reaches 1e10 |
| `l_dec` | 0.1 µm | Justified (numerical smoothing of the junction) |
| `tau_long` | 1 ms | Justified for high-purity Ge, where millisecond bulk lifetimes are reported. V5 sweeps 0.1 to 5 ms |
| `tau_short`, `w_rz` | 1 µs, 100 µm | Design choice (metal-doped or irradiated zone). V6 sweeps both |
| `Ac`, `h_lat`, `Plat_over_A`, `w_wall` | 1 mm², 1e4 W/(m²·K), 4000 m⁻¹, 50 µm | Material-independent, unchanged |
| `T0`, `T_room`, `T_out` | 300 K | Unchanged |
| `Pi_nc` | (kT/q)(ln(Nc/Nd)+2) = 0.0517 V | Formula unchanged. Maxwell-Boltzmann, see section 4, item 1 |
| `Pi_pc` | (kT/q)(ln(Nv/Na)+2) = 0.0338 V | Same |

## 3. Bias window and checks

Germanium has a band gap 0.46 eV smaller than silicon, so the whole bias window moves down.

| Setting | Silicon (old) | Germanium (now) | Reason |
|---|---|---|---|
| I-V sweep `VF_iv` | 0 to 0.9 V, step 0.025 | 0 to 0.5 V, step 0.0125 | V_bi = 0.68 V in Ge |
| Room sweep `VF_room` | 0 to 0.8 V | 0 to 0.4 V | See section 5 |
| Headline bias `VF_report` | 0.7 V | 0.4 V | Above (Eg+3kT)/2q = 0.37 V. Below that even the uniform-lifetime device cools its ends slightly |
| Profiles | 0, 0.6, 0.7, 0.75, 0.8 V | 0, 0.3, 0.35, 0.4, 0.45 V | |
| C2 energy balance | 0.93 to 0.99 for VF ≥ 0.5 V | within ±0.03 of 1 − (kT/q)/VF for VF ≥ 0.2 V | The fixed window was the silicon value of the same formula |
| C5 I-V benchmark | i-region SRH current | i-region SRH current + leakage into the contact layers | See section 4, item 2 |
| C8 reverse bias | floor 1e-6 | floor 5·exp(−VF_report/2Vt) = 2e-3 | Thermal generation is 2000 times stronger in Ge and is real physics, not noise |
| Stage-4 smoke test | J(0.7 V) in 0.02 to 1 A/cm² | J(0.4 V) in 0.3 to 30 A/cm² | Reference: 1.44 A/cm² (i-region) + about 2.5 A/cm² (leakage) |

## 4. Known approximations you should be aware of

1. **Degenerate contacts.** 1e19 cm⁻³ equals Nc and is twice Nv in germanium. Maxwell-Boltzmann
   statistics (the base setting) and the contact Peltier formula are then approximate: the
   band positions are off by about 0.5 to 1 kT (13 to 26 meV), and the contact Peltier
   coefficients may be off by a few tens of percent. Variants **V2a/V2b** rerun V0/V1 with
   Fermi-Dirac statistics to measure the effect. The alternative, 1e18 cm⁻³, is non-degenerate but
   lets ten times more minority carriers leak into the contacts, which is worse (item 2).
2. **Leakage into the contact layers.** Minority carriers diffuse through the 2 µm doped layers
   and recombine at the ohmic contacts. COMSOL (first run, V0 at 0.4 V) shows that 52 % of the
   current ends this way; for V1 it is 5 %. COMSOL's volume heat source `semi.Q_tot` does not
   contain this surface recombination, so the first run lost that heat and V0 appeared to cool
   by 19 mK. That was an artefact. The model now adds |J_minority|·(E_g + 3kT)/q as a boundary
   heat source at each contact and subtracts it from the room heat balance. The reference model
   contains the same leakage (short-diode formula), and agrees with COMSOL's current within 2 %
   for V0 and 8 % for V1. Thicker or more heavily doped contact layers would reduce the leakage;
   that is a design change, not made here.
3. **Radiative recombination is not modelled.** With B = 6.4e-14 cm³/s [I] the radiative
   lifetime at n = 4e16 cm⁻³ is 0.4 ms, comparable to `tau_long`. It matters for V0 only; in V1
   the 1 µs zone dominates. The V5 sweep of `tau_long` (0.1 to 5 ms) brackets the effect.
4. **Silicon-only models removed.** Arora mobility, Slotboom band-gap narrowing and Fletcher
   carrier-carrier scattering are calibrated for silicon. They are disabled
   (`material.silicon_models: false`); variants V8a/V8b were removed because M2 is now the base.

## 5. The 0.1 K plausibility limit

The rule "net cooling of 0.1 K or more is a bug" was set for silicon, where the reference model
gives a few mK. Germanium conducts heat 2.5 times worse and its carriers diffuse 3.6 times
faster, so the idealised reference model gives 64 mK at 0.4 V and passes 0.1 K at about 0.43 V.
The limit was **not** raised. The room sweep stops at 0.4 V instead. If COMSOL reports 0.1 K or
more, treat it as a bug first; raise `report.plausibility_limit` only after checking the energy
balance (C2) by hand.

## 6. Reference-model results (no COMSOL), with contact leakage

| Variant | J at 0.4 V | Q_room (dT = 0) | dT_max | Ends minus sink, Config B (mean) |
|---|---|---|---|---|
| V0 (uniform lifetime) | 2.94 A/cm² | −7.4 mW | none (room heated) | +31 mK |
| V1 (recombination zone) | 4.76 A/cm² | +13.5 mW | 56 mK | −56 mK |

At 0.4 V, Auger recombination carries about 78 % of the volume recombination of V0 (COMSOL:
10 860 of 13 864 A/m²). The Auger coefficient is the least certain material value (section 1),
so V0 at this bias depends on it directly. V1 does not: its current is 99 % SRH in the zone.

COMSOL results produced before the contact-heat fix (commit `6f51f5a`) must not be used.
