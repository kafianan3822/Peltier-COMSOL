"""All figures of spec §8.4 (PNG at 300 dpi + PDF, SI units, labelled axes).

    python postprocess/plots.py

For every variant, COMSOL data in results/<id>/ are used when present; otherwise
reference-model data in results/reference/<id>/ are plotted and the panel says
so. Figures that need fields the reference model does not compute (band diagram)
are written as clearly labelled placeholders until COMSOL results exist.
Writes results/figures/figN_*.png|pdf and results/figures/index.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "reference"))
sys.path.insert(0, str(ROOT / "postprocess"))

import analyze as an  # noqa: E402
from common.params import evaluate_params, expand_variants, load_base  # noqa: E402

FIG = ROOT / "results" / "figures"
# categorical slots 1-3 of the validated reference palette (fixed order; colour follows the variant)
C = {"V0": "#2a78d6", "V1": "#eb6834", "third": "#1baf7a"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
VF_STYLES = {0.65: ":", 0.70: "-", 0.75: "--"}

plt.rcParams.update({
    "font.size": 9, "axes.labelsize": 9, "axes.titlesize": 9, "legend.fontsize": 8,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "lines.linewidth": 1.6, "axes.spines.top": False, "axes.spines.right": False,
    "savefig.bbox": "tight", "legend.frameon": False,
})

INDEX: list[dict] = []


def save(fig, name: str, caption: str, source: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=300)
    plt.close(fig)
    INDEX.append(dict(name=name, caption=caption, source=source))


def data(vid: str):
    """VariantData for vid, COMSOL if available else reference (or None)."""
    run = next((r for r in expand_variants("full") if r["id"] == vid), {"params": {}})
    c = an.load_variant(vid, "comsol", run)
    if c.available:
        return c
    r = an.load_variant(vid, "reference", run)
    return r if r.available else None


def src_label(vd) -> str:
    return "COMSOL" if vd.source == "comsol" else "reference model"


def placeholder(name: str, title: str, caption: str) -> None:
    fig, ax = plt.subplots(figsize=(6, 3.2))
    ax.set_axis_off()
    ax.text(0.5, 0.6, title, ha="center", va="center", fontsize=11, color=INK)
    ax.text(0.5, 0.38, "PENDING: requires COMSOL results\n"
            "run comsol/python/build_model.py, then run_variants.py --set core, then plots.py",
            ha="center", va="center", fontsize=9, color=MUTED)
    save(fig, name, caption + " (placeholder: COMSOL results not available)", "none")


# ------------------------------------------------------------------ figure 1
def fig1_band():
    vd = data("V0")
    name, cap = "fig1_band_diagram", "Band diagram Ec, Ev, Efn, Efp at VF = 0 and 0.7 V (V0), zoomed on both junctions"
    if vd is None or vd.source != "comsol" or 0.7 not in vd.profiles:
        return placeholder(name, "Fig. 1  Band diagram (V0)", cap)
    p = evaluate_params()
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.0), sharey=True, gridspec_kw=dict(width_ratios=[1, 2, 1]))
    windows = [(0, p["Wn"] + 8e-6), (0, p["Ltot"]), (p["Ltot"] - p["Wp"] - 8e-6, p["Ltot"])]
    for v, ls in ((0.0, "--"), (0.7, "-")):
        df = vd.profiles[v]
        for ax, (a, b) in zip(axes, windows):
            m = (df.x >= a) & (df.x <= b)
            x = df.x[m] * 1e6
            for col, color in (("Ec", INK), ("Ev", INK), ("Efn", C["V0"]), ("Efp", C["V1"])):
                ax.plot(x, df[col][m], ls=ls, color=color, lw=1.2,
                        label=f"{col}, {v:g} V" if ax is axes[1] else None)
            ax.set_xlim(a * 1e6, b * 1e6)
    axes[0].set_ylabel("energy (eV)")
    axes[0].set_title("n+ junction")
    axes[1].set_title("whole device")
    axes[2].set_title("p+ junction")
    for ax in axes:
        ax.set_xlabel("x (um)")
    axes[1].legend(ncol=2, loc="lower left")
    save(fig, name, cap, src_label(vd))


# ------------------------------------------------------------------ figure 2
def fig2_carriers():
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    srcs = []
    for vid in ("V0", "V1"):
        vd = data(vid)
        if vd is None or 0.7 not in vd.profiles:
            continue
        df = vd.profiles[0.7]
        ax.semilogy(df.x * 1e3, df.n, color=C[vid], label=f"{vid} n ({src_label(vd)})")
        if vd.source == "comsol":
            ax.semilogy(df.x * 1e3, df.p, color=C[vid], ls="--", label=f"{vid} p")
        srcs.append(src_label(vd))
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("carrier density (m$^{-3}$)")
    ax.set_title("n(x), p(x) at VF = 0.7 V" + ("" if "COMSOL" in srcs else "  (reference: n = p, i-region only)"))
    ax.legend()
    save(fig, "fig2_carriers", "Electron and hole densities, V0 vs V1, VF = 0.7 V", ", ".join(sorted(set(srcs))))


# ------------------------------------------------------------------ figure 3
def fig3_heat_source():
    vd = data("V0")
    if vd is None or 0.7 not in vd.profiles:
        return placeholder("fig3_heat_source", "Fig. 3  Q_tot(x)", "Q_tot(x) near the junctions")
    p = evaluate_params()
    df = vd.profiles[0.7]
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0), sharey=False)
    fig.subplots_adjust(wspace=0.4)
    for ax, (a, b), title in ((axes[0], (0, 10e-6), "n side, 0-10 um"),
                              (axes[1], (p["Ltot"] - 10e-6, p["Ltot"]), "p side, mirror region")):
        m = (df.x >= a) & (df.x <= b)
        x = df.x[m] * 1e6
        ax.plot(x, df.Q_tot[m], color=INK, label="Q_tot")
        ax.plot(x, df.JdotE[m], color=C["V0"], ls="--", label="J·E")
        ax.plot(x, df.Q_rec[m], color=C["V1"], ls=":", label="Q_rec = Q_tot - J·E")
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.set_xlim(a * 1e6, b * 1e6)
        ax.set_xlabel("x (um)")
        ax.set_title(title)
    axes[0].set_ylabel("heat source (W m$^{-3}$)")
    axes[0].legend(loc="center right")
    if vd.source != "comsol":
        Qb = float(an.interp_at(vd.glob, "Qjn_n", 0.7)) / p["Ac"]
        axes[1].text(0.04, 0.55, "Reference model (i-region only): the junction\n"
                     "and contact cooling is a lumped point sink of\n"
                     f"{Qb:.3g} W/m$^2$ per end, not a distributed dip.\n"
                     "The negative Q_tot dip requires COMSOL data.",
                     transform=axes[1].transAxes, fontsize=7, va="center", color=MUTED)
        fig.suptitle("Q_tot(x), V0, VF = 0.7 V (reference model; COMSOL pending)", fontsize=9, y=1.06)
    save(fig, "fig3_heat_source", "Q_tot(x) zoomed on 0-10 um and the mirror region with J·E and Q_rec, V0, VF = 0.7 V",
         src_label(vd))


# ------------------------------------------------------------------ figure 4 (key)
def fig4_temperature():
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    srcs = []
    T_room = evaluate_params()["T_room"]
    for vid in ("V0", "V1"):
        vd = data(vid)
        if vd is None or 0.7 not in vd.profiles:
            continue
        df = vd.profiles[0.7]
        ax.plot(df.x * 1e3, (df["T"] - T_room) * 1e3, color=C[vid], label=f"{vid} ({src_label(vd)})")
        end = (df["T"].iloc[0] - T_room) * 1e3
        ax.annotate(f"end: {end:+.2f} mK", (df.x.iloc[0] * 1e3, end), textcoords="offset points",
                    xytext=(10, 8 if end < 0 else -14), fontsize=8, color=INK)
        srcs.append(src_label(vd))
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("T - T_room (mK)")
    ax.set_title("Config B: sink at centre, insulated ends, VF = 0.7 V")
    ax.legend()
    save(fig, "fig4_temperature_configB", "KEY FIGURE: T(x) - T_room in mK, Config B, V0 vs V1, VF = 0.7 V",
         ", ".join(sorted(set(srcs))))


# ------------------------------------------------------------------ figure 5
def fig5_room():
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    srcs = []
    for vid in ("V0", "V1"):
        vd = data(vid)
        if vd is None or vd.room is None:
            continue
        for vf, ls in VF_STYLES.items():
            g = vd.room[np.isclose(vd.room.VF, vf)].sort_values("dT_sink")
            if g.empty:
                continue
            ax.plot(g.dT_sink * 1e3, g.Q_room * 1e3, color=C[vid], ls=ls, label=f"{vid}, {vf:.2f} V")
            r = an.dT_max_from_curve(g.dT_sink, g.Q_room)
            if r.value is not None and abs(r.value) <= 0.02:
                ax.plot([r.value * 1e3], [0], "o", ms=5, mfc=C[vid], mec="white", mew=1.5)
        srcs.append(src_label(vd))
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.set_xlabel("dT_sink = T_sink - T_room (mK)")
    ax.set_ylabel("Q_room (mW)   (+ = room cooled)")
    ax.set_title("Config A: room heat balance; markers = dT_max")
    ax.legend(ncol=2)
    save(fig, "fig5_Qroom_vs_dTsink", "Q_room vs dT_sink (Config A), V0 vs V1, VF = 0.65/0.70/0.75 V, with dT_max markers",
         ", ".join(sorted(set(srcs))))


# ------------------------------------------------------------------ figure 6
def fig6_dtmax_cop():
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(5.2, 5.0), sharex=True)
    srcs = []
    for vid in ("V0", "V1"):
        vd = data(vid)
        if vd is None or vd.room is None:
            continue
        tab = an.dT_max_vs_VF(vd.room)
        tab["I"] = np.interp(tab.VF, vd.glob.VF, vd.glob.I)
        tab = tab[tab.VF >= 0.3 - 1e-9]   # high-injection regime of the models
        a1.plot(tab.VF, tab.dT_max * 1e3, color=C[vid], marker="o", ms=3, label=f"{vid} ({src_label(vd)})")
        copv = an.cop(tab.Q_room0, tab.I, tab.VF)
        coph = an.cop(tab.Q_room_half, tab.I, tab.VF)
        a2.plot(tab.VF, copv, color=C[vid], label=f"{vid}, dT = 0")
        a2.plot(tab.VF, coph, color=C[vid], ls="--", label=f"{vid}, dT = dT_max/2")
        srcs.append(src_label(vd))
    a1.set_ylabel("dT_max (mK)")
    a1.set_title("dT_max (undefined where the room is heated)")
    a1.legend()
    a2.axhline(0, color=MUTED, lw=0.8)
    a2.set_ylabel("COP = Q_room/(I VF)")
    a2.set_xlabel("VF (V)")
    a2.legend(ncol=2, fontsize=7)
    save(fig, "fig6_dTmax_COP_vs_VF", "dT_max and COP vs VF (COP at dT = 0 and dT_max/2)", ", ".join(sorted(set(srcs))))


# ------------------------------------------------------------------ figure 7
def _sweep_metric(prefix: str, VF: float = 0.7):
    rows = []
    for r in expand_variants(ids=[prefix]):
        vd = data(r["id"])
        if vd is None:
            continue
        m = an.metrics(vd, VF)
        rows.append(dict(id=r["id"], **r["sweep_values"], dT=-m["dT_end_B"], source=vd.source,
                         p=evaluate_params(r["params"])))
    return rows


def fig7_scaling():
    import reference_model as rm
    rows = _sweep_metric("V5")
    if not rows:
        return placeholder("fig7_V5_scaling", "Fig. 7  V5 scaling", "dT_max vs Wi")
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    taus = sorted({r["tau_long"] for r in rows}, key=lambda s: rows[[x["tau_long"] for x in rows].index(s)]["p"]["tau_long"])
    styles = ["-", "--", ":"]
    for tau, ls in zip(taus, styles):
        sel = sorted([r for r in rows if r["tau_long"] == tau], key=lambda r: r["p"]["Wi"])
        W = np.array([r["p"]["Wi"] for r in sel]) * 1e3
        ax.plot(W, [r["dT"] * 1e3 for r in sel], color=C["V1"], ls=ls, marker="o", ms=4,
                label=f"tau_long = {tau.replace('[', ' ').replace(']', '')}")
    # analytic estimate n_b D_a Pi_side / k (spec §11.3), evaluated at each run's own V_j
    for tau, ls in zip(taus, styles):
        sel = sorted([r for r in rows if r["tau_long"] == tau], key=lambda r: r["p"]["Wi"])
        Wb, bb = [], []
        for r in sel:
            vd = data(r["id"])
            g = vd.glob
            Vj = (an.interp_at(g, "Vj", 0.7) if "Vj" in g else 0.7 - an.interp_at(g, "V_ifield", 0.7))
            dev = rm.RefDevice.from_params(r["p"])
            Wb.append(r["p"]["Wi"] * 1e3)
            bb.append(rm.analytic_bound(dev, Vj)["dT_bound"] * 1e3)
        ax.plot(Wb, bb, color=INK, ls=ls, lw=0.9, marker="x", ms=4,
                label="estimate n_b D_a Pi_side/k" if tau == taus[0] else None)
    Wg = np.linspace(0.2e-3, 2.1e-3, 60)
    ba = [rm.analytic_bound(rm.RefDevice.from_params(evaluate_params({"rz_on": "1", "Wi": f"{W}[m]"})), 0.7)
          ["dT_bound_auger"] for W in Wg]
    ax.plot(Wg * 1e3, np.array(ba) * 1e3, color=MUTED, lw=1.0, ls="-.",
            label="upper bound, Auger-limited n_b = (2/W_i)(D_a/C_a)^1/2")
    ax.set_yscale("log")
    ax.set_xlabel("W_i (mm)")
    ax.set_ylabel("dT_max = T_room - T_end, Config B (mK)")
    src = "COMSOL" if all(r["source"] == "comsol" for r in rows) else "reference model"
    ax.set_title(f"V5 scaling at VF = 0.7 V ({src})")
    ax.legend(fontsize=7)
    save(fig, "fig7_V5_scaling", "V5: dT_max vs Wi for each tau_long, with the analytic bound n D_a Pi / k", src)


# ------------------------------------------------------------------ figure 8
def fig8_rz_map():
    rows = _sweep_metric("V6")
    if not rows:
        return placeholder("fig8_V6_heatmap", "Fig. 8  V6 map", "dT_max over (w_rz, tau_short)")
    ws = sorted({r["p"]["w_rz"] for r in rows})
    ts = sorted({r["p"]["tau_short"] for r in rows})
    Z = np.full((len(ts), len(ws)), np.nan)
    for r in rows:
        Z[ts.index(r["p"]["tau_short"]), ws.index(r["p"]["w_rz"])] = r["dT"] * 1e3
    fig, ax = plt.subplots(figsize=(5.0, 3.4))
    im = ax.imshow(np.clip(Z, 0, None), origin="lower", cmap="Blues", aspect="auto")
    for i in range(len(ts)):
        for j in range(len(ws)):
            v = Z[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if v > 0.6 * np.nanmax(Z) else INK)
    ax.set_xticks(range(len(ws)), [f"{w*1e6:g}" for w in ws])
    ax.set_yticks(range(len(ts)), [f"{t*1e6:g}" for t in ts])
    ax.grid(False)
    ax.set_xlabel("w_rz (um)")
    ax.set_ylabel("tau_short (us)")
    fig.colorbar(im, ax=ax, label="dT_max (mK), Config B, VF = 0.7 V")
    src = "COMSOL" if all(r["source"] == "comsol" for r in rows) else "reference model"
    ax.set_title(f"V6 recombination-zone design ({src})")
    save(fig, "fig8_V6_heatmap", "V6: dT_max heat map over (w_rz, tau_short)", src)


# ------------------------------------------------------------------ figure 9
def fig9_compare():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 3.2))
    have_comsol = False
    for vid in ("V0", "V1"):
        r = an.load_variant(vid, "reference")
        c = an.load_variant(vid, "comsol")
        T_room = evaluate_params()["T_room"]
        for vd, ls in ((c, "-"), (r, "--")):
            if not vd.available:
                continue
            have_comsol |= vd.source == "comsol"
            g = vd.glob[vd.glob.VF > 0]
            a1.semilogy(g.VF, g.J * 1e-4, color=C[vid], ls=ls, label=f"{vid} {src_label(vd)}")
            a2.plot(g.VF, (0.5 * (g.T_P1 + g.T_P5) - T_room) * 1e3, color=C[vid], ls=ls,
                    label=f"{vid} {src_label(vd)}")
    a1.set_xlabel("VF (V)")
    a1.set_ylabel("J (A cm$^{-2}$)")
    a1.set_title("I-V")
    a2.axhline(0, color=MUTED, lw=0.8)
    a2.set_xlabel("VF (V)")
    a2.set_ylabel("T_end - T_room, Config B (mK)")
    a2.set_title("end temperature")
    a1.legend(fontsize=7)
    if not have_comsol:
        fig.suptitle("COMSOL vs reference: COMSOL curves PENDING (reference only)", fontsize=9, color=MUTED)
    save(fig, "fig9_comsol_vs_reference", "COMSOL (solid) vs reference model (dashed) for V0 and V1",
         "COMSOL + reference model" if have_comsol else "reference model only")


def fig10_thermophotonic():
    import reference_model as rm
    rm.plot_thermophotonic(FIG)
    INDEX.append(dict(name="fig10_thermophotonic_map", caption="V10 thermophotonic stub: net cooling per pair "
                      "eta_EQE*hw - qV over EQE and qV/hw (analytic)", source="analytic"))


def main() -> None:
    load_base()
    for f in (fig1_band, fig2_carriers, fig3_heat_source, fig4_temperature, fig5_room, fig6_dtmax_cop,
              fig7_scaling, fig8_rz_map, fig9_compare, fig10_thermophotonic):
        f()
    (FIG / "index.json").write_text(json.dumps(INDEX, indent=1), encoding="utf-8")
    for e in INDEX:
        print(f"{e['name']:<32s} [{e['source']}] {e['caption']}")


if __name__ == "__main__":
    main()
