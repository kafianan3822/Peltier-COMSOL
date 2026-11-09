"""Report for the final device (config/final_device.yaml): results/final/summary_final.md
and figures F1-F7 in results/final/figures (PNG 300 dpi + PDF).

    python postprocess/final_report.py

COMSOL results are read from results/<id>/ (written by comsol/python/run_final.py). Reference-model
curves come from results/reference/<id>/; they are computed here if missing (about 35 s).
Without COMSOL results, the report shows the reference model alone, clearly labelled.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "postprocess"))
sys.path.insert(0, str(ROOT / "reference"))

import analyze as an  # noqa: E402
import plots as pl  # noqa: E402  (style, colours)
from common.params import K_B, Q_E, evaluate_params, expand_final, load_final  # noqa: E402

plt = pl.plt
OUT = ROOT / "results" / "final"
FIG = OUT / "figures"
TABLE_VF = [0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]
COL = {"FINAL": "#1baf7a", "V1x": pl.C["V1"]}
INDEX: list[dict] = []


# ---------------------------------------------------------------------- data
def ensure_reference(runs: list[dict]) -> None:
    import reference_model as rm
    for r in runs:
        if not (an.REF / r["id"] / "global_vs_VF.csv").exists() or r["id"] in ("FINAL", "V1x") and \
                an.read_csv(an.REF / r["id"] / "global_vs_VF.csv").VF.max() < 1.0:
            print(f"reference model: {r['id']} ...")
            rm.run_variant(r["id"], r["params"], configs=r.get("configs"), sweeps=r.get("sweeps"))


def load(runs: list[dict]) -> dict:
    d = {}
    for r in runs:
        c = an.load_variant(r["id"], "comsol", r)
        ref = an.load_variant(r["id"], "reference", r)
        info = c.path / "final_run.json"
        d[r["id"]] = dict(run=r, comsol=c if c.available else None, ref=ref if ref.available else None,
                          info=json.loads(info.read_text(encoding="utf-8")) if info.exists() else {})
    return d


def series(vd: an.VariantData) -> pd.DataFrame:
    """Per-VF quantities of one run (COMSOL or reference), Config A at dT_sink = 0 and Config B."""
    p = evaluate_params(vd.run.get("params", {}))
    g = vd.glob.sort_values("VF").reset_index(drop=True)
    s = pd.DataFrame(dict(VF=g.VF, I=g.I, J=g.J, P_el=g.P_el, Q_room=g.Q_room, eta_E=g.eta_E,
                          Qjn=g.Qjn_n + g.Qjn_p, Qtot=g.Qtot_int))
    if "V_ifield" in g:
        s["V_i"] = g.V_ifield
    elif "V_ohm" in g:
        s["V_i"] = g.V_ohm
    else:
        s["V_i"] = np.nan
    s["V_j"] = s.VF - s.V_i
    s["dT_B"] = p["T_room"] - 0.5 * (g.T_P1 + g.T_P5)          # > 0: ends cooler than the sink
    s["COP"] = an.cop(s.Q_room, s.I, s.VF)
    slope = -p["Ac"] * p["k_Si"] * (2.0 / p["Wi"] + 2.0 / p["Wi"])   # dQ_room/d(dT_sink), Config A
    s["dT_max"] = np.where(s.Q_room > 0, -s.Q_room / slope, np.nan)
    if vd.room is not None and not vd.room.empty:
        t = an.dT_max_vs_VF(vd.room)
        s["dT_max"] = np.interp(s.VF, t.VF, t.dT_max, left=np.nan, right=np.nan)
    return s


def at(s: pd.DataFrame, col: str, v: float) -> float:
    return an.interp_at(s, col, v)


def peak(s: pd.DataFrame, col: str) -> tuple[float, float]:
    t = s.dropna(subset=[col])
    if t.empty or t[col].max() <= 0:
        return float("nan"), float("nan")
    i = int(t[col].to_numpy().argmax())
    return float(t[col].iloc[i]), float(t.VF.iloc[i])


def auger_crossover(run: dict) -> float:
    """V_j where Auger (C n^2) equals SRH (1/tau_eff) in the i-region: n* = (C tau_eff)^-1/2."""
    import reference_model as rm
    p = evaluate_params(run["params"])
    dev = rm.RefDevice.from_params(p)
    n_star = 1.0 / math.sqrt(dev.Ca * 2.0 * p["tau_long"])
    return 2.0 * K_B * p["T0"] / Q_E * math.log(n_star / dev.ni)


# ---------------------------------------------------------------------- figures
def save(fig, name: str, caption: str, source: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=300)
    plt.close(fig)
    INDEX.append(dict(name=name, caption=caption, source=source))


def _lines(ax, D, col, scale=1.0, ids=("FINAL", "V1x"), vmin=0.6, absval=False):
    srcs = set()
    for vid in ids:
        for key, ls in (("comsol", "-"), ("ref", "--")):
            s = D[vid].get(f"s_{key}")
            if s is None or col not in s:
                continue
            s = s[s.VF >= vmin - 1e-9]
            y = s[col] * scale
            ax.plot(s.VF, np.abs(y) if absval else y, color=COL[vid], ls=ls,
                    label=f"{vid} {'COMSOL' if key == 'comsol' else 'reference'}")
            srcs.add(key)
    return "COMSOL (solid) + reference (dashed)" if srcs == {"comsol", "ref"} else (
        "COMSOL" if srcs == {"comsol"} else "reference model")


def _invalid_shade(ax, D, vid="FINAL"):
    s = D[vid].get("s_comsol")
    s = s if s is not None else D[vid].get("s_ref")
    if s is None:
        return
    lim = D["_limit"]
    bad = s[np.abs(s.dT_B) > lim]
    if not bad.empty:
        ax.axvspan(bad.VF.min(), s.VF.max(), color=pl.GRID, alpha=0.6, lw=0)
        ax.text(bad.VF.min() + 0.01, 0.97, f"|T_end - T_room| > {lim:g} K:\none-way coupling approximate",
                transform=ax.get_xaxis_transform(), fontsize=7, color=pl.MUTED, va="top")


def figures(D: dict) -> None:
    # F1 I-V
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    src = _lines(ax, D, "J", 1e-4)
    ax.set_yscale("log")
    vx = auger_crossover(D["FINAL"]["run"])
    ax.axvline(vx, color=pl.MUTED, lw=0.8, ls=":")
    ax.text(vx + 0.01, 0.05, f"Auger = SRH\n(V_j = {vx:.2f} V)", transform=ax.get_xaxis_transform(),
            fontsize=7, color=pl.MUTED)
    ax.set_xlabel("VF (V)")
    ax.set_ylabel("J (A cm$^{-2}$)")
    ax.set_title("F1  current-voltage, 0.6-1.5 V")
    ax.legend(fontsize=7)
    save(fig, "F1_IV", "Current density vs applied voltage (log scale); dotted line: V_j where Auger "
                       "recombination overtakes SRH (n* = (C tau_eff)^-1/2)", src)

    # F2 voltage split
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    src = _lines(ax, D, "V_j")
    for vid in ("FINAL", "V1x"):
        for key, ls in (("comsol", "-"), ("ref", "--")):
            s = D[vid].get(f"s_{key}")
            if s is not None:
                s = s[s.VF >= 0.6 - 1e-9]
                ax.plot(s.VF, s.V_i, color=COL[vid], ls=ls, lw=0.9, alpha=0.7)
    p = evaluate_params(D["FINAL"]["run"]["params"])
    vbi = K_B * p["T0"] / Q_E * math.log(p["Nd_p"] * p["Na_p"] / an.NI_C4 ** 2)
    ax.axhline(vbi, color=pl.INK, lw=0.8, ls=":")
    ax.text(0.61, vbi + 0.01, f"V_bi = {vbi:.2f} V (junction barrier gone)", fontsize=7)
    ax.plot([0.6, 1.5], [0.6, 1.5], color=pl.MUTED, lw=0.6, ls=":")
    ax.text(1.36, 1.43, "V_j = VF", fontsize=7, color=pl.MUTED, rotation=33)
    ax.set_xlabel("VF (V)")
    ax.set_ylabel("voltage (V): thick = V_j (junctions), thin = V_i (i-region)")
    ax.set_title("F2  where the applied voltage goes")
    ax.legend(fontsize=7)
    save(fig, "F2_voltage_split", "Junction voltage V_j = VF - V_i (thick) and i-region drop V_i (thin) vs VF", src)

    # F3 temperatures
    fig, ax = plt.subplots(figsize=(5.6, 3.8))
    src = _lines(ax, D, "dT_B", 1e3)
    ax.set_yscale("symlog", linthresh=1.0)
    ax.axhline(0, color=pl.INK, lw=0.8)
    for vid in ("FINAL", "V1x"):
        s = D[vid].get("s_comsol")
        s = s if s is not None else D[vid].get("s_ref")
        if s is not None:
            v, x = peak(s, "dT_B")
            if np.isfinite(v):
                ax.plot(x, v * 1e3, marker="o", color=COL[vid], ms=5)
                ax.annotate(f"{vid}: {v*1e3:.2f} mK @ {x:.2f} V", (x, v * 1e3),
                            xytext=(8, 6) if vid == "FINAL" else (8, -14),
                            textcoords="offset points", fontsize=7, color=COL[vid])
    _invalid_shade(ax, D)
    ax.set_xlabel("VF (V)")
    ax.set_ylabel("dT = T_room - T_end, Config B (mK)\n> 0 cooled, < 0 heated (symlog)")
    ax.set_title("F3  junction-end cooling vs bias")
    ax.legend(fontsize=7, loc="lower left")
    save(fig, "F3_dT_vs_VF", "End cooling T_room - T_end (Config B; equal to dT_max of Config A for the "
                             "symmetric bar) vs VF; markers: optimum", src)

    # F4 Q_room and COP
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 3.3))
    src = _lines(a1, D, "Q_room", 1e3)
    a1.set_yscale("symlog", linthresh=0.1)
    a1.axhline(0, color=pl.INK, lw=0.8)
    a1.set_xlabel("VF (V)")
    a1.set_ylabel("Q_room at dT_sink = 0 (mW), symlog")
    a1.set_title("heat pumped from the room (Config A)")
    _lines(a2, D, "COP")
    a2.set_ylim(-0.5, 1.0)
    a2.axhline(0, color=pl.INK, lw=0.8)
    a2.set_xlabel("VF (V)")
    a2.set_ylabel("COP = Q_room / P_el")
    a2.set_title("efficiency")
    a1.legend(fontsize=7)
    save(fig, "F4_Qroom_COP", "Q_room(dT_sink = 0) and COP vs VF (Config A)", src)

    # F5 heat budget
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 3.3))
    for col, ls, lab in (("P_el", "-", "P_el (electrical input)"), ("Qtot", "--", "Q_tot (heat released in Si)")):
        s = D["FINAL"].get("s_comsol")
        s = s if s is not None else D["FINAL"]["s_ref"]
        s = s[s.VF >= 0.6 - 1e-9]
        a1.semilogy(s.VF, np.abs(s[col]) * 1e3, color=COL["FINAL"], ls=ls, label=lab)
    a1.semilogy(s.VF, np.abs(s.Qjn) * 1e3, color=pl.C["V0"], ls="-", label="|junction cooling| (Qjn < 0)")
    a1.set_xlabel("VF (V)")
    a1.set_ylabel("power (mW)")
    a1.set_title("FINAL heat budget")
    a1.legend(fontsize=7)
    src = _lines(a2, D, "eta_E")
    a2.axhspan(0.98, 1.02, color=pl.GRID, alpha=0.6, lw=0)
    a2.set_xlabel("VF (V)")
    a2.set_ylabel("eta_E = (Q_tot + Q_contacts) / P_el")
    a2.set_title("energy balance (band = 0.98-1.02)")
    save(fig, "F5_heat_budget", "FINAL: electrical power, released heat and junction cooling; energy-balance "
                                "ratio eta_E for both devices", src)

    # F6 profiles
    vd = D["FINAL"]["comsol"] or D["FINAL"]["ref"]
    if vd is not None and vd.profiles:
        fig, ax = plt.subplots(figsize=(5.6, 3.6))
        p = evaluate_params(vd.run.get("params", {}))
        cmap = plt.get_cmap("viridis")
        vs = sorted(v for v in vd.profiles if v >= 0.6)
        for i, v in enumerate(vs):
            pr = vd.profiles[v]
            ax.plot(pr.x * 1e3, (pr["T"] - p["T_room"]) * 1e3, color=cmap(i / max(len(vs) - 1, 1)),
                    label=f"{v:g} V")
        ax.set_yscale("symlog", linthresh=1.0)
        ax.set_xlabel("x (mm)")
        ax.set_ylabel("T - T_room, Config B (mK), symlog")
        ax.set_title(f"F6  FINAL temperature profiles ({'COMSOL' if vd.source == 'comsol' else 'reference'})")
        ax.legend(fontsize=7, ncol=2)
        save(fig, "F6_T_profiles", "FINAL: temperature along the bar (Config B, centre held at T_room)",
             "COMSOL" if vd.source == "comsol" else "reference model")

    # F7 zone scan
    rows = []
    for vid, e in D.items():
        if not vid.startswith("FINAL_scan"):
            continue
        p = evaluate_params(e["run"]["params"])
        for key in ("comsol", "ref"):
            s = e.get(f"s_{key}")
            if s is not None:
                v, x = peak(s, "dT_B")
                rows.append(dict(w=p["w_rz"], tau=p["tau_short"], src=key, dT=v, VF=x))
    if rows:
        r = pd.DataFrame(rows)
        fig, ax = plt.subplots(figsize=(5.4, 3.5))
        for (w, src_), g in r.groupby(["w", "src"]):
            g = g.sort_values("tau")
            ax.plot(g.tau * 1e6, g.dT * 1e3, marker="o" if src_ == "comsol" else "x",
                    ls="-" if src_ == "comsol" else "--",
                    color=pl.C["V0"] if np.isclose(w, 25e-6) else pl.C["V1"],
                    label=f"w_rz = {w*1e6:g} um, {'COMSOL' if src_ == 'comsol' else 'reference'}")
        ax.set_xscale("log")
        ax.set_xlabel("tau_short (us)")
        ax.set_ylabel("peak dT over VF, Config B (mK)")
        ax.set_title("F7  recombination-zone scan at the optimum bias")
        ax.legend(fontsize=7)
        save(fig, "F7_zone_scan", "Peak end cooling (over VF) vs zone lifetime for two zone widths",
             "COMSOL + reference" if (r.src == "comsol").any() else "reference model")


# ---------------------------------------------------------------------- report
def f(v, scale=1.0, fmt="{:.3f}"):
    return "-" if v is None or not np.isfinite(v) else fmt.format(v * scale)


def table(s: pd.DataFrame, limit: float) -> list[str]:
    L = ["| VF (V) | J (A/cm²) | I (mA) | V_j (V) | V_i (V) | P_el (mW) | Q_room (mW) | dT = T_room − T_end (mK) "
         "| COP | eta_E | validity |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in TABLE_VF:
        if v > s.VF.max() + 1e-9 or v < s.VF.min() - 1e-9:
            continue
        dT = at(s, "dT_B", v)
        ok = "ok" if abs(dT) <= limit else f"self-heating {abs(dT):.2g} K"
        L.append(f"| {v:.2f} | {f(at(s, 'J', v), 1e-4, '{:.4g}')} | {f(at(s, 'I', v), 1e3, '{:.4g}')} "
                 f"| {f(at(s, 'V_j', v))} | {f(at(s, 'V_i', v))} | {f(at(s, 'P_el', v), 1e3, '{:.4g}')} "
                 f"| {f(at(s, 'Q_room', v), 1e3, '{:+.4g}')} | {f(dT, 1e3, '{:+.4g}')} "
                 f"| {f(at(s, 'COP', v), fmt='{:.3g}')} | {f(at(s, 'eta_E', v), fmt='{:.4f}')} | {ok} |")
    return L


def checks(vid: str, e: dict, s: pd.DataFrame, limit: float) -> list[str]:
    qsrc = e["run"].get("qsrc", "builtin")
    lo, hi = (0.98, 1.02) if qsrc == "corrected" else (0.93, 1.01)
    t = s[(s.VF >= 0.6 - 1e-9) & (np.abs(s.dT_B) <= limit)]
    eta = t.eta_E.to_numpy()
    out = [f"- **Energy balance ({qsrc} heat source):** eta_E in [{np.nanmin(eta):.4f}, {np.nanmax(eta):.4f}] over the "
           f"valid range, required [{lo}, {hi}]: **{'PASS' if np.all((eta >= lo) & (eta <= hi)) else 'FAIL'}**."]
    cool = s[(s.Qjn < 0) & (s.VF >= 0.3)]
    out.append(f"- **Junction cooling (Qjn < 0):** present from {cool.VF.min():.2f} to {cool.VF.max():.2f} V."
               if not cool.empty else "- **Junction cooling:** not found.")
    v, x = peak(s, "dT_B")
    out.append(f"- **Plausibility:** largest cooling {f(v, 1e3)} mK (< 100 mK required): "
               f"**{'PASS' if not np.isfinite(v) or v < 0.1 else 'BUG'}**.")
    bad = s[np.abs(s.dT_B) > limit]
    out.append(f"- **One-way coupling:** valid up to {bad.VF.min() - 0.01:.2f} V; above that the device self-heats by "
               f"more than {limit:g} K and n_i (about +8 %/K) is no longer that of 300 K, so currents and heats there are "
               "indicative only." if not bad.empty else
               f"- **One-way coupling:** |T − T_room| ≤ {limit:g} K over the whole sweep.")
    if e["info"].get("note"):
        out.append(f"- **Sweep:** {e['info']['note']}.")
    return out


def main() -> int:
    fin = load_final()
    runs = expand_final("all")
    ensure_reference(runs)
    D = load(runs)
    D["_limit"] = float(fin["validity"]["max_self_heating_K"])
    for vid, e in D.items():
        if vid.startswith("_"):
            continue
        e["s_comsol"] = series(e["comsol"]) if e["comsol"] is not None else None
        e["s_ref"] = series(e["ref"]) if e["ref"] is not None else None
    figures(D)
    lim = D["_limit"]
    have_c = any(e.get("comsol") is not None for k, e in D.items() if not k.startswith("_"))
    L = ["# Final device: extended sweep 0.6-1.5 V", "",
         f"_Generated {dt.datetime.now().isoformat(timespec='seconds')} by `postprocess/final_report.py`._", "",
         "Design and all differences from V1: `docs/FINAL_DEVICE.md`. FINAL = 25 µm / 0.3 µs central "
         "recombination zone, carrier-carrier (Fletcher) scattering, corrected heat source. V1x = V1 unchanged, "
         "on the same extended sweep.", ""]
    if not have_c:
        L += ["> **COMSOL results not found.** Everything below is the COMSOL-independent reference model. Run "
              "`python comsol/python/run_final.py`, then this script again.", ""]
    L += ["## 1. Headline numbers", "",
          "| Device | source | dT at 0.7 V | peak dT (VF) | Q_room at peak | COP at peak | P_el at peak | "
          "J at 1.5 V |", "|---|---|---|---|---|---|---|---|"]
    for vid in ("FINAL", "V1x"):
        for key, lab in (("comsol", "COMSOL"), ("ref", "reference")):
            s = D[vid].get(f"s_{key}")
            if s is None:
                continue
            v, x = peak(s, "dT_B")
            L.append(f"| {vid} | {lab} | {f(at(s, 'dT_B', 0.7), 1e3)} mK | {f(v, 1e3)} mK ({f(x, fmt='{:.2f}')} V) "
                     f"| {f(at(s, 'Q_room', x), 1e3)} mW | {f(at(s, 'COP', x), fmt='{:.3f}')} "
                     f"| {f(at(s, 'P_el', x), 1e3, '{:.1f}')} mW | {f(at(s, 'J', 1.5), 1e-4, '{:.4g}')} A/cm² |")
    for vid in ("FINAL", "V1x"):
        for key, lab in (("comsol", "COMSOL"), ("ref", "reference model")):
            s = D[vid].get(f"s_{key}")
            if s is None:
                continue
            L += ["", f"## {vid} ({lab})", ""] + table(s, lim) + [""]
            if key == "comsol" or D[vid].get("s_comsol") is None:
                L += checks(vid, D[vid], s, lim)
    scan = [(k, e) for k, e in D.items() if k.startswith("FINAL_scan")]
    if scan:
        L += ["", "## Zone scan (Config B, peak over VF)", "",
              "| w_rz | tau_short | COMSOL peak dT (VF) | reference peak dT (VF) |", "|---|---|---|---|"]
        for k, e in scan:
            sv = e["run"]["sweep_values"]
            cells = []
            for key in ("comsol", "ref"):
                s = e.get(f"s_{key}")
                v, x = peak(s, "dT_B") if s is not None else (float("nan"), float("nan"))
                cells.append(f"{f(v, 1e3)} mK ({f(x, fmt='{:.2f}')} V)")
            L.append(f"| {sv['w_rz']} | {sv['tau_short']} | {cells[0]} | {cells[1]} |")
    L += ["", "## Figures", ""] + [f"- [{e['name']}](figures/{e['name']}.png): {e['caption']} _[{e['source']}]_"
                                    for e in INDEX]
    L += ["", "Notes: dT = T_room − T_end in Config B equals dT_max of Config A for the symmetric 1D bar. The reference "
          "model has no carrier-carrier scattering, no heavy-doping physics and n_i = 9.65e9 cm^-3 (COMSOL library "
          "6.68e9), so it overestimates the cooling by about 2x (matrix runs: COMSOL/reference = 0.35-0.63).", ""]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary_final.md").write_text("\n".join(L), encoding="utf-8")
    (FIG / "index.json").write_text(json.dumps(INDEX, indent=1), encoding="utf-8")
    print(f"wrote {(OUT / 'summary_final.md').relative_to(ROOT)} and {len(INDEX)} figures in "
          f"{FIG.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
