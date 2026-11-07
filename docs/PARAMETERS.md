# Model parameters and their justification

PIN-diode junction-cooling model (COMSOL 6.3, Semiconductor + Heat Transfer in Solids, 1D).
Single source of truth: `config/params_base.yaml`. Figures of the geometry and set-up:
`results/geometry/G1 … G7` (`python postprocess/geometry_figures.py`).

**Kind of value**
- **D** = design choice of this study (given in the specification). These are chosen, not measured.
- **L** = literature or materials data, with the source given.
- **C** = taken from the COMSOL 6.3 material library (*Si – Silicon*) and read back by the builder.
- **N** = numerical setting.
- **X** = derived from other parameters.

---

## 1. Geometry (figures G1, G2)

| Symbol | Value | Kind | Justification |
|---|---|---|---|
| W_n, W_p | 2 µm | D | Thin, heavily doped emitter/contact layers, as in a conventional PIN diode. They are thin compared with the i-region, so almost all bulk recombination happens in the i-region where the heat is meant to go. |
| W_i | 1 mm | D | Long intrinsic region that separates the "room" side (junction ends) from the heat sink (centre). It is comparable to the ambipolar diffusion length at τ = 1 ms (L_a = √(D_a·2τ) ≈ 1.9 mm; D_a = 18.3 cm²/s). Carriers can therefore cross most of it. Scaled 0.25–2 mm in variant V5. |
| L_tot = W_n + W_i + W_p | 1.004 mm | X | Total length. |
| X_c = L_tot/2 | 0.502 mm | X | Centre: position of the heat sink (Configs A, B) and of the recombination zone. |
| A_c | 1 mm² (1 mm × 1 mm) | D | Cross-section. The 1D model scales every current and heat flux with A_c. It has no effect on temperature differences, only on watts. |
| P/A (Plat_over_A) | 4000 m⁻¹ | X | Perimeter/area of a 1 mm × 1 mm square bar (4a/a² = 4/a). Used only by the lateral sink (Config C). |
| w_wall | 50 µm (0–200 µm in V7) | D | Insulated section next to each junction in Config C, so the lateral sink does not act directly on the cooled ends. |

## 2. Doping (figure G3)

| Symbol | Value | Kind | Justification |
|---|---|---|---|
| N_D⁺ (n⁺), N_A⁺ (p⁺) | 10¹⁹ cm⁻³ | D | Heavy doping for low-resistance ohmic contacts and good injection efficiency. It is close to the effective density of states (N_c ≈ 2.8×10¹⁹), so Maxwell–Boltzmann statistics is approximate there. Variant V2 checks this with Fermi–Dirac statistics and band-gap narrowing. |
| N_bg (i-region) | 10¹² cm⁻³ acceptors | D, L | "Intrinsic" region made of high-resistivity float-zone Si. 10¹² cm⁻³ p-type corresponds to ρ ≈ 1.3×10⁴ Ω·cm (with μ_p ≈ 470 cm²/Vs), which is commercially available. Under forward bias the injected density (10¹⁵–10¹⁷ cm⁻³) is far above N_bg, so the exact value hardly matters. |
| l_dec | 0.1 µm | D | Gaussian decay length outside each doped box: a near-abrupt junction. COMSOL's alternative "junction depth" form was not usable for the 10¹² cm⁻³ background box (CHANGES.md). |

## 3. Material: silicon at 300 K

