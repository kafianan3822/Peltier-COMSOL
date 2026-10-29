"""Write results/summary.md (spec §8.5): variant table, checks C1-C9, figure links,
a short auto-generated conclusion that states the numbers, and the references.

    python postprocess/report.py

Runs analyze.py and plots.py first. Without COMSOL results the COMSOL table and
checks are reported as PENDING placeholders and the reference-model numbers
are shown separately, clearly labelled.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "postprocess"))

import analyze as an  # noqa: E402

OUT = ROOT / "results" / "summary.md"

REFERENCES = [
    "COMSOL Semiconductor Module User's Guide, \"Nonisothermal Models\" (simplified heat source; `semi.Q_tot`). "
    "https://doc.comsol.com/6.4/doc/com.comsol.help.semicond/semicond_ug_modeling.5.18.html",
    "COMSOL Application Library, *Thermal Analysis of a Bipolar Transistor* "
    "(Semiconductor_Module/Transistors/bipolar_transistor_thermal).",
    "G. K. Wachutka, \"Rigorous thermodynamic treatment of heat generation and conduction in semiconductor "
    "device modeling,\" *IEEE Trans. CAD* 9(11), 1141-1149 (1990).",
    "K. P. Pipe, R. J. Ram, A. Shakouri, \"Bias-dependent Peltier coefficient and internal cooling in bipolar "
    "devices,\" *Phys. Rev. B* 66, 125316 (2002).",
    "J. Dziewior, W. Schmid, \"Auger coefficients for highly doped and highly excited silicon,\" "
    "*Appl. Phys. Lett.* 31, 346 (1977).",
    "D. M. Caughey, R. E. Thomas, \"Carrier mobilities in silicon empirically related to doping and field,\" "
    "*Proc. IEEE* 55, 2192 (1967).",
    "T. Sadi, I. Radevici, J. Oksanen, \"Thermophotonic cooling with light-emitting diodes,\" "
    "*Nature Photonics* 14, 205 (2020).",
]


def f(v, scale=1.0, fmt="{:.3f}", none="-"):
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return none
    return fmt.format(v * scale)


def table(metrics: list[dict]) -> list[str]:
    hdr = ("| Variant | dT_max @0.7 V | best dT_max (VF) | Q_room(dT=0) @0.7 V | COP(dT=0) | COP(dT_max/2) "
           "| eta_E @0.7 V | T_end-T_room, Config B |")
    lines = [hdr, "|---|---|---|---|---|---|---|---|"]
    for m in metrics:
        if not m.get("available"):
            continue
        best = (f"{m['dT_max_best']*1e3:.3f} mK ({m['VF_best']:.3f} V)" if m.get("dT_max_best") is not None
                and math.isfinite(m.get("dT_max_best", float("nan"))) else "-")
        lines.append(f"| {m['variant']} | {m.get('dT_max_text', '-')} | {best} | {f(m.get('Q_room'), 1e3)} mW "
                     f"| {f(m.get('cop0'), fmt='{:.3g}')} | {f(m.get('cop_half'), fmt='{:.3g}')} "
                     f"| {f(m.get('eta_E'), fmt='{:.4f}')} | {f(m.get('dT_end_B'), 1e3, '{:+.3f}')} mK |")
    return lines


def checks_md(checks: list[dict]) -> list[str]:
    icon = {"PASS": "PASS", "FAIL": "**FAIL**", "BUG": "**BUG**", "PENDING": "PENDING", "N/A": "N/A"}
    out = ["| # | Check | Status | Detail |", "|---|---|---|---|"]
    for c in checks:
        out.append(f"| {c['cid']} | {c['name']} | {icon.get(c['status'], c['status'])} | {c['detail']} |")
    return out


def conclusion(res: dict) -> str:
    ref = {m["variant"]: m for m in res["metrics"] if m["source"] == "reference" and m.get("available")}
    com = {m["variant"]: m for m in res["metrics"] if m["source"] == "comsol" and m.get("available")}
    src, d = ("COMSOL", com) if "V0" in com and "V1" in com else ("reference-model", ref)
    if "V0" not in d or "V1" not in d:
        return "No V0/V1 results are available yet. Run `python reference/reference_model.py` first."
    v0, v1 = d["V0"], d["V1"]
    s = [f"In the {src} results at VF = 0.7 V, the device as drawn (V0, uniform lifetime) "
         f"{'heats' if v0['dT_end_B'] > 0 else 'cools'} its junction ends by "
         f"{abs(v0['dT_end_B'])*1e3:.3f} mK relative to the sink in Config B. "
         f"Config A gives Q_room = {v0['Q_room']*1e3:.3f} mW and dT_max = {v0.get('dT_max_text', '-')}. "
         "Recombination heat flows back to the ends, so the room is heated."]
    s.append(f"With the engineered central recombination zone (V1) the ends cool by "
             f"{-v1['dT_end_B']*1e3:.3f} mK. Config A gives Q_room(dT=0) = {v1['Q_room']*1e3:.3f} mW, "
             f"COP = {f(v1.get('cop0'), fmt='{:.2f}')} and dT_max = {v1.get('dT_max_text', '-')}")
    if v1.get("dT_max_best") is not None:
        s[-1] += (f". dT_max rises to {v1['dT_max_best']*1e3:.2f} mK at VF = {v1['VF_best']:.3f} V, "
                  "the top of the Study 2 sweep.")
    else:
        s[-1] += "."
    s.append("Junction cooling is therefore real but milli-kelvin in size, consistent with the estimate "
             "dT ~ n_b D_a Pi/k (Fig. 7).")
    casc = ROOT / "results" / "cascade.md"
    if casc.exists():
        s.append("Stacking does not change this: see `results/cascade.md` (about 2000 series stages for 10 K, "
                 "with an electrical power multiplier of about 10^1556 at COP = 0.2 per stage).")
    if src != "COMSOL":
        s.append("These numbers come from the COMSOL-independent reference model. The COMSOL results, and with "
                 "them checks C1-C9, are pending (see 'Not executed').")
    return " ".join(s)


def main() -> int:
    import plots
    res = an.analyze()
    (ROOT / "results" / "analysis.json").write_text(json.dumps(res, indent=1, default=an._json_default),
                                                    encoding="utf-8")
    plots.main()
    figs = json.loads((ROOT / "results" / "figures" / "index.json").read_text(encoding="utf-8"))
    com = [m for m in res["metrics"] if m["source"] == "comsol"]
    ref = [m for m in res["metrics"] if m["source"] == "reference"]
    have_c = res["comsol_available"]
    L = ["# PIN-diode junction cooling: results summary", "",
         f"_Generated {dt.datetime.now().isoformat(timespec='seconds')} by `postprocess/report.py`._", "",
         "Sign conventions: Q_room > 0 means the room is cooled. dT_max is the sink-minus-room temperature at "
         "which Q_room = 0 (Config A); 'none (room heated)' means Q_room < 0 already at dT_sink = 0. "
         "For Config-B-only runs (V5, V6), dT_max = T_room - T_end, which is exact for the symmetric 1D bar.", ""]
    L += ["## 1. COMSOL results", ""]
    if have_c:
        L += table(com)
    else:
        L += ["**PENDING.** No COMSOL results were found in `results/<variant>/`. This table is filled in once you run "
              "`python comsol/python/build_model.py` and `python comsol/python/run_variants.py --set core` "
              "(or `comsol/java/build_and_run.bat`), then `python postprocess/report.py`.", "",
              "| Variant | dT_max @0.7 V | best dT_max (VF) | Q_room(dT=0) @0.7 V | COP(dT=0) | COP(dT_max/2) "
              "| eta_E @0.7 V | T_end-T_room, Config B |", "|---|---|---|---|---|---|---|---|",
              "| V0 | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ |",
              "| V1 | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ |"]
    flags = [r for r in an.expand_variants("full") if r.get("flag")]
    if flags:
        L += ["", "Flags: " + "; ".join(f"{r['id']}: {r['flag']}" for r in flags) + "."]
    L += ["", "## 2. Reference model (COMSOL-independent, spec §11)", "",
          "Ambipolar high-injection model of the i-region with lumped end sinks. eta_E = 1 by construction, because "
          "it books the full E_g + 3k_BT - qV_j per pair. Lifetime convention: `srh_hl` (see CHANGES.md).", ""]
    L += table([m for m in ref if m["variant"] in ("V0", "V1")])
    L += ["", "<details><summary>V5 / V6 sweeps (reference model)</summary>", ""]
    L += table([m for m in ref if m["variant"] not in ("V0", "V1")])
    L += ["", "</details>", "", "## 3. Verification checks (spec §10)", "", "### COMSOL checks C1-C9", ""]
    L += checks_md(res["comsol_checks"])
    L += ["", "### Reference-model sanity checks", ""]
    L += checks_md(res["reference_checks"])
    bug = any(c["status"] == "BUG" for c in res["comsol_checks"] + res["reference_checks"])
    if bug:
        L += ["", "> **BUG: net cooling of at least 0.1 K was detected. Do not report these numbers. "
              "Check the boundary-flux sign convention and the heat-source expression first.**"]
    L += ["", "## 4. Figures", ""]
    for e in figs:
        L.append(f"- [{e['name']}](figures/{e['name']}.png) ([pdf](figures/{e['name']}.pdf)): {e['caption']} "
                 f"_[{e['source']}]_")
    L += ["", "## 5. Conclusion", "", conclusion(res), "", "## 6. Not executed", ""]
    if have_c:
        L.append("All requested COMSOL runs that produced `results/<variant>/global_vs_VF.csv` are included above.")
    else:
        L += ["- COMSOL 6.3 was not reachable on the machine that generated this file, so stages 1-8, V0/V1 and the "
              "remaining variant matrix were not solved.",
              "- As a result, checks C1-C9 are PENDING. Figures 1 and 9 are placeholders or reference-only.",
              "- Before the first COMSOL run, the ⚠VERIFY API names must be confirmed (docs/VERIFY_API_NAMES.md)."]
    L += ["", "## References", ""] + [f"{i}. {r}" for i, r in enumerate(REFERENCES, 1)] + [""]
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 2 if bug else 0


if __name__ == "__main__":
    sys.exit(main())
