"""Driver A -- build the PIN junction-cooling model through MPh (COMSOL Java API).

    python comsol/python/build_model.py                 # stages 1-8, saves comsol/models/*.mph
    python comsol/python/build_model.py --until 4       # stop after stage 4
    python comsol/python/build_model.py --dry-run       # no COMSOL: print the plan

Staged build (spec §9).  Every stage saves comsol/models/stageN.mph and runs a
smoke test, so a failure points to exactly one node.  Stage 8 also saves
comsol/models/pin_peltier_base.mph, which run_variants.py loads.

Coupling is ONE-WAY (spec §0 rule 3): the semiconductor temperature input is
the user-defined constant T0; ht.T is never fed back into semi.

All COMSOL names that could not be confirmed offline come from api_names.py;
when COMSOL rejects one, ApiNameError names the constant and how to verify it.
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import api_names as api  # noqa: E402
from api_names import ALL_THERMAL_NODES, CONFIG_NODES, TAGS, ApiNameError  # noqa: E402
from common.params import load_base, parse_range  # noqa: E402

MODELS = ROOT / "comsol" / "models"
SI_LIBRARY_MPH = ROOT / "comsol" / "materials" / "Si_library.mph"
LOG = logging.getLogger("pin_peltier")

T = TAGS
STUDY_OF_CONFIG = {"A": T["std_room"], "B": T["std_float"], "C": T["std_lat"]}


def setup_logging(path: Path | None = None) -> None:
    handlers = [logging.StreamHandler(sys.stdout)]
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, mode="a", encoding="utf-8"))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=handlers, force=True)


@contextmanager
def verify(key: str, extra: str = ""):
    """Translate any COMSOL exception inside the block into an ApiNameError naming `key`."""
    try:
        yield
    except ApiNameError:
        raise
    except Exception as exc:  # JPype wraps com.comsol.util.exceptions.FlException
        if "vector of length" in str(exc):
            raise RuntimeError(f"Value-format problem in the script while setting {key} (the name is right; "
                               f"COMSOL wants a different number of components; please report it): {exc}") from exc
        if "Ambiguous overloads" in str(exc):
            raise RuntimeError(f"Python/Java type problem in the script while setting {key} (not a wrong "
                               f"COMSOL name; please report it): {exc}") from exc
        raise ApiNameError(key, exc, extra) from exc


class SweepReadError(RuntimeError):
    """The study's results do not contain the complete VF sweep."""


def full_message(exc) -> str:
    """Whole COMSOL error text (all lines), indented for the log."""
    text = str(exc).strip() or type(exc).__name__
    return "\n".join("    " + line for line in text.splitlines() if line.strip())


def diag3(expr: str) -> list[str]:
    return [expr, "0", "0", "0", expr, "0", "0", "0", expr]


