"""Post-processing formulas and automated verification checks (spec §8.1-8.3, §10).

    python postprocess/analyze.py            # analyse results/, write results/analysis.json

COMSOL results are read from results/<variant_id>/ and reference-model results
from results/reference/<variant_id>/.  Checks C1-C9 are evaluated on COMSOL data;
without COMSOL data they are reported as PENDING, and reference-model sanity
checks (R1-R4) are reported instead.

Exit code 2 if C7 / R3 (net cooling >= 0.1 K) fails: that is a bug, not a result.
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.csvio import read_csv, read_header  # noqa: E402
from common.params import K_B, Q_E, evaluate_params, expand_variants  # noqa: E402

RESULTS = ROOT / "results"
REF = RESULTS / "reference"
VF_REPORT = 0.7
PLAUSIBILITY_LIMIT = 0.1      # K (spec §0 rule 6, §10 C7)
NI_C4 = 1e10 * 1e6            # m^-3, spec C4/C5


# ======================================================================
# Formulas (spec §8)
# ======================================================================
def q_room(qx_0, qx_L, J, Ac, Pi_nc, Pi_pc):
    """Spec §8.1: Q_room = Ac [q_x(0+) - q_x(L-) + |J| (Pi_nc + Pi_pc)] (W, + = room cooled)."""
    return Ac * (np.asarray(qx_0) - np.asarray(qx_L) + np.abs(J) * (Pi_nc + Pi_pc))


def cop(Q_room, I, VF):
    """Spec §8.2: COP = Q_room / (I VF)."""
    P = np.asarray(I) * np.asarray(VF)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(P > 0, np.asarray(Q_room) / P, np.nan)


def eta_E(Qtot_int, Qc_contacts, I, VF):
    """Spec §8.3: eta_E = (Qtot_int + Qc_contacts) / (I VF)."""
    P = np.asarray(I) * np.asarray(VF)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(P > 0, (np.asarray(Qtot_int) + np.asarray(Qc_contacts)) / P, np.nan)


def eta_E_expected(VF, T=300.0, qsrc="builtin"):
    """Spec §8.3: ~ 1 - (kT/q)/VF for builtin, ~ 1 for corrected."""
    if qsrc == "corrected":
        return np.ones_like(np.asarray(VF, float))
    return 1.0 - K_B * T / Q_E / np.asarray(VF, float)


@dataclass
class DTmax:
    value: float | None     # K; None -> "none (room heated)"
    status: str             # "interpolated" | "extrapolated" | "none (room heated)"

    def text(self, scale=1e3, unit="mK", fmt="{:.3f}"):
        if self.value is None:
            return self.status
        s = fmt.format(self.value * scale) + f" {unit}"
        return s + (" (extrap.)" if self.status == "extrapolated" else "")


def dT_max_from_curve(dT_sink, Q_room) -> DTmax:
    """Spec §8.1: dT_sink where Q_room = 0, by linear interpolation.
    'none (room heated)' if Q_room < 0 at dT_sink = 0."""
    d = np.asarray(dT_sink, float)
    q = np.asarray(Q_room, float)
    o = np.argsort(d)
    d, q = d[o], q[o]
    q0 = np.interp(0.0, d, q)
    if q0 < 0:
        return DTmax(None, "none (room heated)")
    s = np.sign(q)
    idx = np.where(s[:-1] * s[1:] <= 0)[0]
    idx = [i for i in idx if d[i + 1] >= 0]
    if idx:
        i = idx[0]
        if q[i] == q[i + 1]:
            return DTmax(float(d[i]), "interpolated")
        return DTmax(float(d[i] - q[i] * (d[i + 1] - d[i]) / (q[i + 1] - q[i])), "interpolated")
    # Q_room is exactly linear in dT_sink (one-way coupling, constant k); extrapolate the fit.
    a, b = np.polyfit(d, q, 1)
    return DTmax(float(-b / a), "extrapolated") if a < 0 else DTmax(None, "none (room heated)")


def dT_max_vs_VF(room: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for vf, g in room.groupby("VF"):
        r = dT_max_from_curve(g.dT_sink, g.Q_room)
        q0 = float(np.interp(0.0, np.sort(g.dT_sink), g.sort_values("dT_sink").Q_room))
        qh = (float(np.interp(r.value / 2, np.sort(g.dT_sink), g.sort_values("dT_sink").Q_room))
              if r.value is not None else np.nan)
        rows.append(dict(VF=vf, dT_max=r.value if r.value is not None else np.nan,
                         status=r.status, Q_room0=q0, Q_room_half=qh))
    return pd.DataFrame(rows)


def interp_at(df: pd.DataFrame, col: str, VF: float) -> float:
    d = df.dropna(subset=[col]).sort_values("VF")
    if d.empty or VF < d.VF.min() - 1e-9 or VF > d.VF.max() + 1e-9:
        return float("nan")
    return float(np.interp(VF, d.VF, d[col]))


# ======================================================================
# Loading
# ======================================================================
@dataclass
class VariantData:
    vid: str
    source: str                         # "comsol" | "reference"
    path: Path
    glob: pd.DataFrame | None = None
    room: pd.DataFrame | None = None
    profiles: dict = field(default_factory=dict)
    reverse: pd.DataFrame | None = None
    reverse_glob: pd.DataFrame | None = None
    header: dict = field(default_factory=dict)
    run: dict = field(default_factory=dict)

    @property
    def available(self) -> bool:
        return self.glob is not None


def load_variant(vid: str, source: str = "comsol", run: dict | None = None) -> VariantData:
    path = (RESULTS if source == "comsol" else REF) / vid
    vd = VariantData(vid, source, path, run=run or {})
    g = path / "global_vs_VF.csv"
    if not g.exists():
        return vd
    vd.glob = read_csv(g)
    vd.header = read_header(g)
    if (path / "room_sweep.csv").exists():
        vd.room = read_csv(path / "room_sweep.csv")
    for f in sorted(path.glob("profiles_VF*.csv")):
        try:
            v = float(f.stem.replace("profiles_VF", ""))
        except ValueError:
            continue
        vd.profiles[v] = read_csv(f)
    if (path / "reverse_bias_profile.csv").exists():
        vd.reverse = read_csv(path / "reverse_bias_profile.csv")
    if (path / "reverse_bias_global.csv").exists():
        vd.reverse_glob = read_csv(path / "reverse_bias_global.csv")
    return vd


def params_for(run: dict) -> dict:
    return evaluate_params(run.get("params", {}))


# ======================================================================
# Per-variant metrics
# ======================================================================
def metrics(vd: VariantData, VF: float = VF_REPORT) -> dict:
    if not vd.available:
        return dict(variant=vd.vid, source=vd.source, available=False)
    p = params_for(vd.run) if vd.run else evaluate_params()
    g = vd.glob
    out = dict(variant=vd.vid, source=vd.source, available=True, VF=VF)
    for c in ("I", "J", "P_el", "Qtot_int", "Qjn_n", "Qjn_p", "Qc_contacts", "Q_room", "eta_E"):
        out[c] = interp_at(g, c, VF) if c in g else float("nan")
    T_end = np.nanmean([interp_at(g, "T_P1", VF), interp_at(g, "T_P5", VF)])
    out["dT_end_B"] = T_end - p["T_room"]            # Config B: ends minus sink (K)
    out["cop0"] = float(cop(out["Q_room"], out["I"], VF)) if np.isfinite(out["Q_room"]) else float("nan")
    if vd.room is not None and not vd.room.empty:
        tab = dT_max_vs_VF(vd.room)
        row = tab.iloc[(tab.VF - VF).abs().argmin()]
        r = dT_max_from_curve(vd.room[np.isclose(vd.room.VF, row.VF)].dT_sink,
                              vd.room[np.isclose(vd.room.VF, row.VF)].Q_room)
        out["dT_max"] = r.value
        out["dT_max_status"] = r.status
        out["dT_max_text"] = r.text()
        out["cop_half"] = (float(cop(row.Q_room_half, out["I"], VF)) if r.value is not None else float("nan"))
        best = tab.dropna(subset=["dT_max"])
        if not best.empty:
            b = best.iloc[best.dT_max.argmax()]
            out["dT_max_best"], out["VF_best"] = float(b.dT_max), float(b.VF)
    else:
        # Config B only: for the symmetric 1D bar dT_max(Config A) = T_room - T_end(Config B) exactly.
        out["dT_max"] = -out["dT_end_B"] if np.isfinite(out["dT_end_B"]) and out["dT_end_B"] < 0 else None
        out["dT_max_status"] = "from Config B" if out["dT_max"] is not None else "none (ends warmer)"
        out["dT_max_text"] = (f"{out['dT_max']*1e3:.3f} mK (B)" if out["dT_max"] is not None
                              else out["dT_max_status"])
        out["cop_half"] = float("nan")
    return out


# ======================================================================
# Checks (spec §10)
# ======================================================================
@dataclass
class Check:
    cid: str
    name: str
    status: str          # PASS | FAIL | PENDING | N/A | BUG
    detail: str


def _pending(cid, name, why="needs COMSOL results (results/<variant>/)"):
    return Check(cid, name, "PENDING", why)


def check_C1(vd: VariantData) -> Check:
    name = "Zero bias"
    if 0.0 not in vd.profiles or VF_REPORT not in vd.profiles:
        return _pending("C1", name, "needs profiles_VF0.csv and profiles_VF0.7.csv")
    p0, p7 = vd.profiles[0.0], vd.profiles[VF_REPORT]
    T_room = evaluate_params(vd.run.get("params", {}))["T_room"]
    qmax7 = np.nanmax(np.abs(p7.Q_tot))
    q0 = np.nanmax(np.abs(p0.Q_tot))
    dT0 = np.nanmax(np.abs(p0["T"] - T_room))
    ok = q0 < 1e-6 * qmax7 and dT0 < 1e-6
    return Check("C1", name, "PASS" if ok else "FAIL",
                 f"{vd.vid}: max|Q_tot(0)|/max|Q_tot(0.7)| = {q0/qmax7:.2e} (<1e-6), "
                 f"max|T-T_room| = {dT0*1e6:.3g} uK (<1 uK)")


def check_C2(vd: VariantData) -> Check:
    name = "Energy balance"
    g = vd.glob[vd.glob.VF >= 0.5 - 1e-9]
    qsrc = vd.run.get("qsrc", "builtin")
    lo, hi = (0.98, 1.02) if qsrc == "corrected" else (0.93, 0.99)
    e = g.eta_E.to_numpy()
    ok = bool(np.all((e >= lo) & (e <= hi)))
    return Check("C2", name, "PASS" if ok else "FAIL",
                 f"{vd.vid} ({qsrc}): eta_E in [{np.nanmin(e):.4f}, {np.nanmax(e):.4f}] for VF>=0.5, "
                 f"required [{lo}, {hi}]")


def check_C3(vd: VariantData) -> Check:
    name = "Junction cooling exists"
    g = vd.glob[(vd.glob.VF >= 0.3 - 1e-9) & (vd.glob.VF <= 1.0 + 1e-9)]
    ok = bool(np.all(g.Qjn_n < 0) and np.all(g.Qjn_p < 0))
    return Check("C3", name, "PASS" if ok else "FAIL",
                 f"{vd.vid}: max Qjn_n = {g.Qjn_n.max():.3e} W, max Qjn_p = {g.Qjn_p.max():.3e} W "
                 f"over VF {g.VF.min():.2f}-{g.VF.max():.2f} V (need < 0)")


def check_C4(vd: VariantData) -> Check:
    name = "Junction-cooling magnitude"
    if "V_ifield" not in vd.glob:
        return _pending("C4", name, "needs column V_ifield (i-region field integral)")
    p = evaluate_params(vd.run.get("params", {}))
    Vt = K_B * p["T0"] / Q_E
    Vbi = Vt * math.log(p["Nd_p"] * p["Na_p"] / NI_C4 ** 2)
    g = vd.glob[(vd.glob.VF >= 0.5 - 1e-9) & (vd.glob.VF <= 0.8 + 1e-9)]
    Vj = g.VF - g.V_ifield
    expect = -g.I * (Vbi - Vj)
    ratio = (g.Qjn_n + g.Qjn_p) / expect
    ok = bool(np.all((ratio > 0.7) & (ratio < 1.3)))
    return Check("C4", name, "PASS" if ok else "FAIL",
                 f"{vd.vid}: (Qjn_n+Qjn_p)/(-I(V_bi-V_j)) in [{ratio.min():.3f}, {ratio.max():.3f}] "
                 f"for VF 0.5-0.8 V (V_bi = {Vbi:.3f} V; need 0.7-1.3)")


def check_C5(vd: VariantData) -> Check:
    name = "I-V benchmark (V0)"
    p = evaluate_params(vd.run.get("params", {}))
    Vt = K_B * p["T0"] / Q_E
    tau_eff = 2.0 * p["tau_long"]   # SRH high-injection lifetime tau_n + tau_p (see CHANGES.md)
    g = vd.glob[(vd.glob.VF >= 0.6 - 1e-9) & (vd.glob.VF <= 0.8 + 1e-9)]
    Jref = Q_E * NI_C4 * np.exp(g.VF / (2 * Vt)) * p["Wi"] / tau_eff
    ratio = g.J / Jref
    ok = bool(np.all((ratio > 1 / 3) & (ratio < 3)))
    return Check("C5", name, "PASS" if ok else "FAIL",
                 f"{vd.vid}: J/J_ref in [{ratio.min():.3f}, {ratio.max():.3f}] for 0.6-0.8 V "
                 f"(tau_eff = 2 tau_long; need 1/3-3)")


def check_C6(v1: VariantData, v4: VariantData) -> Check:
    name = "Mesh convergence"
    if not (v1.available and v4.available):
        return _pending("C6", name, "needs COMSOL results for V1 and V4")
    m1, m4 = metrics(v1), metrics(v4)
    rel = []
    for k in ("dT_max", "Qjn_n", "Qjn_p"):
        a, b = m1.get(k), m4.get(k)
        if a is None or b is None or not np.isfinite(a) or a == 0:
            continue
        rel.append((k, abs(b - a) / abs(a)))
    if not rel:
        return Check("C6", name, "FAIL", "no comparable quantities (dT_max undefined?)")
    ok = all(r < 0.02 for _, r in rel)
    return Check("C6", name, "PASS" if ok else "FAIL",
                 "V4 vs V1: " + ", ".join(f"{k} {r*100:.2f}%" for k, r in rel) + " (need < 2%)")


def check_C7(all_metrics: list[dict], source="COMSOL") -> Check:
    name = "Plausibility (|dT_max| < 0.1 K)"
    bad, worst = [], 0.0
    for m in all_metrics:
        if not m.get("available"):
            continue
        for key in ("dT_max", "dT_max_best"):
            v = m.get(key)
            if v is not None and np.isfinite(v):
                worst = max(worst, abs(v))
                if abs(v) >= PLAUSIBILITY_LIMIT:
                    bad.append(f"{m['variant']}:{key}={v*1e3:.1f} mK")
        dB = m.get("dT_end_B")
        if dB is not None and np.isfinite(dB) and -dB >= PLAUSIBILITY_LIMIT:
            bad.append(f"{m['variant']}:Config-B end cooling={-dB*1e3:.1f} mK")
    if not any(m.get("available") for m in all_metrics):
        return _pending("C7", name)
    if bad:
        return Check("C7", name, "BUG", f"{source}: cooling >= 0.1 K -> BUG, do not report: " + "; ".join(bad))
    return Check("C7", name, "PASS", f"{source}: largest |dT_max| = {worst*1e3:.3f} mK")


def check_C8(vd: VariantData) -> Check:
    name = "Reverse bias"
    if vd.reverse is None or vd.reverse_glob is None or VF_REPORT not in vd.profiles:
        return _pending("C8", name, "needs reverse_bias_profile.csv / reverse_bias_global.csv")
    qmax7 = np.nanmax(np.abs(vd.profiles[VF_REPORT].Q_tot))
    qmin = float(np.nanmin(vd.reverse.Q_tot))
    Qr = float(vd.reverse_glob.Q_room.iloc[-1])
    P7 = interp_at(vd.glob, "P_el", VF_REPORT)
    ok = qmin > -1e-6 * qmax7 and Qr <= 1e-6 * P7
    return Check("C8", name, "PASS" if ok else "FAIL",
                 f"{vd.vid}: min Q_tot(-0.5 V) = {qmin:.3e} W/m^3 (noise floor {-1e-6*qmax7:.2e}), "
                 f"Q_room = {Qr:.3e} W (need <= 0)")


def check_C9(comsol: dict[str, VariantData], ref: dict[str, VariantData]) -> Check:
    name = "COMSOL vs reference model"
    parts, ok = [], True
    for vid in ("V0", "V1"):
        c, r = comsol.get(vid), ref.get(vid)
        if not (c and c.available):
            return _pending("C9", name, "needs COMSOL results for V0 and V1")
        if not (r and r.available):
            return _pending("C9", name, "run reference/reference_model.py first")
        a, b = metrics(c)["dT_end_B"], metrics(r)["dT_end_B"]
        ratio = a / b if b != 0 else float("inf")
        ok &= bool(0.5 <= ratio <= 2.0)
        parts.append(f"{vid}: COMSOL {a*1e3:.3f} mK vs ref {b*1e3:.3f} mK (ratio {ratio:.2f})")
    return Check("C9", name, "PASS" if ok else "FAIL", "; ".join(parts) + " (need 0.5-2)")


def comsol_checks(comsol: dict[str, VariantData], ref: dict[str, VariantData], all_m: list[dict]) -> list[Check]:
    v0, v1 = comsol.get("V0"), comsol.get("V1")
    have = v0 is not None and v0.available
    checks = []
    for fn, cid, nm, targets in [
        (check_C1, "C1", "Zero bias", ("V0", "V1")),
        (check_C2, "C2", "Energy balance", None),
        (check_C3, "C3", "Junction cooling exists", ("V0", "V1")),
        (check_C4, "C4", "Junction-cooling magnitude", ("V0", "V1")),
    ]:
        tv = [comsol[t] for t in (targets or comsol) if t in comsol and comsol[t].available
              and (fn is not check_C2 or comsol[t].glob is not None)]
        if not tv:
            checks.append(_pending(cid, nm))
            continue
        res = [fn(v) for v in tv]
        status = ("FAIL" if any(r.status == "FAIL" for r in res)
                  else "PENDING" if all(r.status == "PENDING" for r in res) else "PASS")
        checks.append(Check(cid, nm, status, " | ".join(r.detail for r in res)))
    checks.append(check_C5(v0) if have else _pending("C5", "I-V benchmark (V0)"))
    checks.append(check_C6(v1 or VariantData("V1", "comsol", RESULTS / "V1"),
                           comsol.get("V4") or VariantData("V4", "comsol", RESULTS / "V4")))
    checks.append(check_C7([m for m in all_m if m.get("source") == "comsol"]))
    tv = [comsol[t] for t in ("V0", "V1") if t in comsol and comsol[t].available]
    res = [check_C8(v) for v in tv]
    if not res or all(r.status == "PENDING" for r in res):
        checks.append(_pending("C8", "Reverse bias"))
    else:
        checks.append(Check("C8", "Reverse bias", "FAIL" if any(r.status == "FAIL" for r in res) else "PASS",
                            " | ".join(r.detail for r in res)))
    checks.append(check_C9(comsol, ref))
    return checks


def reference_checks(ref: dict[str, VariantData], all_m: list[dict]) -> list[Check]:
    """Sanity checks of the COMSOL-independent model (always runnable)."""
    out = []
    for vid in ("V0", "V1"):
        if vid not in ref or not ref[vid].available:
            return [Check("R*", "reference", "PENDING", "run reference/reference_model.py")]
    v0, v1 = ref["V0"], ref["V1"]
    g = v0.glob
    z = g[np.isclose(g.VF, 0.0)].iloc[0]
    T_room = evaluate_params()["T_room"]
    ok = abs(z.J) < 1e-12 and abs(z.T_P1 - T_room) < 1e-9
    out.append(Check("R1", "Zero bias (J = 0, T = T_room)", "PASS" if ok else "FAIL",
                     f"J(0) = {z.J:.2e} A/m^2, T_P1 - T_room = {z.T_P1 - T_room:.2e} K"))
    worst = max(np.nanmax(np.abs(v.glob.eta_E[v.glob.VF > 0] - 1)) for v in (v0, v1))
    out.append(Check("R2", "Energy closure (eta_E = 1 for full bookkeeping)",
                     "PASS" if worst < 5e-3 else "FAIL", f"max |eta_E - 1| = {worst:.2e} (need < 5e-3)"))
    c7 = check_C7([m for m in all_m if m.get("source") == "reference"], source="reference")
    out.append(Check("R3", c7.name, c7.status, c7.detail))
    m0, m1 = metrics(v0), metrics(v1)
    ok = m0["dT_end_B"] > 0 and m1["dT_end_B"] < 0
    out.append(Check("R4", "Qualitative outcome (V0 ends warmer, V1 ends cooler)", "PASS" if ok else "FAIL",
                     f"Config B T_end - T_room at 0.7 V: V0 {m0['dT_end_B']*1e3:+.3f} mK, "
                     f"V1 {m1['dT_end_B']*1e3:+.3f} mK"))
    return out


# ======================================================================
# Driver
# ======================================================================
def collect(set_name: str = "full"):
    runs = {r["id"]: r for r in expand_variants(set_name)}
    comsol = {vid: load_variant(vid, "comsol", r) for vid, r in runs.items()}
    ref = {vid: load_variant(vid, "reference", r) for vid, r in runs.items()}
    return runs, comsol, ref


def analyze(set_name: str = "full") -> dict:
    runs, comsol, ref = collect(set_name)
    all_m = [metrics(v) for v in comsol.values()] + [metrics(v) for v in ref.values()]
    c_checks = comsol_checks(comsol, ref, all_m)
    r_checks = reference_checks(ref, all_m)
    return dict(metrics=all_m, comsol_checks=[asdict(c) for c in c_checks],
                reference_checks=[asdict(c) for c in r_checks],
                comsol_available=any(v.available for v in comsol.values()))


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return str(o)


def main() -> int:
    res = analyze()
    out = RESULTS / "analysis.json"
    out.write_text(json.dumps(res, indent=1, default=_json_default), encoding="utf-8")
    bug = False
    for title, key in (("COMSOL checks", "comsol_checks"), ("Reference-model checks", "reference_checks")):
        print(f"== {title}")
        for c in res[key]:
            print(f"  [{c['status']:7s}] {c['cid']:3s} {c['name']}: {c['detail']}")
            bug |= c["status"] == "BUG"
    print(f"wrote {out.relative_to(ROOT)}")
    if bug:
        print("!! BUG: net cooling >= 0.1 K detected (spec §0 rule 6). Investigate before reporting.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
