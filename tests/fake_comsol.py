"""Test double for the slice of the COMSOL Java API and MPh that Driver A uses.

It is NOT a physics model. It lets the tests execute every code path of
comsol/python/build_model.py and run_variants.py (stages 1-8, variant
application, exports, fallbacks) without COMSOL. Evaluations return
reference-model numbers, shaped the way MPh returns them, so the downstream
analysis also runs. Anything produced with it is written to pytest's tmp_path
only and must never be reported as a COMSOL result.
"""
from __future__ import annotations

import re

import numpy as np

from common.params import eval_expr, parse_range


class FakeSelection:
    def __init__(self):
        self.entities, self.dim, self.is_all = [], None, False

    def all(self):
        self.is_all = True

    def set(self, ents):
        self.entities = list(ents)

    def geom(self, g, dim):
        self.dim = dim


class FakeEntity:
    def __init__(self, tag="", ftype="", parent=None):
        self.tag, self.ftype, self.parent = tag, ftype, parent
        self.props: dict = {}
        self.children: dict[str, FakeEntity] = {}
        self._label = tag
        self._active = True
        self._sel = FakeSelection()

    # property access
    def set(self, name, value, desc=None):
        self.props[name] = value
        return self

    def getString(self, name):
        v = self.props[name]
        return v[0] if isinstance(v, (list, tuple)) else str(v)

    def getStringArray(self, name):
        v = self.props[name]
        return list(v) if isinstance(v, (list, tuple)) else [str(v)]

    def getBoolean(self, name):
        return bool(self.props.get(name, False))

    def properties(self):
        return list(self.props)

    def getType(self):
        return self.ftype

    def label(self, new=None):
        if new is None:
            return self._label
        self._label = new
        return self

    def active(self, a):
        self._active = bool(a)
        return self

    def selection(self):
        return self._sel

    # children
    def create(self, tag, ftype="", *dims):
        child = FakeEntity(tag, ftype, self)
        if ftype == "Common":                       # materials come with the 'def' group
            child.children["def"] = FakeEntity("def", "group", child)
        if ftype == "Segregated":                   # default segregated step
            child.children["ssDef"] = FakeEntity("ssDef", "SegregatedStep", child)
        self.children[tag] = child
        return child

    def feature(self, tag=None):
        if tag is None:
            return self
        return self.children[tag]

    def tags(self):
        return list(self.children)

    def remove(self, tag):
        self.children.pop(tag, None)

    def prop(self, group):
        return self.children.setdefault(group, FakeEntity(group, "prop", self))

    def propertyGroup(self, tag=None):
        if tag is None:
            return self
        return self.children[tag]


class FakeGeom(FakeEntity):
    def run(self):
        pass

    def getNDomains(self):
        return 4

    def getNBoundaries(self):
        return 5


class FakeMesh(FakeEntity):
    """Emulates COMSOL edge distributions: fixed count, or geometric with
    element ratio (last/first along the edge direction, flipped by 'reverse')."""

    def __init__(self, tag, parent, fake):
        super().__init__(tag, "Mesh", parent)
        self.fake = fake
        self.built = False

    def run(self):
        self.built = True

    def getVertex(self):
        p = self.fake.pvals()
        ends = [0.0, p["Wn"], p["Xc"], p["Wn"] + p["Wi"], p["Ltot"]]
        pts = [np.array([0.0])]
        edg = self.children["edg1"]
        for d in edg.children.values():
            dom = d._sel.entities[0]
            a, b = ends[dom - 1], ends[dom]
            if "numelem" in d.props:
                x = np.linspace(a, b, int(d.props["numelem"]) + 1)
            else:
                n, r = int(d.props["elemcount"]), float(d.props["elemratio"])
                q = r ** (1.0 / (n - 1))
                h = q ** np.arange(n)
                if d.props.get("reverse"):
                    h = h[::-1]
                x = a + (b - a) * np.concatenate([[0], np.cumsum(h)]) / h.sum()
            pts.append(x[1:])
        return [list(np.concatenate(pts))]


