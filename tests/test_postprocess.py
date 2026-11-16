"""Post-processing formulas on synthetic data (spec §8, §10) and config consistency."""
import numpy as np
import pandas as pd
import pytest

import analyze as an
import cascade_calculator as cc
from common.params import K_B, Q_E, evaluate_params, expand_variants, parse_range


# ------------------------------------------------------------ formulas
def test_q_room_formula():
    Ac, J, Pn, Pp = 1e-6, 1000.0, 0.08, 0.08
    # no conduction: room supplies exactly the contact Peltier heat
    assert an.q_room(0.0, 0.0, J, Ac, Pn, Pp) == pytest.approx(Ac * J * 0.16)
    # heat conducted into the room at both ends (qx_0 < 0, qx_L > 0) reduces Q_room
    assert an.q_room(-50.0, 50.0, J, Ac, Pn, Pp) == pytest.approx(Ac * (J * 0.16 - 100.0))
    assert an.q_room(0.0, 0.0, -J, Ac, Pn, Pp) == pytest.approx(Ac * J * 0.16)  # |J|


def test_dTmax_interpolation_linear():
    d = parse_range("range(-0.02,0.0025,0.02)")
    q = 2e-4 - 0.6 * d          # zero at 0.333 mK
    r = an.dT_max_from_curve(d, q)
    assert r.status == "interpolated"
    assert r.value == pytest.approx(2e-4 / 0.6, rel=1e-9)


def test_dTmax_room_heated():
    d = parse_range("range(-0.02,0.0025,0.02)")
    r = an.dT_max_from_curve(d, -1e-5 - 0.6 * d)
    assert r.value is None and r.status == "none (room heated)"
    assert r.text() == "none (room heated)"


def test_dTmax_extrapolated_beyond_sweep():
    d = parse_range("range(-0.02,0.0025,0.02)")
    r = an.dT_max_from_curve(d, 0.03 - 0.6 * d)  # zero at 50 mK, outside +-20 mK
    assert r.status == "extrapolated"
    assert r.value == pytest.approx(0.05, rel=1e-9)


def test_cop_and_eta():
    assert an.cop(1e-3, 1e-2, 0.5) == pytest.approx(0.2)
    assert np.isnan(an.cop(1e-3, 0.0, 0.5))
    assert an.eta_E(0.95, 0.01, 2.0, 0.5) == pytest.approx(0.96)
    vt = K_B * 300 / Q_E
    assert an.eta_E_expected(0.7) == pytest.approx(1 - vt / 0.7)
    assert 0.95 < an.eta_E_expected(0.6) < 0.97


def test_dTmax_vs_VF_table():
    d = parse_range("range(-0.02,0.0025,0.02)")
    rows = [dict(VF=v, dT_sink=x, Q_room=(v - 0.6) * 1e-3 - 0.6 * x) for v in (0.6, 0.7) for x in d]
    tab = an.dT_max_vs_VF(pd.DataFrame(rows))
    assert tab.loc[tab.VF == 0.7, "dT_max"].iloc[0] == pytest.approx(1e-4 / 0.6)
    assert tab.loc[tab.VF == 0.7, "Q_room_half"].iloc[0] == pytest.approx(0.5e-4)


# ------------------------------------------------------------ checks on synthetic data
def _synthetic(vid="V0", d_eta=0.0, qjn=-1e-4, qsrc="builtin"):
    """d_eta = offset of eta_E from the builtin expectation 1 - Vt/VF."""
    p = evaluate_params()
    VF = parse_range("range(0,0.0125,0.5)")
    Vt = K_B * 300 / Q_E
    J = Q_E * an.NI_C4 * np.exp(VF / (2 * Vt)) * p["Wi"] / (2 * p["tau_long"]) + an.emitter_leakage(p, VF)
    J[0] = 0.0
    I = J * p["Ac"]
    with np.errstate(divide="ignore"):
        eta = np.where(VF > 0, an.eta_E_expected(VF, 300.0, "builtin") + d_eta, np.nan)
    g = pd.DataFrame(dict(VF=VF, I=I, J=J, P_el=I * VF, eta_E=eta,
                          Qjn_n=np.where(VF > 0, qjn, 0.0), Qjn_p=np.where(VF > 0, qjn, 0.0),
                          T_P1=300.0, T_P5=300.0))
    return an.VariantData(vid, "comsol", an.RESULTS / vid, glob=g, run={"qsrc": qsrc, "params": {}})


def test_C2_pass_and_fail():
    assert an.check_C2(_synthetic(d_eta=0.01)).status == "PASS"
    assert an.check_C2(_synthetic(d_eta=0.06)).status == "FAIL"          # eta_E ~ 1 with the builtin source
    vd = _synthetic(qsrc="corrected")
    vd.glob["eta_E"] = np.where(vd.glob.VF > 0, 1.0, np.nan)
    assert an.check_C2(vd).status == "PASS"


