"""Driver A -- loop over config/variants.yaml, solve, export the CSVs of spec §6.

    python comsol/python/run_variants.py --set core        # V0, V1
    python comsol/python/run_variants.py --set full        # whole matrix (§7)
    python comsol/python/run_variants.py --ids V4,V8a
    python comsol/python/run_variants.py --set core --dry-run   # list runs, no COMSOL

Each run reloads comsol/models/pin_peltier_base.mph (so no setting leaks from one
variant into the next), applies the variant with model.parameter(...) and the
physics switches, re-runs geometry and mesh, solves Study 1 and the studies of
its thermal configurations, and writes results/<variant_id>/:

    global_vs_VF.csv      spec §6.1 (+ V_ifield for check C4)
    profiles_VF{v}.csv    spec §6.2, v in {0, 0.6, 0.7, 0.75, 0.8}
    room_sweep.csv        spec §6.3 (Config A runs)
    float_vs_VF.csv       Config B point temperatures (merged into global_vs_VF)
    lat_vs_VF.csv         Config C point temperatures
    reverse_bias_*.csv    VF = -0.5 V (check C8, V0/V1)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from api_names import TAGS as T, ApiNameError  # noqa: E402
from common.csvio import write_csv  # noqa: E402
from common.params import expand_variants, load_base, parse_range  # noqa: E402

LOG = logging.getLogger("pin_peltier")
MODELS = ROOT / "comsol" / "models"
BASE_MPH = MODELS / "pin_peltier_base.mph"
RESULTS = ROOT / "results"
REVERSE_VF = "range(0,-0.025,-0.5)"


# ===================================================================== applying a variant
def apply_variant(b, run: dict) -> None:
    """Apply parameters and physics switches of one run to builder `b` (spec §7)."""
    base = load_base()
    for name, (expr, _) in base["parameters"].items():      # reset, then override
        if name not in ("Nc_si", "Nv_si"):                    # keep material read-back values
            b.model.parameter(name, str(expr))
    for name, expr in run.get("params", {}).items():
        b.model.parameter(name, str(expr))
    b.set_statistics(run.get("stats", "MB"))
    b.set_bgn(run.get("bgn", "off"))
    b.set_mobility(run.get("mobility", b.mobility_base), bool(run.get("fletcher", False)))
    b.set_heat_source(run.get("qsrc", "builtin"))
    b.comp.geom(T["geom"]).run()
    b.build_mesh(float(run.get("params", {}).get("mesh_factor", 1)))


# ===================================================================== export helpers
def _header(b, run: dict, version: str) -> dict:
    return {"source": "COMSOL (Driver A, MPh)", "COMSOL version": version, "variant": run["id"],
            "params": "; ".join(f"{k}={v}" for k, v in run.get("params", {}).items()),
            "switches": f"stats={run.get('stats')} bgn={run.get('bgn')} mobility={run.get('mobility')} "
                        f"fletcher={run.get('fletcher')} qsrc={run.get('qsrc')}",
            "material": b.material_used, "heat source": b.hs_expr,
            "api names": json.dumps(b.names),
            "T_P1,T_P5,T_P3": "std_float (Config B)", "qx_0,qx_L,Q_room": "std_eq_iv (Config A, dT_sink=0)",
            "units": "SI (V, A, A/m^2, W, W/m^2, K); energies in eV"}


def global_table(b, study: str) -> pd.DataFrame:
    g = lambda e, **kw: b.eval_global(e, study, **kw)  # noqa: E731
    hs, tf = b.hs_expr, b.var("TFLUX_X")
    Ac = b.param_value("Ac")
    Pi_sum = b.param_value("Pi_nc+Pi_pc")
    VF = g("VF", unit="V")
    I = np.abs(g(b.var("I_TERMINAL"), unit="A"))
    J = I / Ac
    df = pd.DataFrame(dict(VF=VF, I=I, J=J, P_el=I * VF))
    df["Qtot_int"] = Ac * g(f"intop_all({hs})", unit="W/m^2")
    df["Qjn_n"] = Ac * g(f"intop_all(({hs})*(x<Wn+5[um]))", unit="W/m^2")
    df["Qjn_p"] = Ac * g(f"intop_all(({hs})*(x>Ltot-Wp-5[um]))", unit="W/m^2")
    df["Qc_contacts"] = -J * Ac * Pi_sum
    try:
        df["qx_0"] = g(f"pt_n({tf})", unit="W/m^2")
        df["qx_L"] = g(f"pt_p({tf})", unit="W/m^2")
        df["T_P1"], df["T_P5"], df["T_P3"] = (g(f"{p}(T)", unit="K") for p in ("pt_n", "pt_p", "pt_c"))
        df["Q_room"] = Ac * (df.qx_0 - df.qx_L + J * Pi_sum)
    except Exception as exc:  # semi-only study
        LOG.debug("no ht quantities in %s: %s", study, exc)
    with np.errstate(divide="ignore", invalid="ignore"):
        df["eta_E"] = np.where(df.P_el > 0, (df.Qtot_int + df.Qc_contacts) / df.P_el, np.nan)
    df["V_ifield"] = -g(f"intop_i({b.var('E_X')})", unit="V")
    return df


def point_temps(b, study: str) -> pd.DataFrame:
    g = lambda e: b.eval_global(e, study, unit="K")  # noqa: E731
    return pd.DataFrame(dict(VF=b.eval_global("VF", study, unit="V"), T_P1=g("pt_n(T)"),
                             T_P5=g("pt_p(T)"), T_P3=g("pt_c(T)")))


PROFILE_COLS = ["x", "Ec", "Ev", "Efn", "Efp", "n", "p", "Ndop", "JdotE", "Q_tot", "Q_rec", "T", "tfluxX"]


def profiles(b, study_semi: str, study_T: str, VFs: list[float]) -> dict[float, pd.DataFrame]:
    """Spec §6.2 profiles at mesh nodes; carriers/heat from study_semi, T/flux from study_T
    (identical semi solution in both because of one-way coupling)."""
    jx, ex, hs = b.var("J_X"), b.var("E_X"), b.hs_expr
    exprs = ["x", b.var("EC"), b.var("EV"), b.var("EFN"), b.var("EFP"), b.var("N_E"), b.var("P_H"),
             b.var("NDOP"), f"{jx}*{ex}", hs, f"({hs})-{jx}*{ex}"]
    units = ["m", "eV", "eV", "eV", "eV", "1/m^3", "1/m^3", "1/m^3", "W/m^3", "W/m^3", "W/m^3"]
    vals = b.eval_field(exprs, study_semi, unit=units)
    tvals = b.eval_field(["x", "T", b.var("TFLUX_X")], study_T, unit=["m", "K", "W/m^2"])
    VFa = b.eval_global("VF", study_semi, unit="V")
    VFt = b.eval_global("VF", study_T, unit="V")
    out = {}
    for v in VFs:
        i = int(np.argmin(np.abs(VFa - v)))
        k = int(np.argmin(np.abs(VFt - v)))
        if abs(VFa[i] - v) > 1e-9 or abs(VFt[k] - v) > 1e-9:
            LOG.warning("VF=%g not on the sweep grid; skipped", v)
            continue
        cols = {c: a[i] for c, a in zip(PROFILE_COLS[:11], vals)}
        if not np.allclose(tvals[0][k], cols["x"]):
            raise RuntimeError("profile export: node coordinates differ between studies")
        cols["T"], cols["tfluxX"] = tvals[1][k], tvals[2][k]
        df = pd.DataFrame(cols)[PROFILE_COLS]
        df = df.sort_values("x", kind="stable").reset_index(drop=True)
        out[v] = df
    return out


def room_sweep(b) -> pd.DataFrame:
    """Q_room(VF, dT_sink) from the Parametric Sweep of std_room; driver-loop fallback."""
    base = load_base()
    dTs = parse_range(base["sweeps"]["dT_sink"])
    tf, I_t = b.var("TFLUX_X"), b.var("I_TERMINAL")
    expr = f"Ac*(pt_n({tf})-pt_p({tf}))+abs({I_t})*(Pi_nc+Pi_pc)"
    rows = []
    try:
        for k, d in enumerate(dTs, start=1):
            VF = b.eval_global("VF", T["std_room"], unit="V", parametric=True, outer=k)
            Q = b.eval_global(expr, T["std_room"], unit="W", parametric=True, outer=k)
            rows += [dict(VF=v, dT_sink=d, Q_room=q) for v, q in zip(VF, Q)]
        return pd.DataFrame(rows)
    except Exception as exc:
        LOG.warning("parametric dataset export failed (%s) -> driver loop over dT_sink", exc)
    std = b.j.study(T["std_room"])
    std.feature("param").active(False)
    try:
        for d in dTs:
            b.model.parameter("dT_sink", f"{d:.6g}[K]")
            b.solve(T["std_room"])
            VF = b.eval_global("VF", T["std_room"], unit="V")
            Q = b.eval_global(expr, T["std_room"], unit="W")
            rows += [dict(VF=v, dT_sink=d, Q_room=q) for v, q in zip(VF, Q)]
    finally:
        std.feature("param").active(True)
        b.model.parameter("dT_sink", "0[K]")
    return pd.DataFrame(rows)


def reverse_bias(b, hdr: dict, out: Path) -> None:
    """Check C8: VF = -0.5 V on Study 1 (Config A)."""
    st = b.j.study(T["std_eq_iv"]).feature("stat")
    fwd = str(st.getStringArray("plistarr")[0])
    st.set("plistarr", [REVERSE_VF])
    try:
        b.solve(T["std_eq_iv"])
        g = global_table(b, T["std_eq_iv"])
        write_csv(out / "reverse_bias_global.csv", g, {**hdr, "sweep": REVERSE_VF})
        hs = b.hs_expr
        x, q = b.eval_field(["x", hs], T["std_eq_iv"], unit=["m", "W/m^3"])
        write_csv(out / "reverse_bias_profile.csv",
                  pd.DataFrame(dict(x=x[-1], Q_tot=q[-1])).sort_values("x"), {**hdr, "VF": -0.5})
    finally:
        st.set("plistarr", [fwd])


def export_variant(b, run: dict, out_root: Path = RESULTS, solve: bool = True, reverse: bool = True,
                   version: str = "6.3") -> Path:
    out = out_root / run["id"]
    out.mkdir(parents=True, exist_ok=True)
    hdr = _header(b, run, version)
    base = load_base()
    t0 = time.time()
    if solve:
        b.solve(T["std_eq_iv"])
    glob = global_table(b, T["std_eq_iv"])
    cfgs = run.get("configs", ["A", "B"])
    study_T = T["std_eq_iv"]
    if "B" in cfgs:
        if solve:
            b.solve(T["std_float"])
        fl = point_temps(b, T["std_float"])
        write_csv(out / "float_vs_VF.csv", fl, hdr)
        for c in ("T_P1", "T_P5", "T_P3"):
            glob[c] = np.interp(glob.VF, fl.VF, fl[c])
        study_T = T["std_float"]
    else:
        for c in ("T_P1", "T_P5", "T_P3"):
            glob[c] = np.nan
    if "C" in cfgs:
        if solve:
            b.solve(T["std_lat"])
        write_csv(out / "lat_vs_VF.csv", point_temps(b, T["std_lat"]), hdr)
        study_T = study_T if "B" in cfgs else T["std_lat"]
    write_csv(out / "global_vs_VF.csv", glob, hdr)
    for v, df in profiles(b, T["std_eq_iv"], study_T, base["sweeps"]["profile_VF"]).items():
        write_csv(out / f"profiles_VF{v:g}.csv", df, {**hdr, "VF": v, "T,tfluxX from": study_T})
    if "A" in cfgs:
        if solve:
            b.solve(T["std_room"])
        write_csv(out / "room_sweep.csv", room_sweep(b), hdr)
    if reverse:
        reverse_bias(b, hdr, out)
    LOG.info("variant %s exported to %s (%.1f s)", run["id"], out, time.time() - t0)
    return out


# ===================================================================== main loop
def load_builder(client, path: Path = BASE_MPH):
    from build_model import PinPeltierBuilder
    model = client.load(str(path))
    b = PinPeltierBuilder(model, client)
    info = json.loads((MODELS / "build_info.json").read_text(encoding="utf-8"))
    b.material_used, b.mobility_base, b.names = info["material"], info["mobility_base"], info["names"]
    b.hs_expr = info["hs_expr"]
    b._dists = {t: b.comp.mesh(T["mesh"]).feature("edg1").feature(t) for t in ("dis_n", "dis_p", "dis_iL", "dis_iR")}
    return b


def resolve_runs(set_name: str | None, ids: str | None) -> list[dict]:
    return expand_variants(ids=ids.split(",")) if ids else expand_variants(set_name or "core")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", default="core", choices=["core", "full"])
    ap.add_argument("--ids", default=None, help="comma-separated run ids or parent ids (e.g. V5)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-reverse", action="store_true", help="skip the VF=-0.5 V run (check C8)")
    ap.add_argument("--cores", type=int, default=None)
    a = ap.parse_args(argv)
    runs = resolve_runs(a.set, a.ids)
    if a.dry_run:
        for r in runs:
            print(f"{r['id']:<34s} configs={','.join(r['configs'])} qsrc={r['qsrc']} stats={r['stats']} "
                  f"bgn={r['bgn']} mob={r['mobility']} fletcher={r['fletcher']} params={r['params']}")
        print(f"{len(runs)} runs")
        return 0
    from build_model import setup_logging
    setup_logging(RESULTS / "run_variants.log")
    if not BASE_MPH.exists():
        LOG.error("%s missing: run comsol/python/build_model.py first", BASE_MPH)
        return 1
    import mph
    from env import comsol_version, user_env
    client = mph.start(cores=a.cores or user_env().get("mph", {}).get("cores", 4), version=comsol_version())
    version = str(client.version)
    failed = []
    for r in runs:
        b = load_builder(client)
        try:
            if r.get("mobility") == "M1" and b.material_used != "library":
                r = dict(r, mobility="M2")
                LOG.warning("%s: M1 needs the library material -> running with M2", r["id"])
            if r.get("fletcher") or r.get("bgn") == "slotboom":
                if b.material_used != "library":
                    LOG.error("%s needs library material parameters (BGN/Fletcher); skipped", r["id"])
                    failed.append((r["id"], "needs library material"))
                    continue
            apply_variant(b, r)
            export_variant(b, r, reverse=(not a.no_reverse) and r["id"] in ("V0", "V1"), version=version)
        except ApiNameError as e:
            LOG.error("%s", e)
            return 3
        except Exception as e:  # keep going with the other variants
            LOG.exception("variant %s failed: %s", r["id"], e)
            failed.append((r["id"], str(e).splitlines()[0]))
        finally:
            client.remove(b.model)
    if failed:
        LOG.warning("failed runs: %s", failed)
    return 0 if not failed else 4


if __name__ == "__main__":
    sys.exit(main())