class PinPeltierBuilder:
    """Builds the model stage by stage on an mph.Model (or a raw Java model)."""

    def __init__(self, model, client=None, material_source: str = "auto", stage_dir: Path = MODELS):
        self.model = model
        self.client = client
        self.j = model.java if hasattr(model, "java") else model
        self.base = load_base()
        self.material_source = material_source
        self.material_used = None
        self.mobility_base = None
        self.stage_dir = stage_dir
        self.names: dict[str, str] = {}   # probed variable names
        self.hs_expr = None

    # ----------------------------------------------------------------- small helpers
    @property
    def comp(self):
        return self.j.component(T["comp"])

    @property
    def semi(self):
        return self.comp.physics(T["semi"])

    @property
    def ht(self):
        return self.comp.physics(T["ht"])

    def var(self, key: str) -> str | None:
        """Probed name of a result variable (None: optional variable not available)."""
        return self.names[key] if key in self.names else api.name(key)

    def save(self, n: int | str) -> Path:
        self.stage_dir.mkdir(parents=True, exist_ok=True)
        path = self.stage_dir / (f"stage{n}.mph" if isinstance(n, int) else n)
        self.j.save(str(path))
        LOG.info("saved %s", path)
        return path

    def set_userdef(self, feat, prop: str, value: str, key: str) -> None:
        """Set a 'From material / User defined' property to a user-defined value."""
        try:
            feat.set(prop + api.name("USERDEF_SUFFIX"), "userdef")
        except Exception:
            LOG.debug("no %s%s selector (ok if the property is always user defined)",
                      prop, api.name("USERDEF_SUFFIX"))
        with verify(key):
            feat.set(prop, value)

    def param_value(self, expr: str) -> float:
        return float(self.j.param().evaluate(expr))

    # ================================================================= STAGE 1
    def stage1(self) -> None:
        """Parameters, functions, variables, geometry, couplings, mesh."""
        LOG.info("== stage 1: parameters, functions, variables, geometry")
        for name, (expr, desc) in self.base["parameters"].items():
            self.j.param().set(name, str(expr), str(desc))
        self.j.component().create(T["comp"], True)
        geom = self.comp.geom().create(T["geom"], 1)
        with verify("GEOM_INTERVAL"):
            i1 = geom.create("i1", api.name("GEOM_INTERVAL"))
        coords = ["0", "Wn", "Xc", "Wn+Wi", "Ltot"]
        try:
            with verify("INT_SPECIFY_PROP"):
                i1.set(api.name("INT_SPECIFY_PROP"), api.name("INT_SPECIFY_VAL"))
            with verify("INT_COORD_PROP"):
                i1.set(api.name("INT_COORD_PROP"), coords)
        except ApiNameError as e:
            LOG.warning("%s -- trying the spec §9.2 form set('specify','coord')", e)
            i1.set("specify", "coord")
            i1.set("coord", coords)
        geom.run()
        nd, nb = int(geom.getNDomains()), int(geom.getNBoundaries())
        LOG.info("geometry: %d domains, %d points", nd, nb)
        if (nd, nb) != (4, 5):
            raise RuntimeError(f"stage 1 smoke test failed: expected 4 domains / 5 points, got {nd}/{nb}")

        f = self.base["functions"]["rect1"]
        with verify("FUNC_RECT"):
            rect = self.j.func().create("rect1", api.name("FUNC_RECT"))
        rect.set("funcname", "rect1")
        with verify("RECT_LOWER"):
            rect.set(api.name("RECT_LOWER"), f["lower"])
        with verify("RECT_UPPER"):
            rect.set(api.name("RECT_UPPER"), f["upper"])
        with verify("RECT_SMOOTH"):
            rect.set(api.name("RECT_SMOOTH"), f["smooth"])

        var = self.comp.variable().create("var1")
        var.selection().geom(T["geom"], 1)
        var.selection().all()
        for vname, (expr, desc) in self.base["variables"].items():
            var.set(vname, expr, desc)

        self._couplings()
        self.build_mesh(1)

    def _couplings(self) -> None:
        with verify("CPL_INTEGRATION"):
            cpl = self.comp.cpl()
            ia = cpl.create(T["intop_all"], api.name("CPL_INTEGRATION"))
        ia.selection().geom(T["geom"], 1)
        ia.selection().all()
        ia.set("opname", T["intop_all"])
        ii = cpl.create(T["intop_i"], api.name("CPL_INTEGRATION"))
        ii.selection().geom(T["geom"], 1)
        ii.selection().set([2, 3])
        ii.set("opname", T["intop_i"])
        for tag, pt in ((T["pt_n"], 1), (T["pt_c"], 3), (T["pt_p"], 5)):
            c = cpl.create(tag, api.name("CPL_INTEGRATION"))
            c.selection().geom(T["geom"], 0)
            c.selection().set([pt])
            c.set("opname", tag)

    # ----------------------------------------------------------------- mesh (§4.5)
    def build_mesh(self, mesh_factor: float = 1.0) -> None:
        m = self.base["mesh"]
        nd, ni, ratio = (int(round(m["n_doped"] * mesh_factor)), int(round(m["n_ihalf"] * mesh_factor)),
                         m["elemratio_ihalf"])
        mesh_list = [str(t) for t in self.comp.mesh().tags()]
        if T["mesh"] in mesh_list:
            self.comp.mesh().remove(T["mesh"])
        mesh = self.comp.mesh().create(T["mesh"])
        with verify("MESH_EDGE"):
            edg = mesh.create("edg1", api.name("MESH_EDGE"))
        edg.selection().geom(T["geom"], 1)          # 1D: Edge acts on domains (dimension 1)
        edg.selection().all()
        specs = [  # (tag, domain, kind, reverse)
            ("dis_n", 1, "fixed", False), ("dis_p", 4, "fixed", False),
            ("dis_iL", 2, "geom", False), ("dis_iR", 3, "geom", True),
        ]
        self._dists = {}
        for tag, dom, kind, rev in specs:
            with verify("MESH_DIST"):
                d = edg.create(tag, api.name("MESH_DIST"))
            d.selection().geom(T["geom"], 1)
            d.selection().set([dom])
            if kind == "fixed":
                with verify("DIST_NUMELEM"):
                    d.set(api.name("DIST_NUMELEM"), str(nd))   # str: a Python int is ambiguous (int/boolean) in JPype
            else:
                with verify("DIST_TYPE"):
                    d.set(api.name("DIST_TYPE"), api.name("DIST_PREDEFINED"))
                with verify("DIST_ELEMCOUNT"):
                    d.set(api.name("DIST_ELEMCOUNT"), str(ni))   # str: a Python int is ambiguous (int/boolean) in JPype
                with verify("DIST_ELEMRATIO"):
                    d.set(api.name("DIST_ELEMRATIO"), str(ratio))   # str: a Python int is ambiguous (int/boolean) in JPype
                with verify("DIST_GROWTH"):
                    d.set(api.name("DIST_GROWTH"), api.name("DIST_GEOMETRIC"))
                with verify("DIST_REVERSE"):
                    d.set(api.name("DIST_REVERSE"), rev)
            self._dists[tag] = d
        mesh.run()
        self.assert_mesh_grading()
        LOG.info("mesh: %d+%d+%d+%d elements (mesh_factor=%g)", nd, ni, ni, nd, mesh_factor)

    def mesh_nodes(self) -> np.ndarray:
        v = np.array(self.comp.mesh(T["mesh"]).getVertex(), dtype=float)
        return np.sort(v.reshape(-1))

    def assert_mesh_grading(self, _retry: bool = True) -> None:
        """Smallest element of each i-half must sit at its junction (spec §4.5)."""
        x = self.mesh_nodes()
        Wn, Xc, Wi = (self.param_value(s) for s in ("Wn", "Xc", "Wi"))
        h = np.diff(x)
        xm = 0.5 * (x[1:] + x[:-1])
        ok = True
        for tag, lo, hi, fine_at_lo in (("dis_iL", Wn, Xc, True), ("dis_iR", Xc, Wn + Wi, False)):
            sel = (xm > lo) & (xm < hi)
            hs, xs = h[sel], xm[sel]
            if hs.size < 2:
                raise RuntimeError(f"mesh check: no elements in ({lo}, {hi})")
            at_lo, at_hi = hs[np.argmin(xs)], hs[np.argmax(xs)]
            good = at_lo < at_hi if fine_at_lo else at_hi < at_lo
            LOG.info("mesh %s: h(junction)=%.3g m, h(centre)=%.3g m", tag,
                     at_lo if fine_at_lo else at_hi, at_hi if fine_at_lo else at_lo)
            if not good:
                ok = False
                d = self._dists[tag]
                cur = bool(d.getBoolean(api.name("DIST_REVERSE")))
                LOG.warning("mesh %s: fine end not at the junction -> flipping reverse to %s", tag, not cur)
                d.set(api.name("DIST_REVERSE"), not cur)
        if not ok:
            if not _retry:
                raise RuntimeError("mesh grading assertion failed after flipping 'reverse'")
            self.comp.mesh(T["mesh"]).run()
            self.assert_mesh_grading(_retry=False)

    # ================================================================= STAGE 2
    def stage2(self) -> None:
        """Material (library copy or §4.2 fallback); read back Eg0, Nc, Nv; log Pi_nc, Pi_pc."""
        LOG.info("== stage 2: material")
        mat = self.comp.material().create(T["mat"], "Common")
        mat.selection().all()
        use_lib = self.material_source in ("auto", "library") and SI_LIBRARY_MPH.exists()
        if self.material_source == "library" and not use_lib:
            raise FileNotFoundError(f"material_source=library but {SI_LIBRARY_MPH} is missing "
                                    "(see docs/GUI_build_steps.md, 'Si library material')")
        if use_lib:
            self._copy_library_material(mat)
            self.material_used = "library"
        else:
            self._fallback_material(mat)
            self.material_used = "fallback"
        # spec §4.2: thermal properties are always the spec parameters
        d = mat.propertyGroup("def")
        d.set("thermalconductivity", diag3("k_Si"))
        d.set("density", "rho_Si")
        d.set("heatcapacity", "Cp_Si")
        self.readback_material()

    def _fallback_material(self, mat) -> None:
        fb = self.base["material_fallback"]
        with verify("MAT_RELPERM"):
            mat.propertyGroup("def").set(api.name("MAT_RELPERM"), diag3(fb["relpermittivity"]))
        with verify("MAT_SEMI_GROUP"):
            g = mat.propertyGroup().create(api.name("MAT_SEMI_GROUP"), "Semiconductor material")
        for key, prop in (("MAT_EG0", "Eg0"), ("MAT_CHI0", "chi0"), ("MAT_NC", "Nc"),
                          ("MAT_NV", "Nv"), ("MAT_MUN", "mun"), ("MAT_MUP", "mup")):
            with verify(key):
                g.set(api.name(key), fb[prop])
        self.declare_temperature_inputs(mat)
        LOG.info("material: explicit fallback properties (spec §4.2 table)")

    def declare_temperature_inputs(self, mat) -> None:
        """Property groups whose expressions use T must declare temperature as a model input
        (GUI-generated code: propertyGroup(...).addInput("temperature")). Otherwise COMSOL 6.3 reports
        'Undefined variable T' (user's run). The semiconductor then evaluates the material at its
        own model-input temperature, the user-defined T0 (one-way coupling)."""
        added = []
        for gtag in [str(t) for t in mat.propertyGroup().tags()]:
            g = mat.propertyGroup(gtag)
            uses_T = False
            for prop in [str(p) for p in g.properties()]:
                try:
                    vals = [str(v) for v in g.getStringArray(prop)]
                except Exception:
                    try:
                        vals = [str(g.getString(prop))]
                    except Exception:
                        continue
                if any(re.search(r"\bT\b", v) for v in vals):
                    uses_T = True
                    break
            if uses_T:
                with verify("MAT_ADD_INPUT", f"property group {gtag}"):
                    g.addInput(api.name("MAT_INPUT_TEMPERATURE"))
                added.append(gtag)
        LOG.info("material: temperature declared as model input for groups: %s", ", ".join(added) or "none")

    def _copy_library_material(self, mat) -> None:
        """Copy every property group of the library Si material saved by the user in
        comsol/materials/Si_library.mph (see docs/GUI_build_steps.md)."""
        if self.client is None:
            raise RuntimeError("copying the library material needs an mph client")
        src = self.client.load(str(SI_LIBRARY_MPH))
        try:
            sm = src.java.component("comp1").material("mat1")
            for gtag in sm.propertyGroup().tags():
                gtag = str(gtag)
                sg = sm.propertyGroup(gtag)
                if gtag not in [str(t) for t in mat.propertyGroup().tags()]:
                    mat.propertyGroup().create(gtag, str(sg.label()))
                dg = mat.propertyGroup(gtag)
                for prop in sg.properties():
                    prop = str(prop)
                    try:
                        dg.set(prop, [str(s) for s in sg.getStringArray(prop)])
                    except Exception:
                        dg.set(prop, str(sg.getString(prop)))
            mat.label(str(sm.label()))
            self.declare_temperature_inputs(mat)
            LOG.info("material: copied library material '%s' (%d groups)", sm.label(),
                     len(list(sm.propertyGroup().tags())))
        finally:
            self.client.remove(src)

    def readback_material(self) -> None:
        """Read Eg0, Nc, Nv back from the material, overwrite Nc_si/Nv_si, log Pi (spec §4.2)."""
        g = self.comp.material(T["mat"]).propertyGroup(api.name("MAT_SEMI_GROUP"))
        vals = {}
        for key in ("MAT_EG0", "MAT_NC", "MAT_NV"):
            with verify(key, "while reading the material back"):
                s = str(g.getStringArray(api.name(key))[0])
            expr = re.sub(r"\bT\b", "T0", s)
            vals[key] = (s, self.param_value(expr))
        for k, (s, v) in vals.items():
            LOG.info("material readback %s = '%s' -> %.6g (SI, at T0)", api.name(k), s, v)
        self.j.param().set("Eg0_si", f"{vals['MAT_EG0'][1]:.6g}[V]", "band gap read back from material at T0")
        self.j.param().set("Nc_si", f"{vals['MAT_NC'][1]:.6g}[1/m^3]", "Nc read back from material at T0")
        self.j.param().set("Nv_si", f"{vals['MAT_NV'][1]:.6g}[1/m^3]", "Nv read back from material at T0")
        pin, pip = self.param_value("Pi_nc"), self.param_value("Pi_pc")
        LOG.info("Pi_nc = %.5f V, Pi_pc = %.5f V from the read-back Nc, Nv (the spec's ~0.079 / ~0.081 V "
                 "assume Nc = 2.86e19, Nv = 3.10e19 cm^-3; library values differ, which is intended, spec §4.2)",
                 pin, pip)
        self.Pi = (pin, pip)

    # ================================================================= STAGE 3
    def stage3(self) -> None:
        """semi interface (MB, T0 input, no BGN) + 3 analytic dopings; equilibrium solve."""
        LOG.info("== stage 3: semi interface + doping; equilibrium solve")
        with verify("PHYS_SEMI"):
            semi = self.comp.physics().create(T["semi"], api.name("PHYS_SEMI"), T["geom"])
        with verify("SEMI_AREA_PROP"):
            semi.prop(api.name("SEMI_AREA_GROUP")).set(api.name("SEMI_AREA_PROP"), "Ac")
        self.set_statistics("MB")
        try:  # optional: COMSOL 6.3 shows no reference-temperature setting on semi (CHANGES.md M15)
            with verify("SEMI_TREF_PROP"):
                semi.prop(api.name("SEMI_MODEL_GROUP")).set(api.name("SEMI_TREF_PROP"), "T0")
        except ApiNameError:
            LOG.warning("no reference-temperature setting on semi; skipped (energy reference only; "
                        "the semiconductor temperature is still the user-defined T0 in smm1)")
        smm = semi.feature(api.name("SMM_TAG"))
        self.set_user_temperature(strict=False)       # enforced again in stage 5, once ht exists
        self.set_bgn("off", strict=False)             # off and complete ionization are COMSOL's defaults
        try:
            with verify("SMM_INCION_PROP"):
                smm.set(api.name("SMM_INCION_PROP"), api.name("SMM_ION_COMPLETE"))
        except ApiNameError as e:
            LOG.warning("could not set complete ionization explicitly (COMSOL default is complete): %s",
                        str(e).splitlines()[-1])
        self.mobility_base = "M1" if self.material_used == "library" else "M2"
        if self.mobility_base == "M2":
            LOG.warning("fallback material has no Arora parameters -> base mobility = M2 "
                        "(Caughey-Thomas, spec §4.3). Recorded in the run headers; see CHANGES.md.")
        try:
            self.set_mobility(self.mobility_base, fletcher=False)
        except ApiNameError as e:
            if self.mobility_base != "M1":
                raise
            LOG.warning("could not select the Arora mobility model (M1) in smm1: %s", e)
            LOG.warning("-> continuing with mobility option M2 (Caughey-Thomas, spec §4.3). Variants that ask "
                        "for M1 run with M2; V2a/V2b (Fletcher on Arora) are skipped. See CHANGES.md M16.")
            self.mobility_base = "M2"
            self.set_mobility("M2", fletcher=False)

        for tag, dtype, x0, w, conc, profile in (
            (T["dop_bg"], "acceptor", "0", "Ltot", "N_bg", "none"),
            (T["dop_n"], "donor", "0", "Wn", "Nd_p", "gaussian"),
            (T["dop_p"], "acceptor", "Ltot-Wp", "Wp", "Na_p", "gaussian"),
        ):
            with verify("FEAT_DOPING"):
                d = semi.create(tag, api.name("FEAT_DOPING"), 1)
            d.selection().all()
            with verify("DOP_DIST"):
                d.set(api.name("DOP_DIST"), api.name("DOP_BOX"))
            with verify("DOP_TYPE"):
                d.set(api.name("DOP_TYPE"), api.name("DOP_DONOR" if dtype == "donor" else "DOP_ACCEPTOR"))
            key = "DOP_ND" if dtype == "donor" else "DOP_NA"
            with verify(key):
                d.set(api.name(key), conc)
            with verify("DOP_X0"):
                d.set(api.name("DOP_X0"), [x0, "0", "0"])   # COMSOL 6.3: rb is a 3-vector even in 1D
            with verify("DOP_W"):
                d.set(api.name("DOP_W"), w)
            # Every box uses the decay-length form. COMSOL's default ('junction depth') derives the
            # length from log(N_box/N_b) with N_b = 1e15 cm^-3, which is undefined for the 1e12 cm^-3
            # background box (COMSOL 6.3: "real square root of negative number"). The background
            # box spans the whole bar, so its drop-off profile has no effect.
            with verify("DOP_PROFILE"):
                d.set(api.name("DOP_PROFILE"), api.name("DOP_GAUSS"))
            with verify("DOP_LSCALE_SRC"):
                d.set(api.name("DOP_LSCALE_SRC"), api.name("DOP_LSCALE_LENGTH"))
            with verify("DOP_LSCALE"):
                d.set(api.name("DOP_LSCALE"), "l_dec")

        std = self.j.study().create(T["std_eq_iv"])
        std.label("Study 1: I-V and heat-source map")
        with verify("STUDY_EQ"):
            eq = std.create("sseq", api.name("STUDY_EQ"))
        self.set_activate(eq, semi=True, ht=None)
        self.solve(T["std_eq_iv"])
        self.probe_names(T["std_eq_iv"], ["NDOP"])
        ndop = self.eval_field(self.var("NDOP"), T["std_eq_iv"])[-1]
        Nd, Na = self.param_value("Nd_p"), self.param_value("Na_p")
        LOG.info("net doping range: %.3g .. %.3g 1/m^3", ndop.min(), ndop.max())
        if not (abs(ndop.max() / Nd - 1) < 0.05 and abs(-ndop.min() / Na - 1) < 0.05):
            raise RuntimeError("stage 3 smoke test failed: net doping not within -1e19..+1e19 cm^-3 (+-5%)")
        # positions: centre of n+, centre of the bar, centre of p+ (checks box base/width names)
        x = self.eval_field("x", T["std_eq_iv"])[-1]
        o = np.argsort(x)
        Wn, Xc, Lt, Wp, Nbg = (self.param_value(n) for n in ("Wn", "Xc", "Ltot", "Wp", "N_bg"))
        at = lambda xx: float(np.interp(xx, x[o], ndop[o]))  # noqa: E731
        checks = [(Wn / 2, Nd), (Xc, -Nbg), (Lt - Wp / 2, -Na)]
        LOG.info("net doping at n+ centre / bar centre / p+ centre: %.3g / %.3g / %.3g 1/m^3",
                 *(at(xx) for xx, _ in checks))
        for xx, want in checks:
            if abs(at(xx) / want - 1) > 0.05:
                raise RuntimeError(f"stage 3 smoke test failed: net doping at x = {xx:.4g} m is {at(xx):.3g} "
                                   f"1/m^3, expected {want:.3g} (check DOP_X0 = '{api.name('DOP_X0')}', "
                                   f"DOP_W = '{api.name('DOP_W')}')")

    # ----------------------------------------------------------------- semi switches (variants)
    def set_statistics(self, stats: str) -> None:
        with verify("SEMI_STATS_PROP"):
            self.semi.prop(api.name("SEMI_MODEL_GROUP")).set(
                api.name("SEMI_STATS_PROP"), api.name("SEMI_STATS_MB" if stats == "MB" else "SEMI_STATS_FD"))

    def set_user_temperature(self, strict: bool = True) -> None:
        """One-way coupling: semi temperature = user-defined T0, never ht.T (spec §0 rule 3).
        Without ht, COMSOL offers only 'User defined' and may not have the source selector, so
        stage 3 tolerates a rejection; stage 5 (ht present) does not."""
        smm = self.semi.feature(api.name("SMM_TAG"))
        try:
            with verify("SMM_TEMP_SRC", "one-way coupling: the semiconductor temperature must be the "
                        "user-defined T0. Open stage4.mph, add Heat Transfer in Solids, then check "
                        "Semiconductor Material Model 1 > Model Input > Temperature."):
                smm.set(api.name("SMM_TEMP_SRC"), "userdef")
        except ApiNameError:
            if strict:
                raise
            LOG.info("temperature source selector not offered yet (no ht); default is user defined")
        with verify("SMM_TEMP"):
            smm.set(api.name("SMM_TEMP"), "T0")

    def set_bgn(self, bgn: str, strict: bool = True) -> None:
        smm = self.semi.feature(api.name("SMM_TAG"))
        try:
            with verify("SMM_BGN_PROP" if bgn == "slotboom" else "SMM_BGN_OFF"):
                smm.set(api.name("SMM_BGN_PROP"),
                        api.name("SMM_BGN_SLOTBOOM" if bgn == "slotboom" else "SMM_BGN_OFF"))
        except ApiNameError as e:
            if strict:
                raise
            LOG.warning("band-gap narrowing 'off' not set explicitly (COMSOL default is off). If COMSOL "
                        "listed allowed values, put the 'off' one into SMM_BGN_OFF: %s", e)

    def set_mobility(self, mode: str, fletcher: bool) -> None:
        """M1 = Arora (library parameters), M2 = user-defined Caughey-Thomas; optional Fletcher."""
        smm = self.semi.feature(api.name("SMM_TAG"))
        existing = [str(t) for t in smm.feature().tags()]
        if mode == "M1":
            if self.material_used != "library":
                raise RuntimeError("mobility M1 (Arora, library parameters) needs the library material; "
                                   f"provide {SI_LIBRARY_MPH} (docs/GUI_build_steps.md)")
            if T["mob_arora"] not in existing:
                with verify("FEAT_MOB_ARORA"):
                    smm.create(T["mob_arora"], api.name("FEAT_MOB_ARORA"), 1)
            if fletcher:
                if T["mob_fletcher"] not in existing:
                    with verify("FEAT_MOB_FLETCHER"):
                        f = smm.create(T["mob_fletcher"], api.name("FEAT_MOB_FLETCHER"), 1)
                else:
                    f = smm.feature(T["mob_fletcher"])
                with verify("MOB_INPUT_N"):
                    f.set(api.name("MOB_INPUT_N"), api.name("MOB_ARORA_N"))
                with verify("MOB_INPUT_P"):
                    f.set(api.name("MOB_INPUT_P"), api.name("MOB_ARORA_P"))
                sel_n, sel_p = api.name("MOB_FLETCHER_N"), api.name("MOB_FLETCHER_P")
            else:
                sel_n, sel_p = api.name("MOB_ARORA_N"), api.name("MOB_ARORA_P")
                if T["mob_fletcher"] in existing:
                    smm.feature(T["mob_fletcher"]).active(False)
            smm.feature(T["mob_arora"]).active(True)
            if "var_m2" in [str(t) for t in self.comp.variable().tags()]:
                self.comp.variable("var_m2").active(False)
            with verify("SMM_MUN_SEL"):
                smm.set(api.name("SMM_MUN_SEL"), sel_n)
            with verify("SMM_MUP_SEL"):
                smm.set(api.name("SMM_MUP_SEL"), sel_p)
        else:
            if fletcher:
                raise RuntimeError("Fletcher add-on is defined on top of Arora (M1) only")
            for tag in (T["mob_arora"], T["mob_fletcher"]):
                if tag in existing:
                    smm.feature(tag).active(False)
            self.define_m2_variables()
            self.set_userdef(smm, api.name("SMM_MUN_USER"), "mun_CT", "SMM_MUN_USER")
            self.set_userdef(smm, api.name("SMM_MUP_USER"), "mup_CT", "SMM_MUP_USER")

    def define_recombination_variable(self) -> None:
        """U_x: total net recombination rate written out explicitly (COMSOL 6.3 offers no variable
        found under the names tried). Exact for this model: SRH with tau_n = tau_p = tau_x and a
        midgap trap, R = (np - ni^2)/(tau_x (n + p + 2 ni)), plus Auger (Cn n + Cp p)(np - ni^2) when
        Auger is included. Without band-gap narrowing ni = sqrt(Nc Nv) exp(-Eg/(2 kT/q))."""
        n, p = api.name("N_E"), api.name("P_H")
        var = self.comp.variable().create("var_rec")
        var.selection().geom(T["geom"], 1)
        var.selection().all()
        var.set("ni_x", "sqrt(semi.Nc*semi.Nv)*exp(-Eg0_si/(2*k_B_const*T0/e_const))",
                "intrinsic density (no BGN), for U_x")
        u = f"({n}*{p}-ni_x^2)/(tau_x*({n}+{p}+2*ni_x))"
        if getattr(self, "auger", False):
            u += f"+(Cn_aug*{n}+Cp_aug*{p})*({n}*{p}-ni_x^2)"
        var.set("U_x", u, "total net recombination rate (SRH" + (" + Auger)" if self.auger else ")"))
        LOG.info("U_x = %s", u)

    def define_m2_variables(self) -> None:
        """mun_CT, mup_CT (option M2) in their own Variables node, created only when M2 is used:
        COMSOL checks every defined variable at solve time, so unused ones must not exist."""
        from write_params_txt import caughey_thomas_expr
        if "var_m2" not in [str(t) for t in self.comp.variable().tags()]:
            var = self.comp.variable().create("var_m2")
            var.selection().geom(T["geom"], 1)
            var.selection().all()
            for carrier, vname in (("electrons", "mun_CT"), ("holes", "mup_CT")):
                var.set(vname, caughey_thomas_expr(carrier, self.base),
                        f"Caughey-Thomas mobility ({carrier}), option M2")
        self.comp.variable("var_m2").active(True)

    def add_auger(self) -> bool:
        """Auger recombination (Cn_aug, Cp_aug). COMSOL 6.3 rejected the type 'AugerRecombination'
        (api_dump), so candidate types are tried; if none works the build continues WITHOUT Auger,
        loudly logged and recorded in build_info.json (CHANGES.md M17)."""
        item = api.VERIFY["FEAT_AUGER"]
        errors = []
        for ftype in [item.value] + [c for c in item.candidates if c != item.value]:
            try:
                aug = self.semi.create(T["auger"], ftype, 1)
            except Exception as exc:
                errors.append(f"{ftype}: {' '.join(str(exc).split())[:300]}")
                continue
            try:
                aug.selection().all()
                self.set_userdef(aug, api.name("AUG_CN"), "Cn_aug", "AUG_CN")
                self.set_userdef(aug, api.name("AUG_CP"), "Cp_aug", "AUG_CP")
            except ApiNameError as exc:
                self.semi.feature().remove(T["auger"])
                errors.append(f"{ftype}: created, but coefficients rejected: {' '.join(str(exc).split())[:300]}")
                break
            LOG.info("Auger recombination added (type '%s')", ftype)
            item.value = ftype
            return True
        LOG.warning("!! AUGER RECOMBINATION NOT INCLUDED -- COMSOL rejected every attempt:\n   %s",
                    "\n   ".join(errors))
        LOG.warning("!! Continuing with SRH only. Auger matters mainly above VF ~ 0.75 V. Please send these "
                    "lines to the script maintainer (CHANGES.md M17).")
        return False

    def set_first(self, feat, key: str, value) -> str:
        """Set `value` on the first property name of api key `key` that COMSOL accepts
        (its value, then its candidates). Remembers the working name; ApiNameError if none."""
        item = api.VERIFY[key]
        names = [item.value] + [c for c in item.candidates if c != item.value]
        errors = []
        for n in names:
            try:
                feat.set(n, value)
            except Exception as exc:
                errors.append(f"{n}: {str(exc).splitlines()[0] if str(exc) else exc}")
                continue
            if n != item.value:
                LOG.warning("API name %s: '%s' rejected, '%s' works", key, item.value, n)
                item.value = n
            return n
        raise ApiNameError(key, extra="none of " + ", ".join(names) + " accepted: " + " | ".join(errors))

    # ================================================================= STAGE 4
    def stage4(self) -> None:
        """SRH + Auger, ohmic contacts, Study 1 semi-only sweep; probe variable names."""
        LOG.info("== stage 4: recombination, contacts, Study 1 (semi only)")
        semi = self.semi
        with verify("FEAT_SRH"):
            srh = semi.create(T["srh"], api.name("FEAT_SRH"), 1)
        srh.selection().all()
        self.set_userdef(srh, api.name("SRH_TAUN"), "tau_x", "SRH_TAUN")
        self.set_userdef(srh, api.name("SRH_TAUP"), "tau_x", "SRH_TAUP")
        try:
            self.set_userdef(srh, api.name("SRH_ET"), "0[V]", "SRH_ET")
        except ApiNameError as e:
            LOG.warning("trap level not set explicitly (COMSOL default is midgap): %s", e)
        self.auger = self.add_auger()
        self.define_recombination_variable()
        for tag, pt, v in ((T["mc_n"], 1, "0[V]"), (T["mc_p"], 5, "VF")):
            with verify("FEAT_CONTACT"):
                mc = semi.create(tag, api.name("FEAT_CONTACT"), 0)
            mc.selection().set([pt])
            with verify("MC_TERMTYPE"):
                mc.set(api.name("MC_TERMTYPE"), api.name("MC_VOLTAGE"))
            with verify("MC_V0"):
                mc.set(api.name("MC_V0"), v)

        std = self.j.study(T["std_eq_iv"])
        with verify("STUDY_STAT"):
            st = std.create("stat", api.name("STUDY_STAT"))
        self.set_activate(st, semi=True, ht=None)
        self.set_aux_sweep(st, self.base["sweeps"]["VF_iv"])
        self.solve(T["std_eq_iv"])
        self.probe_names(T["std_eq_iv"])
        VF = self.vf_values(T["std_eq_iv"])
        I = np.abs(self.eval_global(self.var("I_TERMINAL"), T["std_eq_iv"]))
        Ac = self.param_value("Ac")
        J = I / Ac
        JX = np.abs(self.eval_global(f"pt_p({self.var('J_X')})", T["std_eq_iv"]))
        sel = VF > 0.3
        r = I[sel] / (Ac * JX[sel])
        LOG.info("consistency |I_TERMINAL| / (Ac*|J_X|) = %.4g .. %.4g", r.min(), r.max())
        if np.any(np.abs(r - 1) > 0.05):
            alt = api.COMPUTED_FALLBACKS["I_TERMINAL"].format(J_X=self.var("J_X"))
            LOG.warning("terminal current '%s' is not Ac*|J_X| (per-area value or another terminal); "
                        "using I = %s instead", self.var("I_TERMINAL"), alt)
            self.names["I_TERMINAL"] = alt
            I = np.abs(self.eval_global(alt, T["std_eq_iv"]))
            J = I / Ac
        # plausibility (spec §9 stage 4): reported, not fatal
        if np.any(np.diff(I[VF > 0.05]) <= 0):
            LOG.warning("stage 4 check: I-V is not monotonic above 0.05 V -- inspect stage4.mph")
        J07 = float(np.interp(0.7, VF, J)) * 1e-4
        LOG.info("J(0.7 V) = %.4f A/cm^2 (spec V0 window 0.02-1; reference model 0.056)", J07)
        if not 0.02 <= J07 <= 1.0:
            LOG.warning("stage 4 check: J(0.7 V) = %.4g A/cm^2 is outside the spec window 0.02-1 A/cm^2", J07)

    def probe_names(self, study: str, keys: list[str] | None = None) -> None:
        """Pick, for each variable constant, the first candidate COMSOL can evaluate (the last
        candidates are formulas built from confirmed names). Optional variables may stay unresolved.
        TFLUX_X is probed after stage 5 (needs ht)."""
        for key, item in api.VERIFY.items():
            if item.kind != "variable" or (keys is not None and key not in keys):
                continue
            if keys is None and key in ("TFLUX_X", "NDOP"):
                continue
            cands = list(item.candidates or [item.value])
            if key in api.COMPUTED_FALLBACKS and self.names.get("J_X"):
                cands.append(api.COMPUTED_FALLBACKS[key].format(J_X=self.names["J_X"]))
            ok, errors = None, []
            for cand in cands:
                expr = cand if key == "I_TERMINAL" else f"pt_c({cand})"
                try:
                    self.eval_global(expr, study)
                    ok = cand
                    break
                except SweepReadError:
                    raise                     # not a naming problem: report it as it is
                except Exception as exc:
                    errors.append(f"{cand}: {' '.join(str(exc).split())[:160]}")
            if ok is None:
                if key in api.OPTIONAL_VARIABLES:
                    LOG.warning("optional variable %s not available (tried %s); dependent outputs are skipped",
                                key, ", ".join(cands))
                    self.names[key] = None
                    continue
                raise ApiNameError(key, extra="none of the candidates evaluates:\n    " + "\n    ".join(errors))
            self.names[key] = ok
            if ok != item.value:
                LOG.warning("API name %s: '%s' not found, using '%s'", key, item.value, ok)
            else:
                LOG.info("API name %s = %s (verified by evaluation)", key, ok)
        for key in ("NC_VAR", "NV_VAR"):
            if self.names.get(key):
                v = float(np.atleast_1d(self.eval_global(f"pt_c({self.names[key]})", study))[0])
                LOG.info("semi readback %s = %.4g 1/m^3", self.names[key], v)

    # ================================================================= STAGE 5
    def stage5(self) -> None:
        """ht interface, hs1 = semi.Q_tot, contact Peltier sinks, Config B sink; T(VF=0) = T_room."""
        LOG.info("== stage 5: ht interface, heat sources, Config B nodes")
        with verify("PHYS_HT"):
            ht = self.comp.physics().create(T["ht"], api.name("PHYS_HT"), T["geom"])
        with verify("HT_AREA_PROP"):
            ht.prop(api.name("HT_AREA_GROUP")).set(api.name("HT_AREA_PROP"), "Ac")
        with verify("HT_BFLUX_PROP"):
            ht.prop(api.name("HT_BFLUX_GROUP")).set(api.name("HT_BFLUX_PROP"), True)
        with verify("HT_INIT_T"):
            ht.feature(api.name("HT_INIT_TAG")).set(api.name("HT_INIT_T"), "T_room")
        self.set_user_temperature(strict=True)        # ht now exists: never let semi use ht.T
        with verify("FEAT_HS"):
            hs = ht.create(T["hs1"], api.name("FEAT_HS"), 1)
        hs.selection().all()
        self.set_heat_source("builtin")
        jx = self.var("J_X")
        for tag, pt, pi in ((T["bhs_n"], 1, "Pi_nc"), (T["bhs_p"], 5, "Pi_pc")):
            with verify("FEAT_BHS"):
                b = ht.create(tag, api.name("FEAT_BHS"), 0)
            b.selection().set([pt])
            with verify("BHS_QB"):
                b.set(api.name("BHS_QB"), f"-abs({jx})*{pi}")
        self._temp_node(T["temp_sinkB"], [3], "T_room")
        st = self.j.study(T["std_eq_iv"]).feature("stat")
        self.set_activate(st, semi=True, ht=True)
        self.set_activate(self.j.study(T["std_eq_iv"]).feature("sseq"), semi=True, ht=False)
        self.solve(T["std_eq_iv"])
        self.probe_names(T["std_eq_iv"], ["TFLUX_X"])
        Tf = self.eval_field("T", T["std_eq_iv"])
        dT0 = float(np.max(np.abs(Tf[0] - self.param_value("T_room"))))
        LOG.info("max|T(VF=0) - T_room| = %.3g K", dT0)
        if dT0 > 1e-6:
            LOG.warning("stage 5 check: T(VF=0) deviates from T_room by %.3g K (expected < 1 uK); "
                        "check C1 in the report", dT0)

    def _temp_node(self, tag: str, points: list[int], value: str):
        with verify("FEAT_TEMP"):
            t = self.ht.create(tag, api.name("FEAT_TEMP"), 0)
        t.selection().set(points)
        with verify("TEMP_T0"):
            t.set(api.name("TEMP_T0"), value)
        return t

    def heat_source_expr(self, qsrc: str) -> str:
        q = self.var("Q_TOT")
        if qsrc == "builtin":
            return q
        if not self.var("U_TOT"):
            raise RuntimeError("qsrc=corrected needs the total recombination rate (U_TOT), which is not "
                               "available in this COMSOL version; corrected-source variants are skipped")
        return f"{q}+k_B_const*T0*{self.var('U_TOT')}"

    def set_heat_source(self, qsrc: str) -> None:
        self.hs_expr = self.heat_source_expr(qsrc)
        with verify("HS_Q0"):
            self.ht.feature(T["hs1"]).set(api.name("HS_Q0"), self.hs_expr)
        LOG.info("hs1 Q0 = %s (qsrc=%s)", self.hs_expr, qsrc)

    # ================================================================= STAGE 6
    def stage6(self) -> None:
        """Config A/C nodes, Studies 2-4, 'modify model configuration' toggles."""
        LOG.info("== stage 6: Config A/C nodes, Studies 2-4, model-configuration toggles")
        self._temp_node(T["temp_ends"], [1, 5], "T_room")
        self._temp_node(T["temp_sinkA"], [3], "T_room+dT_sink")
        hl = self.ht.create(T["hs_lat"], api.name("FEAT_HS"), 1)
        hl.selection().set([2, 3])
        hl.set(api.name("HS_Q0"), "-h_lat*Plat_over_A*(T-T_out)*lat_mask")

        # Study 1 runs Config A at dT_sink = 0 (qx_0, qx_L, Q_room); see CHANGES.md
        self.set_config(self.j.study(T["std_eq_iv"]).feature("stat"), "A")
        self.set_config(self.j.study(T["std_eq_iv"]).feature("sseq"), "A")

        for tag, label, cfg, vf in ((T["std_room"], "Study 2: Config A, dT_max search", "A", "VF_room"),
                                    (T["std_float"], "Study 3: Config B", "B", "VF_iv"),
                                    (T["std_lat"], "Study 4: Config C (lateral sink)", "C", "VF_iv")):
            std = self.j.study().create(tag)
            std.label(label)
            st = std.create("stat", api.name("STUDY_STAT"))
            self.set_activate(st, semi=True, ht=True)
            self.set_aux_sweep(st, self.base["sweeps"][vf])
            self.set_config(st, cfg)
            if tag == T["std_room"]:
                with verify("STUDY_PARAM"):
                    ps = std.create("param", api.name("STUDY_PARAM"))
                ps.set("pname", ["dT_sink"])
                ps.set("plistarr", [self.base["sweeps"]["dT_sink"]])
                ps.set("punit", ["K"])
            std.createAutoSequences("all")
            self.set_solver_tolerance(tag)

    def set_config(self, step, cfg: str) -> None:
        """'Modify model configuration for study step': disable thermal nodes of other configs."""
        disabled = [f"{T['ht']}/{T[n]}" for n in ALL_THERMAL_NODES if n not in CONFIG_NODES[cfg]]
        with verify("STEP_USEDISABLE"):
            step.set(api.name("STEP_USEDISABLE"), True)
        with verify("STEP_DISABLED"):
            step.set(api.name("STEP_DISABLED"), disabled)

    def set_activate(self, step, semi: bool, ht: bool | None) -> None:
        act = [T["semi"], "on" if semi else "off"]
        if ht is not None:
            act += [T["ht"], "on" if ht else "off"]
        with verify("STEP_ACTIVATE"):
            step.set(api.name("STEP_ACTIVATE"), act)

    def set_aux_sweep(self, step, plist: str) -> None:
        step.set("useparam", True)
        step.set("pname", ["VF"])
        step.set("plistarr", [plist])
        step.set("punit", ["V"])
        try:
            with verify("STEP_CONTINUATION"):
                step.set(api.name("STEP_CONTINUATION"), api.name("STEP_CONT_MANUAL"))
            with verify("STEP_CONT_PARAM"):
                step.set(api.name("STEP_CONT_PARAM"), "VF")
        except ApiNameError as e:
            LOG.warning("could not set continuation explicitly (COMSOL default is continuation ON "
                        "for a single auxiliary parameter): %s", e)

    # ================================================================= STAGE 7 / 8
    def stage7(self) -> None:
        """Export routines: smoke export of the base model to results/_smoke/."""
        LOG.info("== stage 7: export routines (smoke export of the base model)")
        from run_variants import export_variant  # noqa: WPS433 (avoid import cycle at module load)
        export_variant(self, {"id": "_stage7_smoke", "params": {}, "configs": ["A", "B"], "qsrc": "builtin",
                              "stats": "MB", "bgn": "off", "mobility": self.mobility_base, "fletcher": False},
                       out_root=ROOT / "results" / "_smoke", solve=True, reverse=False)

    def stage8(self) -> Path:
        """Variant-driver hooks (apply/revert a variant); save pin_peltier_base.mph."""
        LOG.info("== stage 8: variant-driver hooks; saving base model")
        from run_variants import apply_variant
        qsrc = "corrected" if self.var("U_TOT") else "builtin"
        apply_variant(self, {"params": {"rz_on": "1"}, "qsrc": qsrc, "stats": "MB", "bgn": "off",
                             "mobility": self.mobility_base, "fletcher": False})
        if qsrc == "corrected" and not self.hs_expr.endswith(self.var("U_TOT")):
            raise RuntimeError("stage 8 check: qsrc switch failed")
        apply_variant(self, {"params": {"rz_on": "0"}, "qsrc": "builtin", "stats": "MB", "bgn": "off",
                             "mobility": self.mobility_base, "fletcher": False})
        self.j.param().set("dT_sink", "0[K]")
        self.write_build_info()
        return self.save("pin_peltier_base.mph")

    def write_build_info(self) -> None:
        import json
        info = dict(material=self.material_used, mobility_base=self.mobility_base, names=self.names,
                    auger=getattr(self, "auger", None),
                    hs_expr=self.hs_expr, Pi=getattr(self, "Pi", None))
        self.stage_dir.mkdir(parents=True, exist_ok=True)
        (self.stage_dir / "build_info.json").write_text(json.dumps(info, indent=1), encoding="utf-8")

    # ================================================================= solving / evaluation
    def set_solver_tolerance(self, study: str) -> None:
        for sol in self.solutions_of(study):
            s = self.j.sol(sol)
            for ftag in s.feature().tags():
                if str(s.feature(ftag).getType()) == "Stationary":
                    with verify("SOLVER_STOL"):
                        s.feature(ftag).set(api.name("SOLVER_STOL"), str(self.base["sweeps"]["rtol"]))

    def solutions_of(self, study: str) -> list[str]:
        out = []
        for t in self.j.sol().tags():
            try:
                if str(self.j.sol(t).study()) == study:
                    out.append(str(t))
            except Exception:
                continue
        return out

    def main_solution(self, study: str, parametric: bool = False) -> str:
        """The solution object holding a study's results. A study with an equilibrium step also owns a
        'Solution Store' (target of a StoreSolution feature) that holds only the equilibrium point;
        COMSOL 6.3 lists it under the same study, so it must be skipped (user's run)."""
        sols = self.solutions_of(study)
        stored, solver_sols = set(), set()
        for sname in sols:
            so = self.j.sol(sname)
            for f in [str(t) for t in so.feature().tags()]:
                try:
                    ftype = str(so.feature(f).getType())
                except Exception:
                    continue
                if ftype == "StoreSolution":
                    try:
                        stored.add(str(so.feature(f).getString("sol")))
                    except Exception:
                        pass
                if ftype == "Stationary":
                    solver_sols.add(sname)
        cands = [x for x in sols if x not in stored
                 and ("Parametric" in str(self.j.sol(x).label())) == parametric
                 and (parametric or x in solver_sols)]
        if not cands:
            raise RuntimeError(f"no {'parametric ' if parametric else ''}solution found for study {study} "
                               f"(solutions {sols}, stored {sorted(stored)})")
        return cands[0]

    def dataset_of(self, study: str, parametric: bool = False) -> str:
        """Dataset tag of the study's main solution (created if COMSOL made none)."""
        sol = self.main_solution(study, parametric)
        for d in self.j.result().dataset().tags():
            try:
                if str(self.j.result().dataset(d).getString("solution")) == sol:
                    return str(d)
            except Exception:
                continue
        tag = f"dset_{study}{'_p' if parametric else ''}"
        ds = self.j.result().dataset().create(tag, "Solution")
        ds.set("solution", sol)
        LOG.info("created dataset %s for %s", tag, sol)
        return tag

    def vf_values(self, study: str) -> np.ndarray:
        """VF of every inner solution; checked against the study's sweep list."""
        VF = self.eval_global("VF", study, unit="V")
        st = self.j.study(study).feature("stat") if "stat" in [str(t) for t in self.j.study(study).feature().tags()] else None
        if st is not None and st.getBoolean("useparam"):
            m = re.fullmatch(r"\s*range\(([^,]+),([^,]+),([^,]+)\)\s*", str(st.getStringArray("plistarr")[0]))
            if m:
                expected = parse_range(str(st.getStringArray("plistarr")[0]))
                if VF.size != expected.size or not np.allclose(VF, expected, atol=1e-9):
                    raise RuntimeError(f"{study}: read {VF.size} VF values ({VF[:3]}...), expected the sweep "
                                       f"{expected[0]}..{expected[-1]} ({expected.size} points) -- wrong dataset?")
        return VF

    def solve(self, study: str, plist: str | None = None) -> None:
        """Run a study; on failure apply the spec §4.6 fallback (segregated, then half VF step)."""
        std = self.j.study(study)
        self.__dict__.setdefault("_readers", {}).clear()   # datasets may change with a new solution
        self.reset_solver(study)
        self.set_solver_tolerance(study)
        t0 = time.time()
        try:
            std.run()
            LOG.info("solved %s in %.1f s", study, time.time() - t0)
            return
        except Exception as exc:
            first_error = full_message(exc)
            LOG.warning("%s failed. COMSOL said:\n%s", study, first_error)
        if self.make_segregated(study):
            LOG.warning("%s -> fallback 1: segregated solver", study)
            try:
                std.run()
                LOG.info("solved %s with segregated solver in %.1f s", study, time.time() - t0)
                return
            except Exception as exc:
                LOG.warning("%s failed again. COMSOL said:\n%s", study, full_message(exc))
        st = std.feature("stat") if "stat" in [str(t) for t in std.feature().tags()] else None
        if st is None or not st.getBoolean("useparam"):
            raise RuntimeError(f"{study} did not solve and no fallback applies. COMSOL said:\n{first_error}")
        LOG.warning("%s -> fallback 2: halve the VF step", study)
        a, d, b = re.fullmatch(r"\s*range\(([^,]+),([^,]+),([^,]+)\)\s*",
                               str(st.getStringArray("plistarr")[0])).groups()
        st.set("plistarr", [f"range({a},{float(d)/2:g},{b})"])
        self.reset_solver(study)
        self.set_solver_tolerance(study)
        self.make_segregated(study)
        std.run()
        LOG.info("solved %s with half VF step", study)

    def reset_solver(self, study: str) -> None:
        """Delete the study's old solver sequences, then let COMSOL generate fresh ones. In COMSOL 6.3,
        createAutoSequences kept the equilibrium-only sequence from stage 3 after the sweep step was
        added in stage 4, so the VF sweep never ran (user's run: one solution, VF = 0.7)."""
        for sol in self.solutions_of(study):
            try:
                self.j.sol().remove(sol)
            except Exception as exc:
                LOG.warning("could not remove old solution %s: %s", sol, " ".join(str(exc).split())[:120])
        self.j.study(study).createAutoSequences("all")

    def describe_solutions(self, study: str) -> str:
        """Solver-sequence structure of a study, for diagnostics."""
        lines = []
        for sol in self.solutions_of(study):
            so = self.j.sol(sol)
            feats = []
            for f in [str(t) for t in so.feature().tags()]:
                try:
                    kids = ",".join(f"{c}:{so.feature(f).feature(c).getType()}" for c in
                                    [str(t) for t in so.feature(f).feature().tags()])
                    feats.append(f"{f}:{so.feature(f).getType()}" + (f"[{kids}]" if kids else ""))
                except Exception:
                    feats.append(f)
            lines.append(f"{sol} '{so.label()}': " + " ".join(feats))
        return "\n    ".join(lines) or "(no solutions)"

    def solver_fields(self, sol: str) -> set[str]:
        """Dependent-variable field tags of a solver sequence (children of its Variables nodes)."""
        out = set()
        s = self.j.sol(sol)
        for ftag in s.feature().tags():
            f = s.feature(ftag)
            if str(f.getType()) == "Variables":
                out |= {str(t) for t in f.feature().tags()}
        return out

    def make_segregated(self, study: str) -> bool:
        """Segregated solver (semi | T). Returns False when it cannot apply (no T solved for)."""
        semi_vars = api.name("DEPVARS_SEMI").split(",")
        applied = False
        for sol in self.solutions_of(study):
            if api.name("DEPVAR_T") not in self.solver_fields(sol):
                LOG.info("segregated fallback not applicable to %s (no temperature variable)", study)
                continue
            s = self.j.sol(sol)
            for ftag in s.feature().tags():
                f = s.feature(ftag)
                if str(f.getType()) != "Stationary":
                    continue
                applied = True
                tags = [str(t) for t in f.feature().tags()]
                if "se1" in tags:
                    # COMSOL 6.3 generates a segregated solver (se1: ss1, ss2, ...) for semi + ht
                    # by default (api_dump); use its own variable groups.
                    se = f.feature("se1")
                    for t in tags:
                        if t.startswith("fc"):
                            f.feature(t).active(False)
                    se.active(True)
                    continue
                with verify("SOLVER_SEGREGATED"):
                    se = f.create("se1", api.name("SOLVER_SEGREGATED"))
                kids = [str(t) for t in se.feature().tags()]
                with verify("SEG_DEFAULT_STEP"):
                    ss1 = se.feature(api.name("SEG_DEFAULT_STEP") if api.name("SEG_DEFAULT_STEP") in kids else kids[0])
                with verify("SEG_VARS"):
                    ss1.set(api.name("SEG_VARS"), semi_vars)
                if "ss_T" not in [str(t) for t in se.feature().tags()]:
                    with verify("SEG_STEP"):
                        ss = se.create("ss_T", api.name("SEG_STEP"))
                    with verify("SEG_VARS"):
                        ss.set(api.name("SEG_VARS"), [api.name("DEPVAR_T")])
                for t in tags:
                    if t.startswith("fc"):
                        f.feature(t).active(False)
                se.active(True)
        return applied

    _eval_count = 0
    # Ways of asking a Numerical feature for *all* sweep steps; which one COMSOL 6.3 needs is found
    # at run time by checking that the VF list comes back complete (_reader).
    READ_MODES = {
        "default": {},
        "inner_all": {"innerinput": "all"},
        "looplevel_all": {"looplevelinput": ["all"]},
        "solnum_all": {"solnum": "all"},
    }

    def _numerical(self, ftype: str, dset: str, exprs: list[str], units, mode: str = "default", outer=None):
        """Evaluate through a temporary COMSOL Numerical feature on a dataset *tag*.
        EvalGlobal -> computeResult()[0]; Eval -> getData() [expr][inner][point]."""
        PinPeltierBuilder._eval_count += 1
        tag = f"pp_ev{PinPeltierBuilder._eval_count}"
        num = self.j.result().numerical()
        ev = num.create(tag, ftype)
        try:
            ev.set("data", dset)
            ev.set("expr", list(exprs))
            if units:
                ev.set("unit", list(units))
            if outer is not None:
                ev.set("outersolnum", _jint(outer))
            for k, v in self.READ_MODES[mode].items():
                ev.set(k, v)            # may raise: that mode is then not available
            if ftype == "EvalGlobal":
                return np.array(ev.computeResult()[0], dtype=float)
            return np.array(ev.getData(), dtype=float)
        finally:
            num.remove(tag)

    @staticmethod
    def _one_row(r) -> np.ndarray:
        r = np.atleast_2d(np.asarray(r, dtype=float))
        # one expression: [inner][expr] or [expr][inner]; both reduce to one row
        return r[0] if r.shape[0] == 1 else r[:, 0]

    def expected_vf(self, study: str):
        tags = [str(t) for t in self.j.study(study).feature().tags()]
        if "stat" not in tags:
            return None
        st = self.j.study(study).feature("stat")
        if not st.getBoolean("useparam"):
            return None
        return parse_range(str(st.getStringArray("plistarr")[0]))

    def _reader(self, study: str, parametric: bool = False):
        """(dataset tag, read mode, kind) that returns every sweep step of `study`; cached per solve."""
        key = (study, parametric)
        cache = self.__dict__.setdefault("_readers", {})
        if key in cache:
            return cache[key]
        expected = self.expected_vf(study)
        dsets = [self.dataset_of(study, parametric)]
        sols = set(self.solutions_of(study))
        for d in [str(t) for t in self.j.result().dataset().tags()]:
            try:
                if str(self.j.result().dataset(d).getString("solution")) in sols and d not in dsets:
                    dsets.append(d)
            except Exception:
                continue
        outer = 1 if parametric else None
        tried = []
        for dset in dsets:
            for kind in ("global", "field"):
                for mode in self.READ_MODES:
                    try:
                        if kind == "global":
                            VF = self._one_row(self._numerical("EvalGlobal", dset, ["VF"], None, mode, outer))
                        else:
                            VF = np.atleast_2d(self._numerical("Eval", dset, ["VF+0*x"], None, mode, outer)[0])[:, 0]
                    except Exception as exc:
                        tried.append(f"{dset}/{kind}/{mode}: error {' '.join(str(exc).split())[:80]}")
                        continue
                    ok = (VF.size >= 1 if expected is None else
                          VF.size == expected.size and np.allclose(VF, expected, atol=1e-9))
                    tried.append(f"{dset}/{kind}/{mode}: {VF.size} values {np.round(VF[:3], 4).tolist()}")
                    if ok:
                        cache[key] = (dset, mode, kind)
                        if (dset, mode, kind) != (dsets[0], "default", "global"):
                            LOG.info("reading %s results from dataset %s with %s/%s", study, dset, kind, mode)
                        return cache[key]
        raise SweepReadError(f"cannot read the complete VF sweep of {study} "
                             f"(expected {expected.size if expected is not None else 1} values). Tried:\n    "
                             + "\n    ".join(tried) + "\n  Solver sequences:\n    " + self.describe_solutions(study))

    def eval_global(self, expr: str, study: str, unit: str | None = None, parametric: bool = False,
                    outer: int | None = None) -> np.ndarray:
        """Global expression, one value per inner solution (aux-sweep step)."""
        dset, mode, kind = self._reader(study, parametric)
        outer = outer if outer is not None else (1 if parametric else None)

        def read(u):
            if kind == "global":
                return self._one_row(self._numerical("EvalGlobal", dset, [expr], [u] if u else None, mode, outer))
            data = self._numerical("Eval", dset, [f"({expr})+0*x"], [u] if u else None, mode, outer)
            return np.atleast_2d(data[0])[:, 0]
        try:
            return read(unit)
        except Exception:
            if unit is None:
                raise
            return read(None)   # unit rejected: SI default

    def eval_field(self, expr, study: str, unit=None):
        """Field values at mesh nodes, shape (n_inner, n_points) (or a list for several exprs)."""
        dset, mode, _ = self._reader(study)
        exprs = list(expr) if isinstance(expr, (list, tuple)) else [expr]
        units = (list(unit) if isinstance(unit, (list, tuple)) else [unit]) if unit else None
        expected = self.expected_vf(study)
        modes = [mode] + [m for m in self.READ_MODES if m != mode]
        last = None
        for m in modes:
            for u in ([units, None] if units else [None]):
                try:
                    r = self._numerical("Eval", dset, exprs, u, m)
                except Exception as exc:
                    last = exc
                    continue
                out = [np.atleast_2d(a) for a in r]
                if expected is None or out[0].shape[0] == expected.size:
                    return out if isinstance(expr, (list, tuple)) else out[0]
                last = RuntimeError(f"field read gave {out[0].shape[0]} sweep steps, expected {expected.size}")
        raise RuntimeError(f"cannot read field {exprs} of {study}: {last}")


