"""Exercise Driver A end to end against the COMSOL test double (no COMSOL needed).

What this does and does not prove: it executes every Python code path of the
builder and the variant driver (staged build, smoke tests, mesh-grading
assertion and flip, solver fallback, exports, CSV schema, analysis), so Python
errors cannot hide there. It cannot show that the COMSOL names in api_names.py
are right; only a real COMSOL run can, see docs/VERIFY_API_NAMES.md.
"""
import numpy as np
import pytest

import analyze as an
import build_model as bm
import run_variants as rv
from common.csvio import read_csv
from fake_comsol import FakeClient, FakeModel


@pytest.fixture(scope="module")
def ref():
    import reference_model as rm
    r = rm.run_variant("V0", {"rz_on": "0"}, write=False)
    return r.glob, r.profiles[0.7]


@pytest.fixture()
def built(ref, tmp_path):
    model = FakeModel(*ref)
    b = bm.PinPeltierBuilder(model, FakeClient(lambda: None), material_source="fallback",
                             stage_dir=tmp_path / "models")
    for st in (b.stage1, b.stage2, b.stage3, b.stage4, b.stage5, b.stage6):
        st()
    return b


def test_staged_build_smoke_tests(built):
    b = built
    assert b.material_used == "fallback" and b.mobility_base == "M2"
    assert b.names["U_TOT"] == "semi.U_tot"
    st = b.j.study("std_room")
    assert st.feature("param").getStringArray("pname") == ["dT_sink"]
    dis = st.feature("stat").getStringArray("disabledphysics")
    assert sorted(dis) == ["ht/hs_lat", "ht/temp_sinkB"]
    fl = b.j.study("std_float").feature("stat").getStringArray("disabledphysics")
    assert sorted(fl) == ["ht/hs_lat", "ht/temp_ends", "ht/temp_sinkA"]
    # one-way coupling: semiconductor temperature is the user-defined T0
    smm = b.semi.feature("smm1")
    assert smm.props["minput_temperature_src"] == "userdef" and smm.props["minput_temperature"] == "T0"
    # contact Peltier sinks
    # contact heat: spec form J*Pi (crec_on = 0) or carrier-resolved incl. minority recombination
    assert b.ht.feature("bhs_n").props["Qb_input"] == (
        "(1-crec_on)*semi.JX*Pi_nc+crec_on*(semi.JnX*Pi_nc-semi.JpX*Pi_rn)")
    assert b.ht.feature("bhs_p").props["Qb_input"] == (
        "(1-crec_on)*semi.JX*Pi_pc+crec_on*(semi.JpX*Pi_pc-semi.JnX*Pi_rp)")
    assert b.Pi[0] == pytest.approx(0.0789, abs=1e-3)
    # the equilibrium 'Solution Store' of Study 1 must not be mistaken for the sweep results
    assert "store" not in b.dataset_of("std_eq_iv")
    assert b.vf_values("std_eq_iv").size == 37
    # material groups that use T declare temperature as a model input (else 'Undefined variable T')
    semi_group = b.comp.material("mat1").propertyGroup("SemicondMaterial")
    assert semi_group.props.get("_inputs") == ["temperature"]


def test_mesh_grading_fine_at_junctions(built):
    x = built.mesh_nodes()
    p = built.model.pvals()
    h = np.diff(x)
    xm = 0.5 * (x[1:] + x[:-1])
    left = h[(xm > p["Wn"]) & (xm < p["Xc"])]
    right = h[(xm > p["Xc"]) & (xm < p["Wn"] + p["Wi"])]
    assert left[0] < left[-1] and right[-1] < right[0]
    assert left[-1] / left[0] == pytest.approx(2000, rel=1e-6)


def test_mesh_wrong_direction_is_flipped(built):
    built._dists["dis_iL"].set("reverse", True)       # wrong on purpose
    built.assert_mesh_grading()
    assert built._dists["dis_iL"].getBoolean("reverse") is False


def test_solver_fallback_segregated(built):
    built.model.fail_next["std_float"] = 1
    built.solve("std_float")
    s1 = built.j.sol("sol_std_float").feature("s1")
    assert "se1" in s1.tags() and not s1.feature("fc1")._active