def test_C3():
    assert an.check_C3(_synthetic(qjn=-1e-5)).status == "PASS"
    assert an.check_C3(_synthetic(qjn=+1e-5)).status == "FAIL"


def test_C5_benchmark_passes_on_formula():
    assert an.check_C5(_synthetic()).status == "PASS"


def test_C7_flags_bug():
    ok = [dict(variant="V1", source="comsol", available=True, dT_max=5e-3, dT_end_B=-5e-3)]
    bad = [dict(variant="V1", source="comsol", available=True, dT_max=0.15, dT_end_B=-0.15)]
    assert an.check_C7(ok).status == "PASS"
    assert an.check_C7(bad).status == "BUG"


def test_C1_zero_bias():
    x = np.linspace(0, 1e-3, 11)
    vd = _synthetic()
    vd.profiles = {0.0: pd.DataFrame(dict(x=x, Q_tot=0.0 * x, T=300.0 + 0 * x)),
                   an.VF_REPORT: pd.DataFrame(dict(x=x, Q_tot=1e6 + 0 * x, T=300.0 + 0 * x))}
    assert an.check_C1(vd).status == "PASS"
    vd.profiles[0.0]["T"] = 300.0 + 1e-5
    assert an.check_C1(vd).status == "FAIL"


def test_C4_magnitude():
    p = evaluate_params()
    vd = _synthetic()
    g = vd.glob
    Vt = K_B * 300 / Q_E
    Vbi = Vt * np.log(p["Nd_p"] * p["Na_p"] / an.NI_C4 ** 2)
    g["Vj"] = g.VF - 0.05
    g["Qjn_n"] = g["Qjn_p"] = -0.5 * g.I * (Vbi - (g.VF - 0.05))
    assert an.check_C4(vd).status == "PASS"
    g["Qjn_n"] = g["Qjn_p"] = -0.25 * g.I * (Vbi - (g.VF - 0.05))
    assert an.check_C4(vd).status == "FAIL"


# ------------------------------------------------------------ configuration consistency
def test_material_is_germanium():
    from common.params import material
    m = material()
    assert m["name"] == "Ge" and m["Eg_eV"] == pytest.approx(0.661)
    assert m["ni"] * 1e-6 == pytest.approx(2.0e13, rel=0.05)     # literature n_i of Ge at 300 K
    assert (m["mun"] * 1e4, m["mup"] * 1e4) == pytest.approx((3900.0, 1900.0))


def test_params_values_germanium():
    p = evaluate_params()
    assert p["Ltot"] == pytest.approx(1.004e-3)
    assert p["Xc"] == pytest.approx(0.502e-3)
    assert p["Pi_nc"] == pytest.approx(0.0517, abs=1e-3)      # Ge, Nd = Nc
    assert p["Pi_pc"] == pytest.approx(0.0338, abs=1e-3)      # Ge, Na = 2 Nv
    assert p["Cn_aug"] + p["Cp_aug"] == pytest.approx(1e-42)  # Ge, 1e-30 cm^6/s
    assert p["k_th"] == pytest.approx(60.0)
    assert p["Ac"] == pytest.approx(1e-6)


def test_params_txt_in_sync():
    import write_params_txt as w
    assert w.PARAMS_TXT.read_text(encoding="utf-8") == w.params_txt_text()
    assert w.VARIANTS_FLAT.read_text(encoding="utf-8") == w.variants_flat_text()


def test_variant_expansion_counts():
    ids = [r["id"] for r in expand_variants("full")]
    assert sum(i.startswith("V5_") for i in ids) == 12
    assert sum(i.startswith("V6_") for i in ids) == 12
    assert sum(i.startswith("V7a_") for i in ids) == 9
    assert [r["id"] for r in expand_variants("core")] == ["V0", "V1"]
    v4 = next(r for r in expand_variants("full") if r["id"] == "V4")
    assert v4["params"] == {"rz_on": "1", "mesh_factor": "2"}


def test_api_names_all_verify_items_documented():
    import api_names
    from pathlib import Path
    doc = (Path(an.ROOT) / "docs" / "VERIFY_API_NAMES.md").read_text(encoding="utf-8")
    for name in api_names.VERIFY:
        assert f"`{name}`" in doc, f"{name} missing from docs/VERIFY_API_NAMES.md"


# ------------------------------------------------------------ cascade
def test_cascade_numbers():
    r = cc.compute(cc.CascadeInputs())
    assert r["N_stages"] == 200                                    # 10 K / 50 mK
    assert r["log10_power_multiplier"] == pytest.approx(200 * np.log10(3.0))   # COP = 0.5
    assert r["dT_interface"] == pytest.approx(1e-5 * cc.DEFAULT_QFLUX)
    assert r["parallel_dT"] == 5e-2
