"""Figures of the device geometry and model set-up (for presentations), drawn from the same
parameter values the COMSOL builders use (config/params_base.yaml).

    python postprocess/geometry_figures.py      -> results/geometry/G1..G7 *.png (300 dpi) + *.pdf

These are schematics generated from the model definitions, not COMSOL screenshots. The mesh
(G4) reproduces the COMSOL distribution rule exactly: the junction/centre element sizes,
3.15 nm / 6.31 um, match the sizes the COMSOL build logs.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyArrowPatch, Rectangle  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "reference"))

from common.params import evaluate_params, load_base  # noqa: E402

OUT = ROOT / "results" / "geometry"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
C_N, C_I, C_P = "#2a78d6", "#d9d8d2", "#eb6834"      # n+ (blue), intrinsic (neutral), p+ (orange)
C_METAL, C_HOT, C_COLD = "#8a8a85", "#e34948", "#1baf7a"

plt.rcParams.update({
    "font.size": 9, "axes.labelsize": 9, "axes.titlesize": 10, "legend.fontsize": 8,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "savefig.bbox": "tight",
    "legend.frameon": False,
})
P = evaluate_params()
B = load_base()
UM, MM = 1e6, 1e3


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=300)
    plt.close(fig)
    print(f"wrote results/geometry/{name}.png")


def note(fig, text="Schematic generated from the COMSOL model parameters (config/params_base.yaml)"):
    fig.text(0.01, 0.005, text, fontsize=6.5, color=MUTED, ha="left", va="bottom")


# --------------------------------------------------------------------- G1: 3D view
def g1_device_3d():
    L, A = P["Ltot"] * MM, np.sqrt(P["Ac"]) * MM          # mm
    t = 0.06 * L                                            # drawn thickness of doped layers (exaggerated)
    fig = plt.figure(figsize=(8.0, 5.0))
    ax = fig.add_subplot(111, projection="3d")

    def box(x0, x1, color, alpha=1.0):
        X = [x0, x1]
        Y = [0, A]
        Z = [0, A]
        v = np.array([[X[i], Y[j], Z[k]] for i in (0, 1) for j in (0, 1) for k in (0, 1)])
        faces = [[0, 1, 3, 2], [4, 5, 7, 6], [0, 1, 5, 4], [2, 3, 7, 6], [0, 2, 6, 4], [1, 3, 7, 5]]
        ax.add_collection3d(Poly3DCollection([v[f] for f in faces], facecolor=color, edgecolor="#555",
                                             linewidths=0.4, alpha=alpha))

    box(-0.02 * L, 0, C_METAL)                 # n contact
    box(0, t, C_N)
    box(t, L - t, C_I, 0.55)
    box(L - t, L, C_P)
    box(L, L * 1.02, C_METAL)                  # p contact
    xc = L / 2
    # heat-sink band around the bar at x = Xc (top and front faces)
    ax.plot([xc, xc], [0, A], [A, A], color=C_COLD, lw=3)
    ax.plot([xc, xc], [0, 0], [0, A], color=C_COLD, lw=3)
    ax.set_position([0.20, 0.12, 0.62, 0.78])
    fig.text(0.52, 0.90, "green band: heat sink at the centre (x = Xc)", ha="center", fontsize=8.5, color=C_COLD)
    fig.text(0.02, 0.60, "n⁺ layer (blue)\n+ ohmic contact (grey)\nat 0 V\n\nthis end faces\nthe room",
             fontsize=8, color=C_N, va="center")
    fig.text(0.86, 0.60, "p⁺ layer (orange)\n+ ohmic contact (grey)\nat V_F\n\nthis end faces\nthe room",
             fontsize=8, color=C_P, va="center")
    fig.text(0.52, 0.07, "intrinsic region (light): W_i = 1 mm, N_bg = 10¹² cm⁻³", ha="center", fontsize=8)
    ax.set_xlim(-0.1, L * 1.1)
    ax.set_ylim(0, A)
    ax.set_zlim(0, A)
    ax.set_box_aspect((L * 1.12, A, A))
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_zlabel("z (mm)")
    ax.view_init(elev=20, azim=-62)
    fig.suptitle("G1  PIN bar: n⁺ (2 µm) | i (1 mm) | p⁺ (2 µm), cross-section 1 mm × 1 mm", fontsize=10)
    note(fig, "Doped layers drawn ~30x thicker than scale (true 2 µm). COMSOL solves this bar as a 1D model "
              "with cross-sectional area Ac = 1 mm² (G2).")
    save(fig, "G1_device_3D")


# --------------------------------------------------------------------- G2: the 1D model as built
def g2_model_1d():
    Wn, Wi, Wp, L, Xc = (P[k] for k in ("Wn", "Wi", "Wp", "Ltot", "Xc"))
    fig = plt.figure(figsize=(7.4, 4.6))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.3, 1], hspace=0.45, wspace=0.35)
    fig.subplots_adjust(bottom=0.16)
    ax = fig.add_subplot(gs[0, :])
    ax.set_xlim(-0.06, L * MM + 0.06)
    ax.set_ylim(-1.2, 1.4)
    ax.axis("off")
    # domains (not to scale in the doped layers: draw them 3% wide)
    d = 0.08 * L * MM
    segs = [(0, d, C_N, "1  n⁺"), (d, Xc * MM, C_I, "2  i (left half)"),
            (Xc * MM, L * MM - d, C_I, "3  i (right half)"), (L * MM - d, L * MM, C_P, "4  p⁺")]
    for a, b, c, lab in segs:
        ax.add_patch(Rectangle((a, -0.18), b - a, 0.36, facecolor=c, edgecolor="#555", lw=0.6))
        ax.text((a + b) / 2, -0.55, "domain " + lab, ha="center", fontsize=7.5)
    pts = [(0, "P1", "x = 0: n⁺ ohmic contact (0 V)", "right", 0.62),
           (d, "P2", "x = Wn = 2 µm", "left", 0.62),
           (Xc * MM, "P3", "x = Xc = Ltot/2: sink point", "center", 0.62),
           (L * MM - d, "P4", "x = Wn + Wi", "right", 0.62),
           (L * MM, "P5", "x = Ltot = 1.004 mm: p⁺ contact (VF)", "left", 0.62)]
    for x, name, lab, ha, y in pts:
        ax.plot([x], [0], "o", ms=7, mfc="white", mec=INK, zorder=5)
        dx = {"right": -0.012, "left": 0.012, "center": 0}[ha]
        ax.text(x + dx, 0.30, name, ha=ha, fontsize=8.5, weight="bold")
        ax.text(x + dx, y, lab, ha=ha, va="bottom", fontsize=7, color=MUTED,
                rotation=0 if ha == "center" else 0)
    ax.set_title("G2  1D COMSOL geometry: 5 points, 4 domains (doped layers widened for visibility)")
    # true-scale zooms at both junctions + whole bar
    for k, (lo, hi, title) in enumerate([(0, 6e-6, "zoom: n⁺ side (true scale)"),
                                         (0, L, "whole bar (true scale)"),
                                         (L - 6e-6, L, "zoom: p⁺ side (true scale)")]):
        a2 = fig.add_subplot(gs[1, k])
        for a, b, c in ((0, Wn, C_N), (Wn, Wn + Wi, C_I), (Wn + Wi, L, C_P)):
            a2.axvspan(a * UM, b * UM, color=c, alpha=0.85 if c != C_I else 0.5)
        for x in (0, Wn, Xc, Wn + Wi, L):
            a2.axvline(x * UM, color=INK, lw=0.6)
        a2.set_xlim(lo * UM, hi * UM)
        a2.set_yticks([])
        a2.set_xlabel("x (µm)")
        a2.set_title(title, fontsize=8)
    note(fig)
    save(fig, "G2_model_1D")


# --------------------------------------------------------------------- G3: doping
def doping(x):
    """Net doping (1/m^3) as defined in the builder: boxes with Gaussian decay length l_dec outside
    each box (COMSOL Analytic Doping Model, box + 'decay length' profile)."""
    Wn, Wp, L, l = P["Wn"], P["Wp"], P["Ltot"], P["l_dec"]
    nd = np.where(x <= Wn, P["Nd_p"], P["Nd_p"] * np.exp(-((x - Wn) / l) ** 2))
    na_p = np.where(x >= L - Wp, P["Na_p"], P["Na_p"] * np.exp(-((L - Wp - x) / l) ** 2))
    return nd - na_p - P["N_bg"]


def g3_doping():
    Wn, L = P["Wn"], P["Ltot"]
    fig, axes = plt.subplots(1, 3, figsize=(7.6, 3.2), gridspec_kw=dict(width_ratios=[1, 1.4, 1]), sharey=True)
    windows = [(0, Wn + 1.5e-6, "n⁺ / i junction"), (0, L, "whole bar"), (L - Wn - 1.5e-6, L, "i / p⁺ junction")]
    for ax, (a, b, title) in zip(axes, windows):
        x = np.linspace(a, b, 4000)
        N = doping(x) / 1e6                                       # 1/cm^3
        ax.semilogy(x * UM, np.where(N > 0, N, np.nan), color=C_N, label="donors dominate (N > 0)")
        ax.semilogy(x * UM, np.where(N < 0, -N, np.nan), color=C_P, label="acceptors dominate (N < 0)")
        ax.set_xlim(a * UM, b * UM)
        ax.set_ylim(1e10, 3e19)
        ax.set_xlabel("x (µm)")
        ax.set_title(title, fontsize=8.5)
        ax.grid(True, color=GRID, lw=0.5)
    axes[0].set_ylabel("|net doping| (cm⁻³)")
    fig.subplots_adjust(bottom=0.24)
    axes[1].legend(loc="center", fontsize=7)
    fig.suptitle("G3  Doping: n⁺ = p⁺ = 10¹⁹ cm⁻³ boxes (2 µm), Gaussian decay length 0.1 µm, "
                 "i-region 10¹² cm⁻³ acceptors", fontsize=9, y=1.02)
    note(fig, "COMSOL check (stage 3 log): net doping at n⁺ centre / bar centre / p⁺ centre = "
              "+1e19 / -1e12 / -1e19 cm⁻³")
    save(fig, "G3_doping_profile")


# --------------------------------------------------------------------- G4: mesh
def mesh_nodes(factor=1):
    m = B["mesh"]
    Wn, Wi, Wp, Xc = P["Wn"], P["Wi"], P["Wp"], P["Xc"]
    nd, ni, r = int(m["n_doped"] * factor), int(m["n_ihalf"] * factor), m["elemratio_ihalf"]
    q = r ** (1 / (ni - 1))
    h = q ** np.arange(ni)
    left = Wn + (Xc - Wn) * np.concatenate([[0], np.cumsum(h)]) / h.sum()           # fine at x = Wn
    right = Xc + (Wn + Wi - Xc) * np.concatenate([[0], np.cumsum(h[::-1])]) / h.sum()  # fine at Wn+Wi
    x = np.concatenate([np.linspace(0, Wn, nd + 1), left[1:], right[1:],
                        np.linspace(Wn + Wi, Wn + Wi + Wp, nd + 1)[1:]])
    return x


def g4_mesh():
    x = mesh_nodes()
    h, xm = np.diff(x), 0.5 * (x[1:] + x[:-1])
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    fig.subplots_adjust(bottom=0.2)
    for a, b, c in ((0, P["Wn"], C_N), (P["Wn"], P["Wn"] + P["Wi"], C_I), (P["Wn"] + P["Wi"], P["Ltot"], C_P)):
        ax.axvspan(a * MM, b * MM, color=c, alpha=0.35 if c == C_I else 0.6, lw=0)
    ax.semilogy(xm * MM, h * 1e9, ".", ms=1.5, color=INK)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("element size (nm)")
    ax.set_title(f"G4  Mesh: {x.size - 1} elements (400 | 600 + 600 geometric, ratio 2000 | 400)")
    ax.annotate(f"{h[400]*1e9:.2f} nm at the junction", (xm[400] * MM, h[400] * 1e9), xytext=(0.12, 3),
                fontsize=8, arrowprops=dict(arrowstyle="->", color=MUTED))
    imax = int(np.argmax(h))
    ax.annotate(f"{h[imax]*1e6:.2f} µm at the centre", (xm[imax] * MM, h[imax] * 1e9), xytext=(0.62, 8000),
                fontsize=8, arrowprops=dict(arrowstyle="->", color=MUTED))
    ax.text(0.015, 7, "n⁺: 400 × 5 nm", fontsize=7, color=C_N)
    ax.text(0.86, 14, "p⁺: 400 × 5 nm", fontsize=7, color=C_P)
    ax.grid(True, color=GRID, lw=0.5)
    note(fig, "Same distribution rule as the COMSOL build; the logged sizes are h(junction) = 3.15e-9 m, "
              "h(centre) = 6.31e-6 m.")
    save(fig, "G4_mesh")


# --------------------------------------------------------------------- G5: thermal configurations
def g5_thermal_configs():
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 5.4))
    L = 1.0
    configs = [
        ("Config A  (Studies 1 and 2): room at both ends, sink at the centre (Study 1: dT_sink = 0)",
         [("T = T_room", 0, C_HOT), ("T = T_room + dT_sink", 0.5, C_COLD), ("T = T_room", 1, C_HOT)], None,
         "Output: heat taken from the room Q_room(dT_sink); dT_max = sink-room difference where Q_room = 0"),
        ("Config B  (Study 3): insulated ends, sink at the centre",
         [("insulated", 0, MUTED), ("T = T_room", 0.5, C_COLD), ("insulated", 1, MUTED)], None,
         "Output: how far the ends cool (or warm) below the sink: T_end - T_room"),
        ("Config C  (Study 4): insulated ends, lateral convective sink along the i-region",
         [("insulated", 0, MUTED), (None, 0.5, None), ("insulated", 1, MUTED)], "lat",
         "q_lat = h_lat (P/A)(T - T_out); 50 µm walls next to each junction insulated (w_wall)"),
    ]
    for ax, (title, bcs, lat, out) in zip(axes, configs):
        ax.set_xlim(-0.15, 1.15)
        ax.set_ylim(-0.9, 0.9)
        ax.axis("off")
        ax.add_patch(Rectangle((0, -0.15), 0.025, 0.3, color=C_N))
        ax.add_patch(Rectangle((0.025, -0.15), L - 0.05, 0.3, color=C_I))
        ax.add_patch(Rectangle((L - 0.025, -0.15), 0.025, 0.3, color=C_P))
        for lab, x, c in bcs:
            if lab is None:
                continue
            ax.plot([x], [0], "s" if "T =" in lab else "|", ms=10, color=c, mew=3)
            ax.text(x, 0.3, lab, ha="center", fontsize=7.5, color=c)
        if lat:
            for x in np.linspace(0.12, 0.88, 9):
                ax.add_patch(FancyArrowPatch((x, -0.17), (x, -0.55), arrowstyle="->", color=C_COLD,
                                             mutation_scale=8))
            ax.text(0.5, -0.75, "h_lat = 10³ … 10⁵ W/(m²K)", ha="center", fontsize=7, color=C_COLD)
        for x, lab in ((0, "Peltier sink Q_b,n"), (1, "Peltier sink Q_b,p")):
            ax.text(x, -0.4, lab, ha="center", fontsize=6.5, color=MUTED)
        ax.set_title(title, fontsize=8.5, loc="left")
        ax.text(1.15, 0.62, out, ha="right", fontsize=6.5, color=MUTED)
    fig.suptitle("G5  Thermal boundary configurations (one model; studies switch the nodes on/off)", fontsize=9.5)
    note(fig, "In every configuration: volumetric heat source semi.Q_tot and boundary heat sources at both contacts. "
              "Semiconductor temperature fixed at T0 (one-way coupling).")
    fig.tight_layout()
    save(fig, "G5_thermal_configurations")


# --------------------------------------------------------------------- G6: lifetime
def g6_lifetime():
    import reference_model as rm
    xc = P["Xc"]
    x = np.linspace(0, P["Ltot"], 20001)
    r = rm.rect(x, xc - P["w_rz"] / 2, xc + P["w_rz"] / 2)
    tau0 = np.full_like(x, P["tau_long"])
    tau1 = 1 / (1 / P["tau_long"] + r / P["tau_short"])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 3.0), gridspec_kw=dict(width_ratios=[1.4, 1]))
    for ax in (a1, a2):
        ax.semilogy(x * MM, tau0 * 1e6, color="#2a78d6", label="V0: uniform τ = 1 ms")
        ax.semilogy(x * MM, tau1 * 1e6, color="#eb6834", label="V1: recombination zone τ = 1 µs")
        ax.set_xlabel("x (mm)")
        ax.grid(True, color=GRID, lw=0.5)
    a1.set_ylabel("SRH lifetime τ_n = τ_p (µs)")
    a1.legend(fontsize=7, loc="lower left", bbox_to_anchor=(0.0, 0.25))
    fig.subplots_adjust(bottom=0.22)
    a1.set_title("whole bar", fontsize=8.5)
    a2.set_xlim((xc - 1.2 * P["w_rz"]) * MM, (xc + 1.2 * P["w_rz"]) * MM)
    a2.set_title("zone: w_rz = 100 µm, 10 µm smooth edges", fontsize=8.5)
    fig.suptitle("G6  Lifetime profile τ(x) = 1/(1/τ_long + rz_on·rect(x)/τ_short)", fontsize=9.5, y=1.03)
    note(fig, "Auger recombination (C_n = 2.8e-31, C_p = 9.9e-32 cm⁶/s) acts in addition to SRH in both variants "
              "(COMSOL: folded exactly into the trap-assisted lifetime, CHANGES.md M17).")
    save(fig, "G6_lifetime_profile")


# --------------------------------------------------------------------- G7: energy flow concept
def g7_concept():
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.4)
    ax.axis("off")
    ax.add_patch(Rectangle((0.6, 1.6), 0.35, 1.2, color=C_N))
    ax.add_patch(Rectangle((0.95, 1.6), 8.1, 1.2, color=C_I))
    ax.add_patch(Rectangle((9.05, 1.6), 0.35, 1.2, color=C_P))
    ax.add_patch(Rectangle((4.2, 1.6), 1.6, 1.2, color=C_COLD, alpha=0.35))
    ax.text(5.0, 2.2, "recombination\nzone (V1)", ha="center", va="center", fontsize=7.5)
    ax.text(0.78, 3.15, "junction + contact\nabsorb heat\n(E_g + 3kT − qV per pair)", ha="center", fontsize=7, color=C_N)
    ax.text(9.22, 3.15, "junction + contact\nabsorb heat", ha="center", fontsize=7, color=C_P)
    ax.text(5.0, 3.2, "recombination releases ≈ E_g + 3kT per pair\n→ removed by the central heat sink",
            ha="center", fontsize=7, color=INK)
    for x0, x1 in ((1.1, 4.1), (8.9, 5.9)):
        ax.add_patch(FancyArrowPatch((x0, 1.35), (x1, 1.35), arrowstyle="-|>", color=MUTED, mutation_scale=10))
    ax.text(2.6, 1.0, "electrons + holes diffuse to the zone", ha="center", fontsize=7, color=MUTED)
    ax.text(7.4, 1.0, "(ambipolar diffusion, D_a ≈ 18 cm²/s)", ha="center", fontsize=7, color=MUTED)
    ax.text(0.2, 0.35, "Room side = junction ends; heat sink = centre. The ends can cool below the sink by "
            "only a few mK (bound ~ n D_a Π / k).", fontsize=7.5)
    ax.set_title("G7  Operating principle: bipolar (junction) Peltier cooling of a forward-biased PIN diode",
                 fontsize=9.5)
    save(fig, "G7_operating_principle")


def main():
    for f in (g1_device_3d, g2_model_1d, g3_doping, g4_mesh, g5_thermal_configs, g6_lifetime, g7_concept):
        f()


if __name__ == "__main__":
    main()