class FakeComp(FakeEntity):
    def __init__(self, fake):
        super().__init__("comp1", "Component")
        self.fake = fake
        for n in ("geom", "material", "physics", "mesh", "variable", "cpl"):
            self.children[n] = FakeEntity(n, "list", self)

    def geom(self, tag=None):
        lst = self.children["geom"]
        if tag is None:
            outer = self

            class L:
                def create(self, t, dim):
                    g = FakeGeom(t, "Geom", outer)
                    lst.children[t] = g
                    return g
            return L()
        return lst.children[tag]

    def mesh(self, tag=None):
        lst = self.children["mesh"]
        if tag is None:
            outer = self

            class L:
                def create(self, t):
                    m = FakeMesh(t, outer, outer.fake)
                    lst.children[t] = m
                    return m

                def tags(self):
                    return list(lst.children)

                def remove(self, t):
                    lst.children.pop(t, None)
            return L()
        return lst.children[tag]

    def _list(self, name, tag):
        lst = self.children[name]
        return lst if tag is None else lst.children[tag]

    def material(self, tag=None):
        return self._list("material", tag)

    def physics(self, tag=None):
        if tag is None:
            lst = self.children["physics"]

            class L:
                def create(self, t, ftype, geom):
                    p = lst.create(t, ftype)
                    if ftype == "Semiconductor":
                        p.create("smm1", "SemiconductorMaterialModel")
                    if ftype == "HeatTransfer":
                        p.create("init1", "init")
                    return p
            return L()
        return self.children["physics"].children[tag]

    def variable(self, tag=None):
        return self._list("variable", tag)

    def cpl(self, tag=None):
        return self._list("cpl", tag)


class FakeParam:
    def __init__(self):
        self.exprs: dict[str, str] = {}

    def set(self, name, expr, desc=None):
        self.exprs[name] = str(expr)

    def env(self):
        env: dict[str, float] = {}
        for k, e in self.exprs.items():
            env[k] = eval_expr(e, env)
        return env

    def evaluate(self, expr):
        return eval_expr(expr, self.env())


class FakeStudy(FakeEntity):
    def __init__(self, tag, fake):
        super().__init__(tag, "Study")
        self.fake = fake

    def createAutoSequences(self, what):
        self.fake._make_solutions(self)

    def run(self):
        self.fake._make_solutions(self)
        self.fake.runs.append(self.tag)
        if self.fake.fail_next.get(self.tag, 0) > 0:
            self.fake.fail_next[self.tag] -= 1
            raise RuntimeError("Failed to find a solution (fake)")


class FakeJava:
    def __init__(self, fake):
        self.fake = fake
        self._param = FakeParam()
        self._comp = None
        self._func = FakeEntity("func", "list")
        self._study = FakeEntity("study", "list")
        self._sol = FakeEntity("sol", "list")
        self._result = FakeEntity("result", "list")
        self._result.children["dataset"] = FakeEntity("dataset", "list")
        self._result.children["numerical"] = FakeEntity("numerical", "list")
        self.saved = []

    def param(self):
        return self._param

    def component(self, tag=None):
        if tag is None:
            outer = self

            class L:
                def create(self, t, b):
                    outer._comp = FakeComp(outer.fake)
                    return outer._comp
            return L()
        return self._comp

    def func(self, tag=None):
        return self._func if tag is None else self._func.children[tag]

    def study(self, tag=None):
        if tag is None:
            outer = self

            class L:
                def create(self, t):
                    s = FakeStudy(t, outer.fake)
                    outer._study.children[t] = s
                    return s
            return L()
        return self._study.children[tag]

    def sol(self, tag=None):
        return self._sol if tag is None else self._sol.children[tag]

    def result(self):
        outer = self

        class R:
            def dataset(self, tag=None):
                d = outer._result.children["dataset"]
                return d if tag is None else d.children[tag]
        return R()

    def save(self, path):
        self.saved.append(path)