def _jint(v: int):
    """Java int for COMSOL properties (a Python int is ambiguous int/boolean in JPype)."""
    try:
        import jpype
        if jpype.isJVMStarted():
            return jpype.JInt(int(v))
    except Exception:
        pass
    return str(int(v))


# ===================================================================== CLI
def dry_run() -> None:
    print("Dry run: COMSOL is not used.\n")
    print("Stages:")
    for n, doc in enumerate([PinPeltierBuilder.stage1, PinPeltierBuilder.stage2, PinPeltierBuilder.stage3,
                             PinPeltierBuilder.stage4, PinPeltierBuilder.stage5, PinPeltierBuilder.stage6,
                             PinPeltierBuilder.stage7, PinPeltierBuilder.stage8], start=1):
        print(f"  {n}: {(doc.__doc__ or doc.__name__).strip().splitlines()[0]}")
    print(f"\n{len(api.VERIFY)} API_NAMES entries to verify (docs/VERIFY_API_NAMES.md).")
    print(f"Library material file: {SI_LIBRARY_MPH} ({'present' if SI_LIBRARY_MPH.exists() else 'absent -> fallback'})")
    p = parse_range(load_base()["sweeps"]["VF_iv"])
    print(f"VF sweep: {p[0]}..{p[-1]} V, {p.size} points")