def test_solver_fallback_halves_vf_step(built):
    built.model.fail_next["std_float"] = 2
    built.solve("std_float")
    assert built.j.study("std_float").feature("stat").getString("plistarr") == "range(0,0.0125,0.9)"


def test_variant_apply_and_export(built, tmp_path):
    b = built
    run = {"id": "V1", "params": {"rz_on": "1", "mesh_factor": "2"}, "configs": ["A", "B"],
           "qsrc": "corrected", "stats": "MB", "bgn": "off", "mobility": "M2", "fletcher": False}
    rv.apply_variant(b, run)
    assert b.model.pvals()["rz_on"] == 1.0
    assert b.hs_expr == "semi.Q_tot+k_B_const*T0*semi.U_tot"
    assert b.mesh_nodes().size == 2 * (400 + 600 + 600 + 400) + 1
    out = rv.export_variant(b, run, out_root=tmp_path / "res", reverse=True)
    g = read_csv(out / "global_vs_VF.csv")
    for c in ("VF", "I", "J", "P_el", "Qtot_int", "Qjn_n", "Qjn_p", "Qc_contacts", "qx_0", "qx_L",
              "T_P1", "T_P5", "T_P3", "Q_room", "eta_E", "V_ifield"):
        assert c in g.columns
    assert g.VF.iloc[-1] == pytest.approx(0.9)
    room = read_csv(out / "room_sweep.csv")
    assert set(room.columns) == {"VF", "dT_sink", "Q_room"} and room.dT_sink.nunique() == 17
    for v in (0, 0.6, 0.7, 0.75, 0.8):
        prof = read_csv(out / f"profiles_VF{v:g}.csv")
        assert list(prof.columns) == rv.PROFILE_COLS
        assert np.all(np.diff(prof.x) >= 0)
    assert (out / "reverse_bias_global.csv").exists()
    assert read_csv(out / "reverse_bias_global.csv").VF.iloc[-1] == pytest.approx(-0.5)
    # analysis machinery runs on the exported files
    vd = an.VariantData("V1", "comsol", out, glob=g, room=room,
                        run={"qsrc": "corrected", "params": run["params"]})
    m = an.metrics(vd)
    assert m["available"] and "dT_max_text" in m


def test_stage7_and_stage8(built, tmp_path, monkeypatch):
    monkeypatch.setattr(rv, "RESULTS", tmp_path / "res")
    monkeypatch.setattr(bm, "ROOT", tmp_path)
    built.stage7()
    assert (tmp_path / "results" / "_smoke" / "_stage7_smoke" / "global_vs_VF.csv").exists()
    path = built.stage8()
    assert path.name == "pin_peltier_base.mph"
    assert built.hs_expr == "semi.Q_tot"
    assert (built.stage_dir / "build_info.json").exists()


def test_auger_type_alternatives_and_fallback(built, monkeypatch):
    import api_names as api
    from fake_comsol import FakeEntity
    built.semi.feature().remove("auger1")
    monkeypatch.setattr(api.VERIFY["FEAT_AUGER"], "value", "AugerRecombination")
    monkeypatch.setattr(FakeEntity, "REJECT_TYPES", {"AugerRecombination"})
    assert built.add_auger() is True
    assert built.semi.feature("auger1").ftype == "Auger"
    built.semi.feature().remove("auger1")
    monkeypatch.setattr(FakeEntity, "REJECT_TYPES", set(api.VERIFY["FEAT_AUGER"].candidates) | {"Auger"})
    assert built.add_auger() is False
    assert "auger1" not in built.semi.tags()


def test_mobility_m1_selects_arora_by_variable(built):
    built.material_used = "library"
    built.set_mobility("M1", fletcher=False)
    smm = built.semi.feature("smm1")
    assert smm.props["mun_mat"] == "root.comp1.semi.mun_ar"
    built.set_mobility("M1", fletcher=True)
    assert smm.props["mun_mat"] == "root.comp1.semi.mun_fl"
    assert smm.feature("mmfc1").props["mun_in_src"] == "root.comp1.semi.mun_ar"
