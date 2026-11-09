"""Driver A for the final device (config/final_device.yaml): extended VF sweep up to 1.5 V.

    python comsol/python/run_final.py                 # FINAL and V1x (about 1-2 h)
    python comsol/python/run_final.py --set all       # + FINAL_scan (6 Config-B-only runs)
    python comsol/python/run_final.py --ids FINAL     # one run
    python comsol/python/run_final.py --dry-run       # list the runs, no COMSOL
    python comsol/python/run_final.py --vf-max 1.2 --vf-step 0.02   # override the sweep

Uses the same base model (comsol/models/pin_peltier_base.mph, from build_model.py) and
the same export code as run_variants.py, so the CSV files in results/<id>/ have the
usual format. The only differences are the sweeps (Studies 1-4 go from 0 to VF_max) and
the run definitions. If a run does not converge up to VF_max, it is repeated with the
next value of VF_max_fallbacks (1.5 -> 1.3 -> 1.1 V) and the report says so.

Afterwards: python postprocess/final_report.py
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from api_names import ApiNameError  # noqa: E402
from common.params import expand_final, parse_range  # noqa: E402
from run_variants import BASE_MPH, RESULTS, apply_variant, export_variant, load_builder, set_sweeps  # noqa: E402

LOG = logging.getLogger("run_final")


def sweeps_for(run: dict, vf_max: float, vf_step: float | None = None) -> dict:
    """The run's sweeps with VF_iv / VF_room cut (or re-stepped) at vf_max."""
    sw = dict(run["sweeps"])
    for key in ("VF_iv", "VF_room"):
        v = parse_range(sw[key])
        step = vf_step or float(v[1] - v[0])
        sw[key] = f"range(0,{step:g},{vf_max:g})"
    sw["profile_VF"] = [v for v in sw["profile_VF"] if v <= vf_max + 1e-9]
    return sw


def run_one(client, run: dict, vf_maxes: list[float], vf_step: float | None, version: str) -> dict:
    """Solve and export one run, falling back to a lower VF_max on non-convergence."""
    last = None
    for vf_max in vf_maxes:
        b = load_builder(client)
        try:
            apply_variant(b, run)
            sw = sweeps_for(run, vf_max, vf_step)
            set_sweeps(b, sw)
            out = export_variant(b, run, reverse=False, version=version, sweeps=sw)
            info = dict(id=run["id"], VF_max=vf_max, sweeps=sw, status="ok",
                        note="" if vf_max == vf_maxes[0] else f"converged only up to {vf_max} V")
            (out / "final_run.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
            return info
        except ApiNameError:
            raise
        except Exception as exc:  # non-convergence at high bias -> lower VF_max
            last = " ".join(str(exc).split())[:300]
            LOG.warning("%s did not finish with VF_max = %g V: %s", run["id"], vf_max, last)
        finally:
            client.remove(b.model)
    return dict(id=run["id"], status="failed", error=last)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", default="default", choices=["default", "all"])
    ap.add_argument("--ids", default=None, help="comma-separated ids from config/final_device.yaml")
    ap.add_argument("--vf-max", type=float, default=None, help="override VF_max (V), default 1.5")
    ap.add_argument("--vf-step", type=float, default=None, help="override the VF step (V), default 0.01")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cores", type=int, default=None)
    a = ap.parse_args(argv)
    runs = expand_final(ids=a.ids.split(",")) if a.ids else expand_final(a.set)
    vf_maxes = [a.vf_max] if a.vf_max else list(runs[0]["sweeps"]["VF_max_fallbacks"])
    if a.dry_run:
        for r in runs:
            sw = sweeps_for(r, vf_maxes[0], a.vf_step)
            print(f"{r['id']:<40s} configs={','.join(r['configs'])} qsrc={r['qsrc']} fletcher={r['fletcher']} "
                  f"params={r['params']} VF_iv={sw['VF_iv']}")
        print(f"{len(runs)} runs; VF_max fallbacks {vf_maxes}")
        return 0
    from build_model import setup_logging
    setup_logging(RESULTS / "run_final.log")
    if not BASE_MPH.exists():
        LOG.error("%s missing: run comsol/python/build_model.py first", BASE_MPH)
        return 1
    import mph
    from env import comsol_version, user_env
    client = mph.start(cores=a.cores or user_env().get("mph", {}).get("cores", 4), version=comsol_version())
    version = str(client.version)
    done = []
    for r in runs:
        try:
            probe = load_builder(client)
            ok = probe.mobility_base == "M1" and probe.material_used == "library"
            client.remove(probe.model)
            if r.get("fletcher") and not ok:
                LOG.warning("%s: Fletcher needs the library material with Arora mobility; running without it",
                            r["id"])
                r = dict(r, fletcher=False)
            LOG.info("== %s: %s", r["id"], r["purpose"])
            done.append(run_one(client, r, vf_maxes, a.vf_step, version))
        except ApiNameError as e:
            LOG.error("%s", e)
            return 3
    (RESULTS / "final_runs.json").write_text(json.dumps(done, indent=1), encoding="utf-8")
    failed = [d for d in done if d["status"] != "ok"]
    for d in done:
        LOG.info("%-40s %s %s", d["id"], d["status"], d.get("note") or d.get("error") or "")
    LOG.info("next: python postprocess/final_report.py")
    return 4 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
