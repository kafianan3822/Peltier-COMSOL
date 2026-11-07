"""Ask COMSOL for the real property names and allowed values of every node type the
builders use, and write them to results/api_dump.txt.

    python comsol/python/inspect_api.py

Run it once on the machine with COMSOL and send results/api_dump.txt to whoever
maintains the scripts: it settles the remaining ⚠VERIFY names in one go. It builds
a throw-away 1D model in memory (nothing is saved) and never stops on an error;
every failure is written into the dump.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

OUT = ROOT / "results" / "api_dump.txt"
LINES: list[str] = []


def w(s: str = "") -> None:
    LINES.append(s)
    print(s)


def first_line(exc) -> str:
    s = str(exc).strip()
    return s.splitlines()[0] if s else type(exc).__name__


def value_of(f, p: str) -> str:
    for getter in ("getString", "getStringArray"):
        try:
            v = getattr(f, getter)(p)
            return str(v) if getter == "getString" else "[" + ", ".join(str(x) for x in v) + "]"
        except Exception:
            continue
    return "<?>"


def dump(f, title: str) -> None:
    w(f"\n=== {title}")
    try:
        w(f"type: {f.getType()}")
    except Exception:
        pass
    try:
        props = [str(p) for p in f.properties()]
    except Exception as exc:
        w(f"  (properties() failed: {first_line(exc)})")
        return
    for p in props:
        line = f"  {p} = {value_of(f, p)}"
        try:
            allowed = [str(a) for a in f.getAllowedPropertyValues(p)]
            if allowed:
                line += "   allowed: " + ", ".join(allowed)
        except Exception:
            pass
        w(line)
    try:
        kids = [str(t) for t in f.feature().tags()]
        if kids:
            w(f"  children: {', '.join(kids)}")
    except Exception:
        pass


def attempt(title: str, fn):
    try:
        r = fn()
        w(f"\n[ok] {title}")
        return r
    except Exception as exc:
        w(f"\n[FAILED] {title}: {first_line(exc)}")
        return None


def main() -> int:
    import mph
    from env import comsol_version
    client = mph.start(cores=1, version=comsol_version())
    w(f"COMSOL {client.version}")
    model = client.create("api_probe")
    j = model.java
    try:
        for n, e in (("Wn", "2[um]"), ("Wi", "1[mm]"), ("Ac", "1[mm^2]"), ("VF", "0.5[V]"), ("T0", "300[K]")):
            j.param().set(n, e)
        j.component().create("comp1", True)
        g = j.component("comp1").geom().create("geom1", 1)
        i1 = g.create("i1", "Interval")
        try:
            i1.set("intervals", "many")
            i1.set("p", ["0", "Wn", "Wn+Wi"])
        except Exception:
            pass
        g.run()
        comp = j.component("comp1")

        # ---------------------------------------------------------- physics interfaces
        semi = attempt("create semi (Semiconductor)", lambda: comp.physics().create("semi", "Semiconductor", "geom1"))
        ht = attempt("create ht (HeatTransfer)", lambda: comp.physics().create("ht", "HeatTransfer", "geom1"))
        for name, phys, groups in (("semi", semi, ["d", "ModelProperties", "ShapeProperty", "Continuation"]),
                                   ("ht", ht, ["d", "ShapeProperty", "PhysicalModelProperty", "ModelProperties",
                                               "ConsistentStabilization", "AdvancedSettings"])):
            if phys is None:
                continue
            for gname in groups:
                pg = attempt(f"{name}.prop('{gname}')", lambda p=phys, gn=gname: p.prop(gn))
                if pg is not None:
                    dump(pg, f"{name}.prop('{gname}')")
            try:
                w(f"\n{name} default children: {', '.join(str(t) for t in phys.feature().tags())}")
            except Exception:
                pass

        if semi is not None:
            for tag in [str(t) for t in semi.feature().tags()]:
                dump(semi.feature(tag), f"semi default child {tag}")
            features = [
                ("adm1", "AnalyticDopingModel", 1), ("gdm1", "GeometricDopingModel", 1),
                ("tar1", "TrapAssistedRecombination", 1), ("auger1", "AugerRecombination", 1),
                ("mc1", "MetalContact", 0),
            ]
            for tag, ftype, dim in features:
                f = attempt(f"semi.create({tag}, {ftype}, {dim})", lambda t=tag, ft=ftype, d=dim: semi.create(t, ft, d))
                if f is not None:
                    try:
                        f.selection().all() if dim == 1 else f.selection().set([1])
                    except Exception:
                        pass
                    dump(f, f"semi feature {tag} ({ftype})")
            smm = semi.feature("smm1")
            for tag, ftype in (("mmal1", "AroraMobilityModel"), ("mmfc1", "FletcherMobilityModel"),
                               ("mmct1", "CaugheyThomasMobilityModel"), ("mmud1", "UserDefinedMobilityModel"),
                               ("mmpl1", "PowerLawMobilityModel")):
                f = attempt(f"smm1.create({tag}, {ftype})", lambda t=tag, ft=ftype: smm.create(t, ft, 1))
                if f is not None:
                    dump(f, f"mobility {tag} ({ftype})")
            dump(smm, "semi smm1 AFTER adding mobility models (look for the mobility selectors)")

        if ht is not None:
            dump(ht.feature("init1") if "init1" in [str(t) for t in ht.feature().tags()] else ht, "ht init")
            for tag in [str(t) for t in ht.feature().tags()]:
                dump(ht.feature(tag), f"ht default child {tag}")
            for tag, ftype, dim in (("hs1", "HeatSource", 1), ("bhs1", "BoundaryHeatSource", 0),
                                    ("temp1", "TemperatureBoundary", 0)):
                f = attempt(f"ht.create({tag}, {ftype}, {dim})", lambda t=tag, ft=ftype, d=dim: ht.create(t, ft, d))
                if f is not None:
                    dump(f, f"ht feature {tag} ({ftype})")
            if semi is not None:
                dump(semi.feature("smm1"), "semi smm1 AFTER ht exists (temperature source selector)")

        # ---------------------------------------------------------- functions, couplings, mesh
        rect = attempt("func Rectangle", lambda: j.func().create("rect1", "Rectangle"))
        if rect is not None:
            dump(rect, "func rect1 (Rectangle)")
        cpl = attempt("cpl Integration", lambda: comp.cpl().create("intop1", "Integration"))
        if cpl is not None:
            dump(cpl, "cpl intop1 (Integration)")
        mesh = comp.mesh().create("mesh1")
        edg = attempt("mesh Edge", lambda: mesh.create("edg1", "Edge"))
        if edg is not None:
            dis = attempt("mesh Distribution", lambda: edg.create("dis1", "Distribution"))
            if dis is not None:
                dump(dis, "mesh dis1 (Distribution)")

        # ---------------------------------------------------------- studies and solver
        std = j.study().create("std1")
        for tag, ftype in (("sseq", "SemiconductorEquilibrium"), ("stat", "Stationary")):
            f = attempt(f"study.create({tag}, {ftype})", lambda t=tag, ft=ftype: std.create(t, ft))
            if f is not None:
                dump(f, f"study step {tag} ({ftype})")
        std2 = j.study().create("std2")
        attempt("std2 Stationary", lambda: std2.create("stat", "Stationary"))
        ps = attempt("study Parametric", lambda: std2.create("param", "Parametric"))
        if ps is not None:
            dump(ps, "study param (Parametric)")
        try:
            std.createAutoSequences("all")
            for st in [str(t) for t in j.sol().tags()]:
                s = j.sol(st)
                for ft in [str(t) for t in s.feature().tags()]:
                    dump(s.feature(ft), f"solver {st}/{ft}")
                    try:
                        for ct in [str(t) for t in s.feature(ft).feature().tags()]:
                            dump(s.feature(ft).feature(ct), f"solver {st}/{ft}/{ct}")
                    except Exception:
                        pass
                    if str(s.feature(ft).getType()) == "Stationary":
                        se = attempt("create Segregated", lambda f=s.feature(ft): f.create("se1", "Segregated"))
                        if se is not None:
                            for ct in [str(t) for t in se.feature().tags()]:
                                dump(se.feature(ct), f"segregated child {ct}")
        except Exception as exc:
            w(f"\n[FAILED] solver sequence: {first_line(exc)}")
    except Exception:
        w("\n[UNEXPECTED]\n" + traceback.format_exc())
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text("\n".join(LINES) + "\n", encoding="utf-8")
        print(f"\nwrote {OUT}")
        try:
            client.remove(model)
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