| Symbol | Value used | Kind | Justification / source |
|---|---|---|---|
| T_0, T_room, T_out | 300 K | D | Room temperature. The semiconductor is solved at the fixed T_0 (one-way coupling: the expected ΔT is milli-kelvin, so feeding T back would change nothing measurable). |
| E_g | 1.12 eV | C, L | Si band gap at 300 K [Sze & Ng 2007]. |
| χ (electron affinity) | 4.05 eV | C, L | [Sze & Ng 2007]. Sets only the energy reference; it does not affect currents or heat. |
| ε_r | 11.7 | C, L | COMSOL library value. The literature gives 11.7–11.9 [Sze & Ng 2007 lists 11.9]; the difference is negligible here. |
| N_c (300 K) | 2.8×10¹⁹ cm⁻³ | C, L | COMSOL library, the classic value tabulated in [Sze & Ng 2007]. The specification's fallback uses 2.86×10¹⁹ [Green 1990]. |
| N_v (300 K) | 1.04×10¹⁹ cm⁻³ | C, L | COMSOL library [Sze & Ng 2007]. **Note:** the more recent value is 3.10×10¹⁹ cm⁻³ [Green 1990]. |
| n_i (implied) | 6.7×10⁹ cm⁻³ | X | √(N_c N_v)·exp(−E_g/2kT) with the library values. The accepted value is 9.65×10⁹ cm⁻³ [Altermatt et al. 2003]. Because the high-injection current scales with n_i, COMSOL's J(0.7 V) = 0.0445 A/cm² is ~25% below the reference model (0.056 A/cm², which uses 9.65×10⁹). This is a known limitation of the library parameter set, not an error. |
| Mobility (M1, default) | Arora model: μ_min 88 / 54.3, μ_0 1252 / 407 cm²/Vs, N_ref 1.26×10¹⁷ / 2.35×10¹⁷ cm⁻³, α 0.88 (electrons / holes) | C, L | Doping- and temperature-dependent mobility [Arora, Hauser & Roulston 1982], with COMSOL library parameters. Lattice limits 1448 / 473 cm²/Vs. |
| Mobility (M2, variant V8) | Caughey–Thomas form, μ = μ_min + (μ_max − μ_min)/(1 + (N/N_ref)^α); electrons 68.5, 1414 cm²/Vs, 9.2×10¹⁶ cm⁻³, 0.711; holes 44.9, 470.5 cm²/Vs, 2.23×10¹⁷ cm⁻³, 0.719 | D, L | Functional form from [Caughey & Thomas 1967]. The parameter set is the one given in the specification, a widely used empirical fit for Si at 300 K. *Check the original source of this specific set before citing it in the thesis.* |
| k (thermal conductivity) | 148 W/(m·K) | L | Pure Si at 300 K [Incropera et al., Table A.1]. Doping-dependent reduction in the thin n⁺/p⁺ layers is neglected (they are 0.4% of the length). |
| ρ (density) | 2329 kg/m³ | L | [Incropera et al.; Sze & Ng 2007]. |
| c_p | 700 J/(kg·K) | L | ≈712 J/(kg·K) at 300 K [Incropera et al.]. **Not used** by the stationary studies (only transient problems need ρc_p). |

## 4. Recombination (figure G6)

| Symbol | Value | Kind | Justification / source |
|---|---|---|---|
| τ_long (τ_n = τ_p) | 1 ms (0.1–5 ms in V5) | D, L | Bulk SRH lifetime of high-purity float-zone Si. Millisecond lifetimes are reported for such material [Schroder 2006]. With τ_n = τ_p = τ and a midgap trap, the high-injection lifetime is 2τ. |
| τ_short | 1 µs (0.1–10 µs in V6) | D, L | Lifetime inside the engineered recombination zone. Lifetimes of µs and below are produced by lifetime control (Au/Pt diffusion, electron or proton irradiation) as used in fast power diodes [Baliga 2008]. |
| w_rz | 100 µm (25–200 µm in V6) | D | Width of the central recombination zone. It is wider than the zone's own diffusion length (√(D_a·2τ_short) ≈ 60 µm), so carriers entering it recombine there. |
| Zone edges | 10 µm smooth transition | N | Smoothed rectangle function, to avoid a discontinuous coefficient. |
| Trap level | midgap (E_t = E_i) | D | Standard assumption for the dominant SRH centre. |
| C_n, C_p (Auger) | 2.8×10⁻³¹, 9.9×10⁻³² cm⁶/s | L | [Dziewior & Schmid 1977]. In COMSOL 6.3 Auger is folded exactly into the trap-assisted lifetime (CHANGES.md M17). Its effect becomes noticeable above V_F ≈ 0.75 V. |
| Radiative recombination | none | L | Negligible in indirect-gap Si. |

## 5. Contacts and Peltier coefficients

Values below are with the library N_c, N_v (spec fallback values in brackets).

| Symbol | Value | Kind | Justification / source |
|---|---|---|---|
| Contacts | ideal ohmic at x = 0 (0 V) and x = L (V_F) | D | Standard metal contacts on degenerately doped Si. |
| Π_n,c = (kT/q)(ln(N_c/N_D) + 2) | 0.0783 V (0.0789 V) | X, L | Heat absorbed per electron entering the n⁺ from the metal. Fermi-level offset plus 2kT mean energy flux [Pipe, Ram & Shakouri 2002]. |
| Π_p,c = (kT/q)(ln(N_v/N_A) + 2) | 0.0527 V (0.0810 V) | X, L | The same for holes at the p⁺ contact. It is smaller with the library because N_v is smaller. |
| Π_r,n = E_g − kT ln(N_c/N_D) + 2kT | 1.145 V | X | Energy released per minority hole that recombines at the n-contact. |
| Π_r,p = E_g − kT ln(N_v/N_A) + 2kT | 1.171 V | X | The same for minority electrons at the p-contact. COMSOL's ideal contacts release no heat; these terms were added after the first COMSOL run showed that ~⅓ of the energy was missing in V0 (CHANGES.md M19). |

