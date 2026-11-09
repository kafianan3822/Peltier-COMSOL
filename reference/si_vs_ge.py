"""Si vs Ge comparison with the reference model (numbers of docs/report/pin_peltier_si_vs_ge.tex,
Tables 3-4 and Section 5.3).

    python reference/si_vs_ge.py           # about 5-10 min

Same geometry as the project (W_i = 1 mm, 25 um central zone, tau_long = 1 ms). Germanium
parameters (300 K): Eg 0.66 eV, n_i 2.0e13 cm^-3, Nc 1.04e19, Nv 6.0e18 cm^-3, mu_n 3900,
mu_p 1900 cm^2/(V s) [Sze & Ng], k 60 W/(m K) [Glassbrenner & Slack 1964], ambipolar Auger
7e-31 cm^6/s [Garin et al., Sol. Energy Mater. Sol. Cells 295 (2026)]. Peak = maximum over bias
of T_room - T_end in Config B (equal to dT_max of Config A for the symmetric bar).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import reference_model as rm  # noqa: E402
from common.params import K_B, Q_E, evaluate_params  # noqa: E402

KT = K_B * 300.0 / Q_E
GE = dict(Eg=0.66, ni=2.0e13, Nc=1.04e19, Nv=6.0e18, mun=3900.0, mup=1900.0, k=60.0, Ca=7e-31)


def device(material: str, Wi="1[mm]", w_rz="25[um]", tau_short="0.3[us]", Ca=None, k=None, mob=1.0):
    p = evaluate_params({"rz_on": "1", "Wi": Wi, "w_rz": w_rz, "tau_short": tau_short})
    d = rm.RefDevice.from_params(p)
    if material == "Ge":
        d.Eg_eV, d.ni, d.k = GE["Eg"], GE["ni"] * 1e6, GE["k"]
        d.mun, d.mup = GE["mun"] * 1e-4, GE["mup"] * 1e-4
        d.Ca = GE["Ca"] * 1e-12
        d.Pi_nc = KT * (math.log(GE["Nc"] / 1e19) + 2)
        d.Pi_pc = KT * (math.log(GE["Nv"] / 1e19) + 2)
    if Ca is not None:
        d.Ca = Ca * 1e-12
    if k is not None:
        d.k = k
    d.mun, d.mup = d.mun * mob, d.mup * mob
    return d


def peak(d, Vj_max: float, dVj: float = 0.005) -> dict:
    best = None
    for bp in rm.sweep_Vj(d, Vj_max=Vj_max, dVj=dVj):
        if bp.Vj < 0.2:
            continue
        dT = d.T_room - rm._heat_config_B(d, bp)[0][0]
        if best is None or dT > best["dT"]:
            Q = rm._heat_config_A(d, bp, 0.0)[4]
            P = bp.J * bp.VF * d.Ac
            best = dict(dT=dT, VF=bp.VF, Q=Q, P=P, COP=Q / P, nb=d.n_boundary(bp.Vj))
    return best


CASES = [
    ("Si, Ca Dziewior-Schmid", dict(material="Si", tau_short="0.3[us]"), 0.95),
    ("Si, Ca Dziewior-Schmid", dict(material="Si", tau_short="0.1[us]"), 0.95),
    ("Si, Ca high injection 1.66e-30", dict(material="Si", tau_short="0.1[us]", Ca=1.66e-30), 0.95),
    ("Ge", dict(material="Ge", tau_short="0.1[us]"), 0.62),
    ("Ge", dict(material="Ge", tau_short="0.03[us]"), 0.62),
    ("Ge, mobilities x0.5 (carrier-carrier)", dict(material="Ge", tau_short="0.1[us]", mob=0.5), 0.62),
    ("Ge, W_i = 0.5 mm", dict(material="Ge", Wi="0.5[mm]", tau_short="0.01[us]"), 0.62),
    ("Ge-like, k = 4 W/mK", dict(material="Ge", tau_short="0.1[us]", k=4.0), 0.62),
    ("Ge-like, k = 4 W/mK, D_a = 30 cm2/s", dict(material="Ge", tau_short="0.1[us]", k=4.0, mob=0.45), 0.62),
]


def main() -> None:
    for label, kw, vjm in CASES:
        b = peak(device(**kw), vjm)
        print(f"{label:40s} tau_short={kw.get('tau_short'):9s} peak dT = {b['dT']*1e3:8.1f} mK at VF = "
              f"{b['VF']:.3f} V  COP = {b['COP']:.3f}  P_el = {b['P']*1e3:7.1f} mW  n_b = {b['nb']*1e-6:.2e} cm^-3")


if __name__ == "__main__":
    main()
