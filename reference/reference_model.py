"""COMSOL-independent reference model for the PIN junction-cooling study (spec §11).

Physics (i-region only, high injection, n = p):

    D_a n'' - R(n, x) = 0,      0 < x < W_i,      n(0) = n(W_i) = n_b
    n_b = n_i exp(q V_j / 2 k_B T)

    R(n, x) = (n - n_i) / (s * tau(x))  +  C_a n (n^2 - n_i^2)

with tau(x) from spec §5.2 and ``s`` the lifetime convention (see
``LIFETIME_CONVENTIONS`` and CHANGES.md):  s = 2 reproduces the exact SRH rate
COMSOL evaluates for n = p, tau_n = tau_p = tau, midgap trap
(R = (np - n_i^2)/(tau_p(n+n_i) + tau_n(p+n_i)) = (n-n_i)/(2 tau)); s = 1 is the
literal n/tau of spec §11.1.  The ``- n_i`` terms make R vanish at equilibrium,
so J = 0 and T = T_room at V_j = 0 (test of spec §11.5).

Current and heat (spec §11.2):

    J = q int R dx,  sigma = q n (mu_n + mu_p),  V_Omega = int J/sigma dx,
    V_F = V_j + V_Omega,  H(x) = R (E_g + 3 k_B T) + J^2/sigma,
    point sink at each end  Q_b = -(J/q) Pi_tot / 2,  Pi_tot = E_g + 3k_BT - qV_j

Heat equation k T'' = -H is integrated exactly (cumulative quadrature of the
flux) on each half of the bar; see ``_heat_config_A`` / ``_heat_config_B``.
Energy closes identically: Ac*(int H + 2 Q_b) = I*V_F.

Outputs follow the CSV schema of spec §6 and are written to
results/reference/<variant_id>/.

    python reference/reference_model.py                 # core (V0, V1) + V5 + V6
    python reference/reference_model.py --set core
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.integrate import cumulative_trapezoid, solve_bvp, trapezoid
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.csvio import write_csv  # noqa: E402
from common.params import K_B, Q_E, evaluate_params, expand_variants, load_base, parse_range  # noqa: E402

RESULTS = ROOT / "results" / "reference"

# Material constants for the reference model (spec §11.1, §4.2)
EG_EV = 1.12               # band gap, eV
NI = 9.65e9 * 1e6          # intrinsic density, m^-3 (spec §11.1)
MU_N = 1414e-4             # m^2/(V s)  (spec §11.1, Caughey-Thomas mu_max)
MU_P = 470.5e-4
LIFETIME_CONVENTIONS = {"srh_hl": 2.0, "spec_literal": 1.0}
DEFAULT_CONVENTION = "srh_hl"
RECT_SMOOTH = 10e-6        # rect1 transition-zone size, m (spec §5.2)
PROFILE_VARIANTS = ("V0", "V1")   # profiles are written for the core variants only (repo size)
PROFILE_MAX_ROWS = 2500


# --------------------------------------------------------------------- helpers
def smoothed_step(x, x0, width):
    """C2-continuous step 0 -> 1 centred at x0 over a zone of total size `width`
    (mimics COMSOL's smoothed Heaviside used by the Rectangle function)."""
    if width <= 0:
        return (np.asarray(x) >= x0).astype(float)
    t = np.clip((np.asarray(x, float) - x0) / width + 0.5, 0.0, 1.0)
    return t * t * t * (t * (6.0 * t - 15.0) + 10.0)


def rect(x, lower, upper, smooth=RECT_SMOOTH):
    return smoothed_step(x, lower, smooth) - smoothed_step(x, upper, smooth)


def thermal_voltage(T):
    return K_B * T / Q_E


@dataclass
class RefDevice:
    """Inputs of the reference model in SI units."""
    Wi: float
    Wn: float
    Wp: float
    T: float
    T_room: float
    tau_long: float
    tau_short: float
    w_rz: float
    rz_on: float
    Ca: float
    k: float
    Ac: float
    Pi_nc: float          # V
    Pi_pc: float          # V
    Eg_eV: float = EG_EV
    ni: float = NI
    mun: float = MU_N
    mup: float = MU_P
    auger: bool = True
    convention: str = DEFAULT_CONVENTION
    tau_uniform: float | None = None   # if set, overrides tau(x) (tests)

    @classmethod
    def from_params(cls, p: dict, **kw) -> "RefDevice":
        return cls(Wi=p["Wi"], Wn=p["Wn"], Wp=p["Wp"], T=p["T0"], T_room=p["T_room"],
                   tau_long=p["tau_long"], tau_short=p["tau_short"], w_rz=p["w_rz"],
                   rz_on=p["rz_on"], Ca=p["Cn_aug"] + p["Cp_aug"], k=p["k_Si"], Ac=p["Ac"],
                   Pi_nc=p["Pi_nc"], Pi_pc=p["Pi_pc"], **kw)

    # derived ----------------------------------------------------------------
    @property
    def Vt(self) -> float:
        return thermal_voltage(self.T)

    @property
    def Da(self) -> float:
        Dn, Dp = self.mun * self.Vt, self.mup * self.Vt
        return 2.0 * Dn * Dp / (Dn + Dp)

    @property
    def s(self) -> float:
        return LIFETIME_CONVENTIONS[self.convention]

    @property
    def x_centre(self) -> float:
        """Centre of the rectangle in local i-region coordinates (COMSOL Xc - Wn)."""
        return (self.Wn + self.Wi + self.Wp) / 2.0 - self.Wn

    def tau(self, x):
        x = np.asarray(x, float)
        if self.tau_uniform is not None:
            return np.full_like(x, self.tau_uniform)
        r = rect(x, self.x_centre - self.w_rz / 2, self.x_centre + self.w_rz / 2)
        return 1.0 / (1.0 / self.tau_long + self.rz_on * r / self.tau_short)

    def R(self, n, x):
        r = (n - self.ni) / (self.s * self.tau(x))
        if self.auger:
            r = r + self.Ca * n * (n * n - self.ni ** 2)
        return r

    def dR_dn(self, n, x):
        d = 1.0 / (self.s * self.tau(x))
        if self.auger:
            d = d + self.Ca * (3.0 * n * n - self.ni ** 2)
        return d

    def n_boundary(self, Vj):
        return self.ni * np.exp(Vj / (2.0 * self.Vt))

    def eval_grid(self, n_pts: int = 4001) -> np.ndarray:
        """Graded grid: dense near both ends and around the recombination zone."""
        W, xc = self.Wi, self.x_centre
        g = np.linspace(0, 1, n_pts)
        base = W * g
        ends = np.concatenate([W * 0.02 * g ** 2, W - W * 0.02 * g ** 2])
        zone = np.linspace(xc - self.w_rz, xc + self.w_rz, n_pts // 2)
        x = np.unique(np.clip(np.concatenate([base, ends, zone]), 0, W))
        return x


@dataclass
class BiasPoint:
    Vj: float
    VF: float
    J: float              # A/m^2
    x: np.ndarray
    n: np.ndarray
    Rx: np.ndarray
    sigma: np.ndarray
    H: np.ndarray         # W/m^3
    Q_b: float            # W/m^2, each end (negative)
    Pi_tot_eV: float
    V_ohm: float
    sol: object = field(repr=False, default=None)


# ------------------------------------------------------------- carrier solver
def _initial_mesh(dev: RefDevice, n: int = 400) -> np.ndarray:
    g = np.linspace(0, 1, n)
    x = np.concatenate([dev.Wi * g, dev.x_centre + dev.w_rz * np.linspace(-1, 1, n // 2)])
    return np.unique(np.clip(x, 0, dev.Wi)) / dev.Wi


def solve_carriers(dev: RefDevice, Vj: float, guess=None, tol: float = 1e-6):
    """Solve the ambipolar BVP in scaled form u = n/n_b, xi = x/W_i."""
    nb = dev.n_boundary(Vj)
    W, Da = dev.Wi, dev.Da
    scale = W * W / (Da * nb)

    def fun(xi, y):
        n = nb * y[0]
        return np.vstack([y[1], scale * dev.R(n, xi * W)])

    def fun_jac(xi, y):
        n = nb * y[0]
        m = xi.size
        J = np.zeros((2, 2, m))
        J[0, 1, :] = 1.0
        J[1, 0, :] = scale * dev.dR_dn(n, xi * W) * nb
        return J

    def bc(ya, yb):
        return np.array([ya[0] - 1.0, yb[0] - 1.0])

    def bc_jac(ya, yb):
        return np.array([[1.0, 0.0], [0.0, 0.0]]), np.array([[0.0, 0.0], [1.0, 0.0]])

    if guess is None:
        xi = _initial_mesh(dev)
        y = np.vstack([np.ones_like(xi), np.zeros_like(xi)])
    else:
        xi = guess.x
        y = guess.y * 1.0  # scaled solution is a good guess for the next V_j
    sol = solve_bvp(fun, bc, xi, y, fun_jac=fun_jac, bc_jac=bc_jac,
                    tol=tol, max_nodes=200000, bc_tol=1e-10)
    if sol.status != 0:
        raise RuntimeError(f"solve_bvp failed at Vj={Vj:.4f} V: {sol.message}")
    return sol, nb


def bias_point(dev: RefDevice, Vj: float, guess=None) -> BiasPoint:
    sol, nb = solve_carriers(dev, Vj, guess)
    x = dev.eval_grid()
    n = nb * sol.sol(x / dev.Wi)[0]
    n = np.maximum(n, dev.ni * 1e-6)
    Rx = dev.R(n, x)
    J = Q_E * trapezoid(Rx, x)
    sigma = Q_E * n * (dev.mun + dev.mup)
    V_ohm = trapezoid(J / sigma, x)
    E_pair = (dev.Eg_eV + 3.0 * dev.Vt) * Q_E          # J per recombined pair
    H = Rx * E_pair + J * J / sigma
    Pi_tot = E_pair - Q_E * Vj                           # J per pair
    Q_b = -(J / Q_E) * Pi_tot / 2.0
    return BiasPoint(Vj=Vj, VF=Vj + V_ohm, J=J, x=x, n=n, Rx=Rx, sigma=sigma, H=H,
                     Q_b=Q_b, Pi_tot_eV=Pi_tot / Q_E, V_ohm=V_ohm, sol=sol)


# ------------------------------------------------------------- heat solvers
def _split(x, xc):
    iL = x <= xc
    iR = x >= xc
    return iL, iR


def _heat_config_B(dev: RefDevice, bp: BiasPoint):
    """Insulated ends with point sinks, T(centre) = T_room. Returns T(x), qx(x)."""
    x, H, xc = bp.x, bp.H, dev.Wi / 2.0
    if not np.any(np.isclose(x, xc)):
        raise ValueError("evaluation grid must contain the centre point")
    k = dev.k
    qx = np.empty_like(x)
    T = np.empty_like(x)
    iL, iR = _split(x, xc)
    xL, HL = x[iL], H[iL]
    qL = bp.Q_b + cumulative_trapezoid(HL, xL, initial=0.0)
    TL = dev.T_room + (trapezoid(qL, xL) - cumulative_trapezoid(qL, xL, initial=0.0)) / k
    xR, HR = x[iR], H[iR]
    GR = cumulative_trapezoid(HR[::-1], -xR[::-1] + xR[-1], initial=0.0)[::-1]  # int_x^L H
    qR = -bp.Q_b - GR
    TR = dev.T_room - cumulative_trapezoid(qR, xR, initial=0.0) / k
    qx[iL], T[iL] = qL, TL
    qx[iR], T[iR] = qR, TR
    return T, qx


def _heat_config_A(dev: RefDevice, bp: BiasPoint, dT_sink: float = 0.0):
    """T(0) = T(W) = T_room, T(centre) = T_room + dT_sink.

    Returns T(x), qx(x), qx(0+), qx(L-), Q_room (W) and the heat flux absorbed by
    the centre sink, q_c = qx(Xc-) - qx(Xc+) (W/m^2)."""
    x, H, xc, W, k = bp.x, bp.H, dev.Wi / 2.0, dev.Wi, dev.k
    iL, iR = _split(x, xc)
    xL, HL = x[iL], H[iL]
    GL = cumulative_trapezoid(HL, xL, initial=0.0)
    qx0 = -(k * dT_sink + trapezoid(GL, xL)) / xc
    qL = qx0 + GL
    TL = dev.T_room - cumulative_trapezoid(qL, xL, initial=0.0) / k
    xR, HR = x[iR], H[iR]
    GR = cumulative_trapezoid(HR[::-1], -xR[::-1] + xR[-1], initial=0.0)[::-1]
    qxL = (k * dT_sink + trapezoid(GR, xR)) / (W - xc)
    qR = qxL - GR
    TR = dev.T_room + dT_sink - cumulative_trapezoid(qR, xR, initial=0.0) / k
    T = np.empty_like(x)
    qx = np.empty_like(x)
    T[iL], qx[iL] = TL, qL
    T[iR], qx[iR] = TR, qR
    Q_room = dev.Ac * (qx0 - qxL + (bp.J / Q_E) * bp.Pi_tot_eV * Q_E)
    return T, qx, qx0, qxL, Q_room, qL[-1] - qR[0]


def room_slope(dev: RefDevice) -> float:
    """dQ_room/d(dT_sink) for Config A (exact, linear heat problem), W/K."""
    xc = dev.Wi / 2.0
    return -dev.Ac * dev.k * (1.0 / xc + 1.0 / (dev.Wi - xc))


# ------------------------------------------------------------- bias sweeps
def sweep_Vj(dev: RefDevice, Vj_max: float = 0.9, dVj: float = 0.01) -> list[BiasPoint]:
    pts, guess = [], None
    for Vj in np.round(np.arange(0.0, Vj_max + 1e-12, dVj), 10):
        bp = bias_point(dev, float(Vj), guess)
        guess = bp.sol
        pts.append(bp)
    return pts


def solve_at_VF(dev: RefDevice, VF: float, pts: list[BiasPoint]) -> BiasPoint:
    """Bias point with terminal voltage VF (root-find on V_j, continuation guess)."""
    VFs = np.array([p.VF for p in pts])
    if VF <= 0:
        return bias_point(dev, 0.0)
    i = int(np.searchsorted(VFs, VF))
    i = min(max(i, 1), len(pts) - 1)
    guess = pts[i - 1].sol
    cache = {}

    def f(Vj):
        bp = bias_point(dev, Vj, guess)
        cache[Vj] = bp
        return bp.VF - VF

    Vj = brentq(f, pts[i - 1].Vj, pts[i].Vj, xtol=1e-7)
    return cache.get(Vj) or bias_point(dev, Vj, guess)


@dataclass
class RefResult:
    variant: str
    dev: RefDevice
    params: dict
    pts: list
    glob: pd.DataFrame
    room: pd.DataFrame
    profiles: dict


def _row(dev: RefDevice, bp: BiasPoint) -> dict:
    Ac = dev.Ac
    I = bp.J * Ac
    TB, _ = _heat_config_B(dev, bp)
    _, _, qx0, qxL, Q_room, _ = _heat_config_A(dev, bp, 0.0)
    pairs = bp.J / Q_E
    Qjn_n = -Ac * pairs * Q_E * (bp.Pi_tot_eV / 2.0 - dev.Pi_nc)
    Qjn_p = -Ac * pairs * Q_E * (bp.Pi_tot_eV / 2.0 - dev.Pi_pc)
    Qc = -abs(bp.J) * Ac * (dev.Pi_nc + dev.Pi_pc)
    Qtot_int = Ac * trapezoid(bp.H, bp.x) + Qjn_n + Qjn_p
    P_el = I * bp.VF
    return dict(VF=bp.VF, Vj=bp.Vj, I=I, J=bp.J, P_el=P_el, Qtot_int=Qtot_int,
                Qjn_n=Qjn_n, Qjn_p=Qjn_p, Qc_contacts=Qc, qx_0=qx0, qx_L=qxL,
                T_P1=TB[0], T_P5=TB[-1], T_P3=dev.T_room, Q_room=Q_room,
                eta_E=(Qtot_int + Qc) / P_el if P_el > 0 else np.nan,
                n_b=dev.n_boundary(bp.Vj), V_ohm=bp.V_ohm, Pi_tot=bp.Pi_tot_eV)


def run_variant(variant_id: str, overrides: dict, convention: str = DEFAULT_CONVENTION,
                write: bool = True, out_root: Path = RESULTS, header_extra: dict | None = None) -> RefResult:
    base = load_base()
    p = evaluate_params(overrides)
    dev = RefDevice.from_params(p, convention=convention)
    pts = sweep_Vj(dev)
    VF_iv = parse_range(base["sweeps"]["VF_iv"])
    VF_room = parse_range(base["sweeps"]["VF_room"])
    dTs = parse_range(base["sweeps"]["dT_sink"])

    rows = [_row(dev, solve_at_VF(dev, float(v), pts)) for v in VF_iv if v <= pts[-1].VF]
    glob = pd.DataFrame(rows)
    glob["VF"] = np.round(glob["VF"], 9)

    slope = room_slope(dev)
    Q0 = np.interp(VF_room, glob["VF"], glob["Q_room"])
    room = pd.DataFrame([dict(VF=v, dT_sink=d, Q_room=q + slope * d)
                         for v, q in zip(VF_room, Q0) for d in dTs])

    profiles = {}
    for v in base["sweeps"]["profile_VF"]:
        bp = solve_at_VF(dev, float(v), pts)
        TB, qB = _heat_config_B(dev, bp)
        JdotE = bp.J ** 2 / bp.sigma
        profiles[v] = pd.DataFrame(dict(
            x=bp.x + dev.Wn, Ec=np.nan, Ev=np.nan, Efn=np.nan, Efp=np.nan,
            n=bp.n, p=bp.n, Ndop=-p["N_bg"], JdotE=JdotE, Q_tot=bp.H,
            Q_rec=bp.H - JdotE, T=TB, tfluxX=qB))

    res = RefResult(variant_id, dev, p, pts, glob, room, profiles)
    if write:
        write_result(res, out_root, overrides, header_extra)
    return res


def write_result(res: RefResult, out_root: Path, overrides: dict, header_extra=None) -> None:
    d = out_root / res.variant
    hdr = {"source": "reference/reference_model.py (no COMSOL)", "COMSOL version": "n/a",
           "variant": res.variant, "params": "; ".join(f"{k}={v}" for k, v in overrides.items()),
           "lifetime convention": f"{res.dev.convention} (s={res.dev.s:g})",
           "T_P1,T_P5,T_P3": "Config B (insulated ends + point sinks, centre at T_room)",
           "qx_0,qx_L,Q_room": "Config A at dT_sink = 0",
           "units": "SI (V, A, A/m^2, W, W/m^2, K)"}
    hdr.update(header_extra or {})
    write_csv(d / "global_vs_VF.csv", res.glob, hdr)
    write_csv(d / "room_sweep.csv", res.room, hdr)
    if res.variant not in PROFILE_VARIANTS:
        return
    for v, df in res.profiles.items():
        stride = max(1, len(df) // PROFILE_MAX_ROWS)
        out = pd.concat([df.iloc[::stride], df.iloc[[-1]]]).drop_duplicates()
        write_csv(d / f"profiles_VF{v:g}.csv", out, {**hdr, "VF": v,
                  "note": "Ec/Ev/Efn/Efp not modelled by the reference (NaN); i-region only; "
                          f"every {stride}th node of the evaluation grid"})


# ------------------------------------------------------------- analytic bound
def analytic_bound(dev: RefDevice, Vj: float) -> dict:
    """Spec §11.3: dT_max ~ n_b D_a Pi_side / k, with n_b <= (2/W_i) sqrt(D_a/C_a)."""
    nb = dev.n_boundary(Vj)
    nb_auger = 2.0 / dev.Wi * np.sqrt(dev.Da / dev.Ca)
    Pi_side = (dev.Eg_eV + 3 * dev.Vt - Vj) / 2.0 * Q_E
    return dict(n_b=nb, n_b_auger=nb_auger,
                dT_bound=min(nb, nb_auger) * dev.Da * Pi_side / dev.k,
                dT_bound_auger=nb_auger * dev.Da * Pi_side / dev.k)


# ------------------------------------------------------------- V10 stub
def thermophotonic_cop(EQE, hw_eV, qV_eV):
    """Net cooling per injected pair (eV) of an ideal thermophotonic emitter
    (spec §11.4):  eta_EQE * hbar*omega - qV.  Cooling requires
    eta_EQE > qV / hbar*omega (see ``thermophotonic_cools``)."""
    return np.asarray(EQE) * np.asarray(hw_eV) - np.asarray(qV_eV)


def thermophotonic_cools(EQE, hw_eV, qV_eV):
    return np.asarray(EQE) > np.asarray(qV_eV) / np.asarray(hw_eV)


def plot_thermophotonic(out_dir: Path) -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    eqe = np.linspace(0.5, 1.0, 201)
    ratio = np.linspace(0.5, 1.0, 201)
    E, Rr = np.meshgrid(eqe, ratio)
    cool = thermophotonic_cop(E, 1.0, Rr)  # per pair, in units of hbar*omega
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    lim = np.abs(cool).max()
    cs = ax.pcolormesh(eqe, ratio, cool, cmap="RdBu", vmin=-lim, vmax=lim, shading="auto")
    ax.contour(eqe, ratio, cool, levels=[0.0], colors="k", linewidths=1.2)
    fig.colorbar(cs, ax=ax, label=r"net cooling per pair / $\hbar\omega$  ($\eta_{EQE} - qV/\hbar\omega$)")
    ax.set_xlabel(r"external quantum efficiency $\eta_{EQE}$")
    ax.set_ylabel(r"$qV/\hbar\omega$")
    for e in (0.7, 0.9):
        ax.axvline(e, color="0.25", lw=0.8, ls="--")
    ax.text(0.8, 0.53, "III-V LEDs\n" r"EQE $\gtrsim$ 0.7-0.9", ha="center", fontsize=8)
    ax.annotate(r"Si: EQE $\ll 10^{-2}$" "\n(far left, off-scale)", xy=(0.5, 0.75), xytext=(0.53, 0.9),
                fontsize=8, arrowprops=dict(arrowstyle="->"))
    ax.text(0.93, 0.66, "cooling", fontsize=9, color="navy", ha="center")
    ax.text(0.52, 0.97, "heating", fontsize=9, color="darkred", va="top")
    ax.set_title("V10 thermophotonic stub (analytic, no device data)", fontsize=9)
    fig.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / "fig10_thermophotonic_map.png", out_dir / "fig10_thermophotonic_map.pdf"]
    for pth in paths:
        fig.savefig(pth, dpi=300)
    plt.close(fig)
    return paths


# ------------------------------------------------------------- CLI
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", default="reference",
                    help="core | reference (core + V5 + V6, default) | ids comma-separated")
    ap.add_argument("--convention", default=DEFAULT_CONVENTION, choices=list(LIFETIME_CONVENTIONS))
    args = ap.parse_args(argv)
    if args.set == "core":
        runs = expand_variants("core")
    elif args.set == "reference":
        runs = expand_variants(ids=["V0", "V1", "V5", "V6"])
    else:
        runs = expand_variants(ids=args.set.split(","))
    summary = []
    for r in runs:
        res = run_variant(r["id"], r["params"], args.convention)
        g = res.glob.set_index("VF")
        row = g.loc[np.isclose(g.index, 0.7)].iloc[0] if np.any(np.isclose(g.index, 0.7)) else None
        slope = room_slope(res.dev)
        if row is not None:
            dTmax = -row.Q_room / slope
            summary.append((r["id"], row.J * 1e-4, row.Q_room * 1e3, dTmax * 1e3,
                            (row.T_P1 - res.dev.T_room) * 1e3, row.eta_E))
            print(f"{r['id']:<32s} J(0.7V)={row.J*1e-4:8.4f} A/cm2  Q_room(dT=0)={row.Q_room*1e3:9.4f} mW  "
                  f"dTmax={dTmax*1e3:8.3f} mK  T_end-T_room(B)={(row.T_P1-res.dev.T_room)*1e3:8.3f} mK  "
                  f"eta_E={row.eta_E:.5f}")
    plot_thermophotonic(ROOT / "results" / "figures")
    print(f"reference results written to {RESULTS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