class FakeModel:
    """mph.Model look-alike. `ref` maps 'V0'/'V1'-like keys to reference results."""

    def __init__(self, ref_glob, ref_profile):
        self.java = FakeJava(self)
        self.ref_glob = ref_glob            # DataFrame (reference global_vs_VF)
        self.ref_profile = ref_profile      # DataFrame (reference profile at 0.7 V)
        self.runs: list[str] = []
        self.fail_next: dict[str, int] = {}

    # -------------------------------------------------- MPh API
    def parameter(self, name, value=None):
        self.java._param.set(name, value)

    def pvals(self):
        return self.java._param.env()

    def evaluate(self, expr, unit=None, dataset=None, inner=None, outer=None):
        study, parametric = self._study_of_label(dataset)
        VF = self._vf(study)
        if isinstance(expr, (list, tuple)):
            return [self._field(e, VF) for e in expr]
        return self._global_or_field(expr, VF, study, outer)

    # -------------------------------------------------- internals
    def _make_solutions(self, study: FakeStudy):
        sols = self.java._sol.children
        ds = self.java._result.children["dataset"].children
        for par in (False, True):
            if par and not ("param" in study.children and study.children["param"]._active):
                continue
            st = f"sol_{study.tag}{'_p' if par else ''}"
            if st not in sols:
                s = FakeEntity(st, "Solution")
                s.study = (lambda t=study.tag: t)
                s._label = "Parametric Solutions 1" if par else f"Solution {study.tag}"
                stat = s.create("s1", "Stationary")
                stat.create("fc1", "FullyCoupled")
                sols[st] = s
                d = FakeEntity(f"dset_{st}", "Solution")
                d.props["solution"] = st
                d._label = f"{study.tag}//{s._label}"
                ds[d.tag] = d

    def _study_of_label(self, label):
        for d in self.java._result.children["dataset"].children.values():
            if d._label == label:
                st = d.props["solution"]
                return st.replace("sol_", "").replace("_p", ""), st.endswith("_p")
        raise KeyError(label)

    def _vf(self, study):
        s = self.java._study.children[study]
        if "stat" not in s.children:
            return np.array([0.0])
        return parse_range(s.children["stat"].getString("plistarr"))

    def _ref(self, col, VF):
        g = self.ref_glob
        sign = np.sign(VF)
        return np.interp(np.abs(VF), g.VF, g[col]) * np.where(sign == 0, 1, sign)

    def _global_or_field(self, expr, VF, study, outer):
        p = self.pvals()
        Ac = p["Ac"]
        if expr == "VF":
            return VF
        if expr.startswith("Ac*(pt_n("):           # room expression
            dT = parse_range("range(-0.02,0.0025,0.02)")[(outer or 1) - 1]
            slope = -Ac * p["k_Si"] * (2 / p["Xc"])
            return self._ref("Q_room", VF) + slope * dT
        m = re.fullmatch(r"(pt_n|pt_c|pt_p|intop_all|intop_i)\((.*)\)", expr)
        if expr.startswith("semi.I0") or expr.startswith("abs(semi.I0"):
            return self._ref("I", VF)
        if m is None:
            return self._field(expr, VF)
        op, arg = m.groups()
        if arg == "T":
            col = {"pt_n": "T_P1", "pt_p": "T_P5", "pt_c": "T_P3"}[op]
            return self._ref(col, VF) if study in ("std_float", "std_lat") else np.full_like(VF, p["T_room"])
        if "tfluxX" in arg:
            return self._ref("qx_0" if op == "pt_n" else "qx_L", VF)
        if op == "intop_i":
            return -self._ref("V_ohm", VF)
        if op == "intop_all":
            if "x<Wn" in arg:
                return self._ref("Qjn_n", VF) / Ac
            if "x>Ltot" in arg:
                return self._ref("Qjn_p", VF) / Ac
            return 0.96 * self._ref("P_el", VF) / Ac - self._ref("Qc_contacts", VF) / Ac
        if "JX" in arg:
            return self._ref("J", VF)
        return np.zeros_like(VF)

    def _field(self, expr, VF):
        x = np.asarray(self.java._comp.mesh("mesh1").getVertex()[0])
        n = VF.size
        p = self.pvals()
        prof = self.ref_profile
        scale = np.clip(self._ref("J", VF) / max(self.ref_glob.J.max(), 1e-30), 0, None)[:, None]
        if expr == "x":
            return np.tile(x, (n, 1))
        if expr == "T":
            T = np.interp(x, prof.x, prof["T"]) - p["T_room"]
            return p["T_room"] + scale * T[None, :]
        if expr.endswith("Ndoping"):
            nd = np.where(x < p["Wn"], p["Nd_p"], np.where(x > p["Ltot"] - p["Wp"], -p["Na_p"], -p["N_bg"]))
            return np.tile(nd, (n, 1))
        if "Q_tot" in expr:
            return scale * np.interp(x, prof.x, prof["Q_tot"])[None, :]
        if expr in ("semi.N", "semi.P"):
            return np.tile(np.interp(x, prof.x, prof["n"]), (n, 1))
        return np.zeros((n, x.size))


class FakeClient:
    def __init__(self, model_factory):
        self.model_factory = model_factory
        self.version = "fake"

    def load(self, path):
        return self.model_factory()

    def remove(self, model):
        pass