## 6. Bias and thermal boundary conditions (figure G5)

| Symbol | Value | Kind | Justification / source |
|---|---|---|---|
| V_F (forward bias) | 0–0.9 V in 0.025 V steps (0–0.8 V for Study 2) | D | Covers low to high injection. Cooling is only meaningful in high injection (V_F ≳ 0.5 V). |
| ΔT_sink | −20 … +20 mK in 2.5 mK steps | D | Bracket of the expected milli-kelvin lift; ΔT_max is found where Q_room = 0. |
| h_lat (Config C) | 10⁴ W/(m²K) (10³–10⁵ in V7) | D, L | Lateral convective sink. The range spans forced liquid cooling to boiling [Incropera et al., Table 1.1]. |
| Reverse bias check | −0.5 V | N | Check C8: no cooling may appear in reverse bias. |

## 7. Numerics (figure G4)

| Item | Value | Kind | Justification |
|---|---|---|---|
| Discretization | finite volume (COMSOL default for semi) | N | Current-conserving Scharfetter–Gummel scheme, standard for drift-diffusion. |
| Mesh | 400 \| 600 + 600 \| 400 elements; i-region geometric, ratio 2000 (3.15 nm at the junctions, 6.31 µm at the centre) | N | Resolves the junction space-charge regions (Debye length ~nm at 10¹⁹ cm⁻³) and the 1 mm bulk. Variant V4 doubles all counts (convergence check C6). |
| Solver | stationary, relative tolerance 10⁻⁶; continuation in V_F | N | Specification §4.6. Automatic fallback: segregated solver, then halved V_F step. |
| Coupling | one-way (semiconductor at T_0 → heat transfer) | D | ΔT ~ mK changes the semiconductor properties by ~10⁻⁵, which is negligible. |

---

## References

1. S. M. Sze, K. K. Ng, *Physics of Semiconductor Devices*, 3rd ed., Wiley (2007).
2. M. A. Green, "Intrinsic concentration, effective densities of states, and effective mass in silicon," *J. Appl. Phys.* **67**, 2944 (1990).
3. P. P. Altermatt, A. Schenk, F. Geelhaar, G. Heiser, "Reassessment of the intrinsic carrier density in crystalline silicon in view of band-gap narrowing," *J. Appl. Phys.* **93**, 1598 (2003).
4. N. D. Arora, J. R. Hauser, D. J. Roulston, "Electron and hole mobilities in silicon as a function of concentration and temperature," *IEEE Trans. Electron Devices* **29**, 292 (1982).
5. D. M. Caughey, R. E. Thomas, "Carrier mobilities in silicon empirically related to doping and field," *Proc. IEEE* **55**, 2192 (1967).
6. J. Dziewior, W. Schmid, "Auger coefficients for highly doped and highly excited silicon," *Appl. Phys. Lett.* **31**, 346 (1977).
7. K. P. Pipe, R. J. Ram, A. Shakouri, "Bias-dependent Peltier coefficient and internal cooling in bipolar devices," *Phys. Rev. B* **66**, 125316 (2002).
8. G. K. Wachutka, "Rigorous thermodynamic treatment of heat generation and conduction in semiconductor device modeling," *IEEE Trans. CAD* **9**, 1141 (1990).
9. T. L. Bergman, A. S. Lavine, F. P. Incropera, D. P. DeWitt, *Fundamentals of Heat and Mass Transfer*, 7th ed., Wiley (2011): Table A.1 (Si properties), Table 1.1 (typical h).
10. D. K. Schroder, *Semiconductor Material and Device Characterization*, 3rd ed., Wiley (2006): carrier lifetime.
11. B. J. Baliga, *Fundamentals of Power Semiconductor Devices*, Springer (2008): lifetime control.

*Before citing, check edition, page and table numbers against your library copies. This is especially important for the Caughey–Thomas parameter set (row M2), whose original source is not identified here.*