def build(until: int = 8, material_source: str = "auto", cores: int | None = None):
    import mph
    from env import comsol_version, user_env
    cores = cores or user_env().get("mph", {}).get("cores", 4)
    LOG.info("starting COMSOL %s via MPh (cores=%s)", comsol_version(), cores)
    client = mph.start(cores=cores, version=comsol_version())
    model = client.create("pin_peltier")
    b = PinPeltierBuilder(model, client, material_source)
    stages = [b.stage1, b.stage2, b.stage3, b.stage4, b.stage5, b.stage6, b.stage7, b.stage8]
    for n, fn in enumerate(stages[:until], start=1):
        t0 = time.time()
        fn()
        b.save(n)
        LOG.info("stage %d OK (%.1f s)", n, time.time() - t0)
    return client, b


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--until", type=int, default=8, choices=range(1, 9))
    ap.add_argument("--material", default="auto", choices=["auto", "library", "fallback"])
    ap.add_argument("--cores", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if a.dry_run:
        dry_run()
        return 0
    setup_logging(MODELS / "build.log")
    import importlib.util
    if importlib.util.find_spec("mph") is None:
        LOG.error("MPh is not installed: pip install mph")
        return 1
    try:
        build(a.until, a.material, a.cores)
    except ApiNameError as e:
        LOG.error("%s", e)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
