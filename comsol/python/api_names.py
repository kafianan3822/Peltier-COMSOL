"""API_NAMES -- every COMSOL feature-type string, property name and variable name
that this package could not confirm without a COMSOL installation (spec §0 rule 1,
§9.4).  ONE place, shared by both drivers:

* Driver A (Python/MPh) imports this module.
* Driver B (Java) carries a generated copy of the same block between the markers
  ``// BEGIN API_NAMES`` / ``// END API_NAMES`` in BuildPinPeltier.java and
  RunVariants.java.  Regenerate it with ``python comsol/python/sync_java_api_names.py``;
  tests/test_postprocess.py fails if the copies drift apart.

How to confirm a name (applies to every entry; specifics in docs/VERIFY_API_NAMES.md):
    1. In the COMSOL 6.3 GUI build just the one node (the `gui` text says how).
    2. File > Save As > Model File for Java (*.java).
    3. Open the .java file and search for the `java_hint` pattern; the string in
       that position is the true tag/property for your version.
    4. Put the corrected value in config/api_names_override.yaml
       (``NAME: "value"``); no code edits are needed.  Both drivers read it
       (the Java copy after re-running sync_java_api_names.py).

Variable names (kind == "variable") also carry `candidates`.  After the first
solve the Python builder probes each candidate and keeps the first one that
COMSOL can evaluate, logging the choice; the Java builder does the same.
If none evaluates, the build stops with an error naming the constant.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OVERRIDE_FILE = ROOT / "config" / "api_names_override.yaml"


@dataclass
class V:
    value: str
    kind: str                     # feature | property | value | variable | tag
    gui: str                      # GUI action that creates the node / shows the setting
    java_hint: str                # where it appears in "Save as Java" output
    candidates: list = field(default_factory=list)   # alternatives probed at run time


# ============================================================================
# API_NAMES  (all entries are ⚠VERIFY)
# ============================================================================
VERIFY: dict[str, V] = {
    # ---------------------------------------------------------------- physics
    "PHYS_SEMI": V("Semiconductor", "feature",
                   "Add Physics > Semiconductor > Semiconductor (semi)",
                   'physics().create("semi", "<HERE>", "geom1")'),
    "PHYS_HT": V("HeatTransfer", "feature",
                 "Add Physics > Heat Transfer > Heat Transfer in Solids (ht)",
                 'physics().create("ht", "<HERE>", "geom1")'),
    # ---------------------------------------------------------------- semi features
    "FEAT_DOPING": V("AnalyticDopingModel", "feature",
                     "semi > right-click > Analytic Doping Model",
                     'physics("semi").create("adm1", "<HERE>", 1)'),
    "FEAT_SRH": V("TrapAssistedRecombination", "feature",
                  "semi > right-click > Trap-Assisted Recombination",
                  'physics("semi").create("tar1", "<HERE>", 1)'),
    "FEAT_AUGER": V("AugerRecombination", "feature",
                    "semi > right-click > Auger Recombination",
                    'physics("semi").create("auger1", "<HERE>", 1)'),
    "FEAT_CONTACT": V("MetalContact", "feature",
                      "semi > right-click > Metal Contact (select point)",
                      'physics("semi").create("mc1", "<HERE>", 0)'),
    "FEAT_MOB_ARORA": V("AroraMobilityModel", "feature",
                        "semi > Semiconductor Material Model 1 > right-click > Arora Mobility Model (LI)",
                        'feature("smm1").create("mmal1", "<HERE>", 1)'),
    "FEAT_MOB_FLETCHER": V("FletcherMobilityModel", "feature",
                           "semi > Semiconductor Material Model 1 > right-click > Fletcher Mobility Model (C)",
                           'feature("smm1").create("mmfc1", "<HERE>", 1)'),
    # ---------------------------------------------------------------- semi interface props
    "SEMI_AREA_GROUP": V("d", "property",
                         "semi > Settings > Cross-Sectional Area (1D component)",
                         'physics("semi").prop("<HERE>").set("A", "Ac")'),
    "SEMI_AREA_PROP": V("A", "property", "semi > Settings > Cross-Sectional Area > A (value Ac)", 'physics("semi").prop("d").set("<HERE>", "Ac")'),
    "SEMI_MODEL_GROUP": V("ModelProperties", "property",
                          "semi > Settings > Model Properties (carrier statistics)",
                          'physics("semi").prop("<HERE>").set("CarrierStatistics", ...)'),
    "SEMI_STATS_PROP": V("CarrierStatistics", "property", "semi > Settings > Carrier statistics",
                         'prop("ModelProperties").set("<HERE>", "MaxwellBoltzmann")'),
    "SEMI_STATS_MB": V("MaxwellBoltzmann", "value", "Carrier statistics = Maxwell-Boltzmann",
                       'set("CarrierStatistics", "<HERE>")'),
    "SEMI_STATS_FD": V("FermiDirac", "value", "Carrier statistics = Fermi-Dirac",
                       'set("CarrierStatistics", "<HERE>")'),
    "SEMI_TREF_PROP": V("T0", "property",
                        "semi > Settings > Reference temperature for energy levels (Tref)",
                        'prop("ModelProperties").set("<HERE>", "T0")'),
    "SEMI_DISC_GROUP": V("ShapeProperty", "property", "semi > Settings > Discretization",
                         'prop("<HERE>").set("Formulation", "FV")'),
    # ---------------------------------------------------------------- semiconductor material model (smm1)
    "SMM_TAG": V("smm1", "tag", "semi > Semiconductor Material Model 1 (default node)",
                 'physics("semi").feature("<HERE>")'),
    "SMM_TEMP_SRC": V("minput_temperature_src", "property",
                      "smm1 > Model Input > Temperature = User defined",
                      'feature("smm1").set("<HERE>", "userdef")'),
    "SMM_TEMP": V("minput_temperature", "property", "smm1 > Model Input > Temperature value",
                  'feature("smm1").set("<HERE>", "T0")'),
    "SMM_BGN_PROP": V("BandGapNarrowing", "property", "smm1 > Band-Gap Narrowing",
                      'feature("smm1").set("<HERE>", "Slotboom")'),
    "SMM_BGN_OFF": V("Off", "value", "Band-gap narrowing = Off", 'set("BandGapNarrowing", "<HERE>")'),
    "SMM_BGN_SLOTBOOM": V("Slotboom", "value", "Band-gap narrowing = Slotboom",
                          'set("BandGapNarrowing", "<HERE>")'),
    "SMM_INCION_PROP": V("IncompleteIonization", "property", "smm1 > Dopant Ionization = Complete",
                         'feature("smm1").set("<HERE>", false)'),
    "SMM_MUN_SEL": V("mun_mob", "property",
                     "smm1 > Mobility Model > Electron mobility (select model node)",
                     'feature("smm1").set("<HERE>", "mmal1")'),
    "SMM_MUP_SEL": V("mup_mob", "property",
                     "smm1 > Mobility Model > Hole mobility (select model node)",
                     'feature("smm1").set("<HERE>", "mmal1")'),
    "SMM_MUN_USER": V("mun", "property", "smm1 > Electron mobility (user defined, M2)",
                      'feature("smm1").set("<HERE>", "mun_CT")'),
    "SMM_MUP_USER": V("mup", "property", "smm1 > Hole mobility (user defined, M2)",
                      'feature("smm1").set("<HERE>", "mup_CT")'),
    "MOB_INPUT_N": V("mun_in", "property", "Fletcher node > Input electron mobility = Arora",
                     'feature("mmfc1").set("<HERE>", "mmal1")'),
    "MOB_INPUT_P": V("mup_in", "property", "Fletcher node > Input hole mobility = Arora",
                     'feature("mmfc1").set("<HERE>", "mmal1")'),
    "USERDEF_SUFFIX": V("_mat", "property",
                        "any 'From material / User defined' combo box",
                        'set("taun<HERE>", "userdef")'),
    # ---------------------------------------------------------------- analytic doping
    "DOP_TYPE": V("dopantType", "property", "Analytic Doping Model > Impurity type",
                  'feature("adm1").set("<HERE>", "donor")'),
    "DOP_DONOR": V("donor", "value", "Impurity type = Donor doping", 'set("dopantType", "<HERE>")'),
    "DOP_ACCEPTOR": V("acceptor", "value", "Impurity type = Acceptor doping",
                      'set("dopantType", "<HERE>")'),
    "DOP_DIST": V("dopingDistribution", "property", "Analytic Doping Model > Distribution = Box",
                  'feature("adm1").set("<HERE>", "box")'),
    "DOP_BOX": V("box", "value", "Distribution = Box", 'set("dopingDistribution", "<HERE>")'),
    "DOP_NA": V("NAc", "property", "Acceptor concentration N_A0", 'feature("adm1").set("<HERE>", ...)'),
    "DOP_ND": V("NDc", "property", "Donor concentration N_D0", 'feature("adm1").set("<HERE>", ...)'),
    "DOP_X0": V("x0", "property", "Box > Base position (1D)", 'feature("adm1").set("<HERE>", "0")'),
    "DOP_W": V("W", "property", "Box > Width (1D)", 'feature("adm1").set("<HERE>", "Wn")'),
    "DOP_PROFILE": V("profile", "property", "Profile away from uniform region = Gaussian",
                     'feature("adm1").set("<HERE>", "gaussian")'),
    "DOP_GAUSS": V("gaussian", "value", "Profile = Gaussian", 'set("profile", "<HERE>")'),
    "DOP_NONE": V("none", "value", "Profile = none / step (background box)", 'set("profile", "<HERE>")'),
    "DOP_LSCALE_SRC": V("pspec", "property", "Specify profile length scale (vs junction depth)",
                        'feature("adm1").set("<HERE>", "length")'),
    "DOP_LSCALE": V("l", "property", "Profile length scale (decay length)",
                    'feature("adm1").set("<HERE>", "l_dec")'),
    # ---------------------------------------------------------------- recombination / contacts
    "SRH_TAUN": V("taun", "property", "Trap-Assisted Recombination > Electron lifetime, SRH",
                  'feature("tar1").set("<HERE>", "tau_x")'),
    "SRH_TAUP": V("taup", "property", "Trap-Assisted Recombination > Hole lifetime, SRH",
                  'feature("tar1").set("<HERE>", "tau_x")'),
    "SRH_ET": V("Et", "property", "Trap energy level (relative to midgap = 0)",
                'feature("tar1").set("<HERE>", "0")'),
    "AUG_CN": V("Cn", "property", "Auger > Electron Auger coefficient",
                'feature("auger1").set("<HERE>", "Cn_aug")'),
    "AUG_CP": V("Cp", "property", "Auger > Hole Auger coefficient",
                'feature("auger1").set("<HERE>", "Cp_aug")'),
    "MC_TERMTYPE": V("TerminalType", "property", "Metal Contact > Terminal type = Voltage",
                     'feature("mc1").set("<HERE>", "Voltage")'),
    "MC_VOLTAGE": V("Voltage", "value", "Terminal type = Voltage", 'set("TerminalType", "<HERE>")'),
    "MC_V0": V("V0", "property", "Metal Contact > Voltage", 'feature("mc1").set("<HERE>", "VF")'),
    # ---------------------------------------------------------------- heat transfer
    "FEAT_HS": V("HeatSource", "feature", "ht > right-click > Heat Source",
                 'physics("ht").create("hs1", "<HERE>", 1)'),
    "FEAT_BHS": V("BoundaryHeatSource", "feature", "ht > right-click > Boundary Heat Source (point in 1D)",
                  'physics("ht").create("bhs1", "<HERE>", 0)'),
    "FEAT_TEMP": V("TemperatureBoundary", "feature", "ht > right-click > Temperature (point in 1D)",
                   'physics("ht").create("temp1", "<HERE>", 0)'),
    "HS_Q0": V("Q0", "property", "Heat Source > General source Q", 'feature("hs1").set("<HERE>", ...)'),
    "BHS_QB": V("Qb", "property", "Boundary Heat Source > Q_b", 'feature("bhs1").set("<HERE>", ...)'),
    "TEMP_T0": V("T0", "property", "Temperature > T_0", 'feature("temp1").set("<HERE>", "T_room")'),
    "HT_AREA_GROUP": V("d", "property", "ht > Settings > Cross-Sectional Area (1D)",
                       'physics("ht").prop("<HERE>").set("Ac", "Ac")'),
    "HT_AREA_PROP": V("Ac", "property", "ht > Settings > Cross-Sectional Area > A_c (value Ac)", 'physics("ht").prop("d").set("<HERE>", "Ac")'),
    "HT_BFLUX_GROUP": V("ShapeProperty", "property", "ht > Discretization > Compute boundary fluxes",
                        'physics("ht").prop("<HERE>").set("boundaryFlux_temperature", true)'),
    "HT_BFLUX_PROP": V("boundaryFlux_temperature", "property", "ht > Discretization > Compute boundary fluxes (check box)",
                       'prop("ShapeProperty").set("<HERE>", true)'),
    "HT_INIT_TAG": V("init1", "tag", "ht > Initial Values 1 (default)", 'physics("ht").feature("<HERE>")'),
    "HT_INIT_T": V("Tinit", "property", "Initial Values > Temperature", 'feature("init1").set("<HERE>", "T_room")'),
    # ---------------------------------------------------------------- material
    "MAT_SEMI_GROUP": V("SemicondMaterial", "tag", "Material > Semiconductor material property group",
                        'material("mat1").propertyGroup().create("<HERE>", "Semiconductor material")'),
    "MAT_RELPERM": V("relpermittivity", "property", "Material > Relative permittivity",
                     'propertyGroup("def").set("<HERE>", ...)'),
    "MAT_EG0": V("Eg0", "property", "Semiconductor material > Band gap", 'propertyGroup("SemicondMaterial").set("<HERE>", ...)'),
    "MAT_CHI0": V("chi0", "property", "Semiconductor material > Electron affinity", 'set("<HERE>", ...)'),
    "MAT_NC": V("Nc", "property", "Semiconductor material > Effective DOS, conduction band", 'set("<HERE>", ...)'),
    "MAT_NV": V("Nv", "property", "Semiconductor material > Effective DOS, valence band", 'set("<HERE>", ...)'),
    "MAT_MUN": V("mun", "property", "Semiconductor material > Electron mobility", 'set("<HERE>", ...)'),
    "MAT_MUP": V("mup", "property", "Semiconductor material > Hole mobility", 'set("<HERE>", ...)'),
    # ---------------------------------------------------------------- studies / solver
    "STUDY_EQ": V("SemiconductorEquilibrium", "feature", "Study > Study Steps > Semiconductor Equilibrium",
                  'study("std1").create("sseq", "<HERE>")'),
    "STUDY_STAT": V("Stationary", "feature", "Study > Study Steps > Stationary",
                    'study("std1").create("stat", "<HERE>")'),
    "STUDY_PARAM": V("Parametric", "feature", "Study > right-click > Parametric Sweep",
                     'study("std2").create("param", "<HERE>")'),
    "STEP_ACTIVATE": V("activate", "property", "Study step > Physics and Variables Selection (Solve for)",
                       'feature("stat").set("<HERE>", new String[]{"semi", "on", "ht", "off"})'),
    "STEP_USEDISABLE": V("useadvanceddisable", "property",
                         "Study step > Modify model configuration for study step (check box)",
                         'feature("stat").set("<HERE>", true)'),
    "STEP_DISABLED": V("disabledphysics", "property", "Study step > disable physics features list",
                       'feature("stat").set("<HERE>", new String[]{"ht/temp_sinkA"})'),
    "STEP_CONTINUATION": V("pcontinuationmode", "property",
                           "Study step > Study Extensions > Auxiliary sweep > Run continuation for",
                           'feature("stat").set("<HERE>", "manual")'),
    "STEP_CONT_PARAM": V("pcontinuation", "property", "Study step > Auxiliary sweep > Run continuation for = VF",
                         'feature("stat").set("<HERE>", "VF")'),
    "SOLVER_STOL": V("stol", "property", "Solver Configurations > Stationary Solver 1 > Relative tolerance",
                     'sol("sol1").feature("s1").set("<HERE>", "1e-6")'),
    "SOLVER_SEGREGATED": V("Segregated", "feature", "Stationary Solver > right-click > Segregated",
                           'feature("s1").create("se1", "<HERE>")'),
    "SEG_STEP": V("SegregatedStep", "feature", "Segregated > right-click > Segregated Step",
                  'feature("se1").create("ss2", "<HERE>")'),
    "SEG_VARS": V("segvar", "property", "Segregated Step > Variables",
                  'feature("ss1").set("<HERE>", new String[]{"comp1_V", "comp1_N", "comp1_P"})'),
    "SEG_DEFAULT_STEP": V("ssDef", "tag", "Segregated 1 > default Segregated Step node",
                          'feature("se1").feature("<HERE>").set("segvar", ...)'),
    "DEPVARS_SEMI": V("comp1_V,comp1_N,comp1_P", "value", "Dependent variables of semi (FV formulation)",
                      'set("segvar", new String[]{<HERE>})'),
    "DEPVAR_T": V("comp1_T", "value", "Dependent variable of ht", 'set("segvar", new String[]{"<HERE>"})'),
    # ---------------------------------------------------------------- geometry
    "GEOM_INTERVAL": V("Interval", "feature", "Geometry 1 > right-click > Interval",
                       'geom("geom1").create("i1", "<HERE>")'),
    "INT_SPECIFY_PROP": V("intervals", "property", "Interval > Number of intervals = Many",
                          'feature("i1").set("<HERE>", "many")'),
    "INT_SPECIFY_VAL": V("many", "value", "Number of intervals = Many", 'set("intervals", "<HERE>")'),
    "INT_COORD_PROP": V("p", "property", "Interval > Points (coordinates)",
                        'feature("i1").set("<HERE>", new String[]{"0", "Wn", "Xc", "Wn+Wi", "Ltot"})'),
    # ---------------------------------------------------------------- definitions / mesh
    "FUNC_RECT": V("Rectangle", "feature", "Definitions > Functions > Rectangle",
                   'func().create("rect1", "<HERE>")'),
    "RECT_LOWER": V("lower", "property", "Rectangle > Lower limit", 'func("rect1").set("<HERE>", ...)'),
    "RECT_UPPER": V("upper", "property", "Rectangle > Upper limit", 'func("rect1").set("<HERE>", ...)'),
    "RECT_SMOOTH": V("smooth", "property", "Rectangle > Smoothing > Size of transition zone",
                     'func("rect1").set("<HERE>", "10[um]")'),
    "CPL_INTEGRATION": V("Integration", "feature", "Definitions > Nonlocal Couplings > Integration",
                         'cpl().create("intop1", "<HERE>")'),
    "MESH_EDGE": V("Edge", "feature", "Mesh > Edge (1D)", 'mesh("mesh1").create("edg1", "<HERE>")'),
    "MESH_DIST": V("Distribution", "feature", "Edge > right-click > Distribution",
                   'feature("edg1").create("dis1", "<HERE>")'),
    "DIST_TYPE": V("type", "property", "Distribution > Distribution type", 'feature("dis1").set("<HERE>", "predefined")'),
    "DIST_NUMELEM": V("numelem", "property", "Distribution (Fixed number) > Number of elements",
                      'feature("dis1").set("<HERE>", 400)'),
    "DIST_ELEMCOUNT": V("elemcount", "property", "Distribution (Predefined) > Number of elements",
                        'feature("dis1").set("<HERE>", 600)'),
    "DIST_ELEMRATIO": V("elemratio", "property", "Distribution (Predefined) > Element ratio",
                        'feature("dis1").set("<HERE>", 2000)'),
    "DIST_GROWTH": V("growthrate", "property", "Distribution (Predefined) > Distribution method = Geometric",
                     'feature("dis1").set("<HERE>", "geometric")'),
    "DIST_REVERSE": V("reverse", "property", "Distribution > Reverse direction",
                      'feature("dis1").set("<HERE>", true)'),
    # ---------------------------------------------------------------- variables (probed at run time)
    "Q_TOT": V("semi.Q_tot", "variable", "Results > Add expression > Semiconductor > Heat source",
               "search 'Q_tot' in expression list", ["semi.Q_tot", "semi.Qh", "semi.Q"]),
    "U_TOT": V("semi.U_tot", "variable",
               "Results > Add expression > Semiconductor > Generation-recombination > total recombination",
               "search 'total recombination' in the variable list",
               ["semi.U_tot", "semi.R_tot", "semi.U", "semi.Rtot", "semi.GR_tot"]),
    "J_X": V("semi.JX", "variable", "Results > Add expression > Semiconductor > Current > Total current density, x",
             "search 'current density' in the variable list", ["semi.JX", "semi.Jx", "semi.J_x"]),
    "E_X": V("semi.EX", "variable", "Results > Add expression > Semiconductor > Electric field, x",
             "search 'Electric field' in the variable list", ["semi.EX", "semi.Ex", "-d(V,x)"]),
    "I_TERMINAL": V("semi.I0_2", "variable",
                    "Results > Add expression > Semiconductor > Terminals > Terminal current (terminal of mc_p)",
                    "Metal Contact mc_p > Terminal name; variable semi.I0_<name>",
                    ["semi.I0_2", "semi.I0_mc_p", "semi.mc2.I0", "semi.I0_1"]),
    "EC": V("semi.Ec", "variable", "Semiconductor > Band diagram > Conduction band energy", "",
            ["semi.Ec", "semi.Ec_e"]),
    "EV": V("semi.Ev", "variable", "Semiconductor > Band diagram > Valence band energy", "",
            ["semi.Ev", "semi.Ev_e"]),
    "EFN": V("semi.Efn", "variable", "Semiconductor > Band diagram > Electron quasi-Fermi level", "",
             ["semi.Efn", "semi.Efn_e"]),
    "EFP": V("semi.Efp", "variable", "Semiconductor > Band diagram > Hole quasi-Fermi level", "",
             ["semi.Efp", "semi.Efp_e"]),
    "N_E": V("semi.N", "variable", "Semiconductor > Electron concentration", "", ["semi.N", "semi.n", "N"]),
    "P_H": V("semi.P", "variable", "Semiconductor > Hole concentration", "", ["semi.P", "semi.p", "P"]),
    "NDOP": V("semi.Ndoping", "variable", "Semiconductor > Signed dopant concentration", "",
              ["semi.Ndoping", "semi.Nd_net", "semi.Ndop"]),
    "ND_TOT": V("semi.Nd", "variable", "Semiconductor > Donor concentration (for M2 N_tot)", "",
                ["semi.Nd", "semi.Nd_plus", "semi.Ndplus"]),
    "NA_TOT": V("semi.Na", "variable", "Semiconductor > Acceptor concentration (for M2 N_tot)", "",
                ["semi.Na", "semi.Na_minus", "semi.Naminus"]),
    "NC_VAR": V("semi.Nc", "variable", "Semiconductor > Effective DOS, conduction band", "",
                ["semi.Nc", "semi.Nc_eff"]),
    "NV_VAR": V("semi.Nv", "variable", "Semiconductor > Effective DOS, valence band", "",
                ["semi.Nv", "semi.Nv_eff"]),
    "TFLUX_X": V("ht.tfluxX", "variable", "Heat Transfer > Total heat flux, x component", "",
                 ["ht.tfluxX", "ht.tfluxx", "ht.dfluxX"]),
}

# Non-verify (stable) tags chosen by this package -- not COMSOL names.
TAGS = dict(
    comp="comp1", geom="geom1", mesh="mesh1", mat="mat1", semi="semi", ht="ht",
    dop_bg="dop_bg", dop_n="dop_n", dop_p="dop_p", srh="srh1", auger="auger1",
    mc_n="mc_n", mc_p="mc_p", mob_arora="mmal1", mob_fletcher="mmfc1",
    hs1="hs1", bhs_n="bhs_n", bhs_p="bhs_p", temp_ends="temp_ends", temp_sinkA="temp_sinkA",
    temp_sinkB="temp_sinkB", hs_lat="hs_lat",
    std_eq_iv="std_eq_iv", std_room="std_room", std_float="std_float", std_lat="std_lat",
    intop_all="intop_all", pt_n="pt_n", pt_c="pt_c", pt_p="pt_p", intop_i="intop_i",
)

# Thermal nodes active per configuration (spec §4.4, §7)
CONFIG_NODES = {
    "A": ["temp_ends", "temp_sinkA"],
    "B": ["temp_sinkB"],
    "C": ["hs_lat"],          # ends insulated (point sinks only), lateral convective sink
}
ALL_THERMAL_NODES = ["temp_ends", "temp_sinkA", "temp_sinkB", "hs_lat"]


def load_overrides(path: Path = OVERRIDE_FILE) -> dict[str, str]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    unknown = set(data) - set(VERIFY)
    if unknown:
        raise KeyError(f"{path.name}: unknown API_NAMES keys {sorted(unknown)}")
    return {k: str(v) for k, v in data.items()}


for _k, _v in load_overrides().items():
    VERIFY[_k].value = _v
    VERIFY[_k].candidates = [_v] + [c for c in VERIFY[_k].candidates if c != _v]


def name(key: str) -> str:
    """Current value of an API name (after overrides)."""
    return VERIFY[key].value


class ApiNameError(RuntimeError):
    """Raised when COMSOL rejects one of the API_NAMES."""

    def __init__(self, key: str, exc: BaseException | None = None, extra: str = ""):
        v = VERIFY.get(key)
        msg = (f"COMSOL rejected API name {key} = '{v.value if v else '?'}'. "
               f"GUI: {v.gui if v else '?'}. Verify via File > Save As > Model File for Java and "
               f"search for: {v.java_hint if v else '?'}; then set it in config/api_names_override.yaml. "
               f"See docs/VERIFY_API_NAMES.md#{key.lower()}. {extra}")
        if exc is not None:
            msg += f"\nCOMSOL said: {exc}"
        super().__init__(msg)


# Module-level aliases so builders can write api.PHYS_SEMI etc.
globals().update({k: v.value for k, v in VERIFY.items()})
