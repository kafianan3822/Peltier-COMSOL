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
        raise ApiNameError(key, exc, extra) from exc


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

    def var(self, key: str) -> str:
        return self.names.get(key, api.name(key))

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
        from write_params_txt import caughey_thomas_expr
        for carrier, vname in (("electrons", "mun_CT"), ("holes", "mup_CT")):
            var.set(vname, caughey_thomas_expr(carrier, self.base), f"Caughey-Thomas mobility ({carrier}), option M2")

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
        edg.selection().all()
        specs = [  # (tag, domain, kind, reverse)
            ("dis_n", 1, "fixed", False), ("dis_p", 4, "fixed", False),
            ("dis_iL", 2, "geom", False), ("dis_iR", 3, "geom", True),
        ]
        self._dists = {}
        for tag, dom, kind, rev in specs:
            with verify("MESH_DIST"):
                d = edg.create(tag, api.name("MESH_DIST"))
            d.selection().set([dom])
            if kind == "fixed":
                with verify("DIST_NUMELEM"):
                    d.set(api.name("DIST_NUMELEM"), nd)
            else:
                with verify("DIST_TYPE"):
                    d.set(api.name("DIST_TYPE"), "predefined")
                with verify("DIST_ELEMCOUNT"):
                    d.set(api.name("DIST_ELEMCOUNT"), ni)
                with verify("DIST_ELEMRATIO"):
                    d.set(api.name("DIST_ELEMRATIO"), ratio)
                with verify("DIST_GROWTH"):
                    d.set(api.name("DIST_GROWTH"), "geometric")
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
        LOG.info("material: explicit fallback properties (spec §4.2 table)")

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
        self.j.param().set("Nc_si", f"{vals['MAT_NC'][1]:.6g}[1/m^3]", "Nc read back from material at T0")
        self.j.param().set("Nv_si", f"{vals['MAT_NV'][1]:.6g}[1/m^3]", "Nv read back from material at T0")
        pin, pip = self.param_value("Pi_nc"), self.param_value("Pi_pc")
        LOG.info("Pi_nc = %.5f V, Pi_pc = %.5f V (spec: ~0.079 / ~0.081 V)", pin, pip)
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
        with verify("SEMI_TREF_PROP"):
            semi.prop(api.name("SEMI_MODEL_GROUP")).set(api.name("SEMI_TREF_PROP"), "T0")
        smm = semi.feature(api.name("SMM_TAG"))
        with verify("SMM_TEMP_SRC", "one-way coupling: semi temperature must be the user-defined T0"):
            smm.set(api.name("SMM_TEMP_SRC"), "userdef")
        with verify("SMM_TEMP"):
            smm.set(api.name("SMM_TEMP"), "T0")
        self.set_bgn("off")
        with verify("SMM_INCION_PROP"):
            smm.set(api.name("SMM_INCION_PROP"), False)
        self.mobility_base = "M1" if self.material_used == "library" else "M2"
        if self.mobility_base == "M2":
            LOG.warning("fallback material has no Arora parameters -> base mobility = M2 "
                        "(Caughey-Thomas, spec §4.3). Recorded in the run headers; see CHANGES.md.")
        self.set_mobility(self.mobility_base, fletcher=False)

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
                d.set(api.name("DOP_X0"), x0)
            with verify("DOP_W"):
                d.set(api.name("DOP_W"), w)
            if profile == "gaussian":
                with verify("DOP_PROFILE"):
                    d.set(api.name("DOP_PROFILE"), api.name("DOP_GAUSS"))
                with verify("DOP_LSCALE_SRC"):
                    d.set(api.name("DOP_LSCALE_SRC"), "length")
                with verify("DOP_LSCALE"):
                    d.set(api.name("DOP_LSCALE"), "l_dec")
            else:
                try:
                    d.set(api.name("DOP_PROFILE"), api.name("DOP_NONE"))
                except Exception:
                    LOG.debug("background box: profile 'none' not settable (box covers the whole bar)")

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

    # ----------------------------------------------------------------- semi switches (variants)
    def set_statistics(self, stats: str) -> None:
        with verify("SEMI_STATS_PROP"):
            self.semi.prop(api.name("SEMI_MODEL_GROUP")).set(
                api.name("SEMI_STATS_PROP"), api.name("SEMI_STATS_MB" if stats == "MB" else "SEMI_STATS_FD"))

    def set_bgn(self, bgn: str) -> None:
        smm = self.semi.feature(api.name("SMM_TAG"))
        with verify("SMM_BGN_PROP"):
            smm.set(api.name("SMM_BGN_PROP"), api.name("SMM_BGN_SLOTBOOM" if bgn == "slotboom" else "SMM_BGN_OFF"))

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
            top = T["mob_arora"]
            if fletcher:
                if T["mob_fletcher"] not in existing:
                    with verify("FEAT_MOB_FLETCHER"):
                        f = smm.create(T["mob_fletcher"], api.name("FEAT_MOB_FLETCHER"), 1)
                else:
                    f = smm.feature(T["mob_fletcher"])
                with verify("MOB_INPUT_N"):
                    f.set(api.name("MOB_INPUT_N"), T["mob_arora"])
                with verify("MOB_INPUT_P"):
                    f.set(api.name("MOB_INPUT_P"), T["mob_arora"])
                top = T["mob_fletcher"]
            with verify("SMM_MUN_SEL"):
                smm.set(api.name("SMM_MUN_SEL"), top)
            with verify("SMM_MUP_SEL"):
                smm.set(api.name("SMM_MUP_SEL"), top)
        else:
            if fletcher:
                raise RuntimeError("Fletcher add-on is defined on top of Arora (M1) only")
            for tag in (T["mob_arora"], T["mob_fletcher"]):
                if tag in existing:
                    smm.feature(tag).active(False)
            try:
                smm.set(api.name("SMM_MUN_SEL"), "userdef")
                smm.set(api.name("SMM_MUP_SEL"), "userdef")
            except Exception:
                LOG.debug("mobility selector does not take 'userdef'; setting user-defined values only")
            self.set_userdef(smm, api.name("SMM_MUN_USER"), "mun_CT", "SMM_MUN_USER")
            self.set_userdef(smm, api.name("SMM_MUP_USER"), "mup_CT", "SMM_MUP_USER")

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
        with verify("FEAT_AUGER"):
            aug = semi.create(T["auger"], api.name("FEAT_AUGER"), 1)
        aug.selection().all()
        self.set_userdef(aug, api.name("AUG_CN"), "Cn_aug", "AUG_CN")
        self.set_userdef(aug, api.name("AUG_CP"), "Cp_aug", "AUG_CP")
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
        I = np.abs(self.eval_global(self.var("I_TERMINAL"), T["std_eq_iv"]))
        VF = self.eval_global("VF", T["std_eq_iv"])
        Ac = self.param_value("Ac")
        J = I / Ac
        if np.any(np.diff(I[VF > 0.05]) <= 0):
            raise RuntimeError("stage 4 smoke test failed: I-V not monotonic")
        J07 = float(np.interp(0.7, VF, J)) * 1e-4
        LOG.info("J(0.7 V) = %.4f A/cm^2 (spec V0 window 0.02-1)", J07)
        if not 0.02 <= J07 <= 1.0:
            raise RuntimeError(f"stage 4 smoke test failed: J(0.7 V) = {J07:.4g} A/cm^2 not in 0.02-1")
        JX = np.abs(self.eval_global(f"pt_p({self.var('J_X')})", T["std_eq_iv"]))
        r = I[VF > 0.3] / (Ac * JX[VF > 0.3])
        LOG.info("consistency |I_TERMINAL| / (Ac*|J_X|) = %.4f .. %.4f", r.min(), r.max())
        if np.any(np.abs(r - 1) > 0.05):
            LOG.warning("I_TERMINAL is not Ac*|J_X| (maybe per-area or a different terminal) -- "
                        "check api name I_TERMINAL; exports keep the spec definition I = terminal current")

    def probe_names(self, study: str, keys: list[str] | None = None) -> None:
        """Pick, for each variable constant, the first candidate COMSOL can evaluate.
        TFLUX_X is probed after stage 5 (needs ht)."""
        for key, item in api.VERIFY.items():
            if item.kind != "variable" or (keys is not None and key not in keys):
                continue
            if keys is None and key in ("TFLUX_X", "NDOP"):
                continue
            ok = None
            for cand in item.candidates or [item.value]:
                expr = cand if key == "I_TERMINAL" else f"pt_c({cand})"
                try:
                    self.eval_global(expr, study)
                    ok = cand
                    break
                except Exception:
                    continue
            if ok is None:
                if key in ("ND_TOT", "NA_TOT", "NC_VAR", "NV_VAR"):
                    LOG.warning("no candidate for %s evaluates (optional): %s", key, item.candidates)
                    continue
                raise ApiNameError(key, extra=f"none of the candidates {item.candidates} evaluates")
            self.names[key] = ok
            if ok != item.value:
                LOG.warning("API name %s: '%s' not found, using '%s'", key, item.value, ok)
            else:
                LOG.info("API name %s = %s (verified by evaluation)", key, ok)
        for key in ("NC_VAR", "NV_VAR"):
            if key in self.names:
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
            raise RuntimeError(f"stage 5 smoke test failed: T(VF=0) deviates from T_room by {dT0:.3g} K")

    def _temp_node(self, tag: str, points: list[int], value: str):
        with verify("FEAT_TEMP"):
            t = self.ht.create(tag, api.name("FEAT_TEMP"), 0)
        t.selection().set(points)
        with verify("TEMP_T0"):
            t.set(api.name("TEMP_T0"), value)
        return t

    def heat_source_expr(self, qsrc: str) -> str:
        q = self.var("Q_TOT")
        return q if qsrc == "builtin" else f"{q}+k_B_const*T0*{self.var('U_TOT')}"

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
                step.set(api.name("STEP_CONTINUATION"), "manual")
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
        apply_variant(self, {"params": {"rz_on": "1"}, "qsrc": "corrected", "stats": "MB", "bgn": "off",
                             "mobility": self.mobility_base, "fletcher": False})
        assert self.hs_expr.endswith(self.var("U_TOT")), "qsrc switch failed"
        apply_variant(self, {"params": {"rz_on": "0"}, "qsrc": "builtin", "stats": "MB", "bgn": "off",
                             "mobility": self.mobility_base, "fletcher": False})
        self.j.param().set("dT_sink", "0[K]")
        self.write_build_info()
        return self.save("pin_peltier_base.mph")

    def write_build_info(self) -> None:
        import json
        info = dict(material=self.material_used, mobility_base=self.mobility_base, names=self.names,
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

    def dataset_of(self, study: str, parametric: bool = False) -> str:
        """Dataset tag holding the solution of `study`.  With `parametric`, the dataset of
        the 'Parametric Solutions' solution created by the Parametric Sweep node."""
        sols = [s for s in self.solutions_of(study)
                if ("Parametric" in str(self.j.sol(s).label())) == parametric]
        for d in self.j.result().dataset().tags():
            try:
                if str(self.j.result().dataset(d).getString("solution")) in sols:
                    return str(d)
            except Exception:
                continue
        raise RuntimeError(f"no {'parametric ' if parametric else ''}dataset found for study {study}")

    def _dlabel(self, study: str, parametric=False) -> str:
        return str(self.j.result().dataset(self.dataset_of(study, parametric)).label())

    def solve(self, study: str, plist: str | None = None) -> None:
        """Run a study; on failure apply the spec §4.6 fallback (segregated, then half VF step)."""
        std = self.j.study(study)
        std.createAutoSequences("all")
        self.set_solver_tolerance(study)
        t0 = time.time()
        try:
            std.run()
            LOG.info("solved %s in %.1f s", study, time.time() - t0)
            return
        except Exception as exc:
            LOG.warning("%s failed (%s) -> fallback 1: segregated solver", study, str(exc).splitlines()[0])
        self.make_segregated(study)
        try:
            std.run()
            LOG.info("solved %s with segregated solver in %.1f s", study, time.time() - t0)
            return
        except Exception as exc:
            LOG.warning("%s failed again (%s) -> fallback 2: halve the VF step", study, str(exc).splitlines()[0])
        st = std.feature("stat") if "stat" in [str(t) for t in std.feature().tags()] else None
        if st is None:
            raise RuntimeError(f"{study}: no stationary step to refine")
        a, d, b = re.fullmatch(r"\s*range\(([^,]+),([^,]+),([^,]+)\)\s*",
                               str(st.getStringArray("plistarr")[0])).groups()
        st.set("plistarr", [f"range({a},{float(d)/2:g},{b})"])
        std.createAutoSequences("all")
        self.set_solver_tolerance(study)
        self.make_segregated(study)
        std.run()
        LOG.info("solved %s with segregated solver and half VF step", study)

    def make_segregated(self, study: str) -> None:
        semi_vars = api.name("DEPVARS_SEMI").split(",")
        for sol in self.solutions_of(study):
            s = self.j.sol(sol)
            for ftag in s.feature().tags():
                f = s.feature(ftag)
                if str(f.getType()) != "Stationary":
                    continue
                with verify("SOLVER_SEGREGATED"):
                    tags = [str(t) for t in f.feature().tags()]
                    se = f.feature("se1") if "se1" in tags else f.create("se1", api.name("SOLVER_SEGREGATED"))
                with verify("SEG_DEFAULT_STEP"):
                    ss1 = se.feature(api.name("SEG_DEFAULT_STEP"))
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

    def eval_global(self, expr: str, study: str, unit: str | None = None, parametric: bool = False,
                    outer: int | None = None) -> np.ndarray:
        r = self.model.evaluate(expr, unit, dataset=self._dlabel(study, parametric), outer=outer)
        return np.atleast_1d(np.asarray(r, dtype=float))

    def eval_field(self, expr, study: str, unit=None) -> np.ndarray:
        """Field values at mesh nodes, shape (n_inner, n_points) (or list for several exprs)."""
        r = self.model.evaluate(expr, unit, dataset=self._dlabel(study))
        if isinstance(expr, (list, tuple)):
            return [np.atleast_2d(np.asarray(a, dtype=float)) for a in r]
        return np.atleast_2d(np.asarray(r, dtype=float))


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
