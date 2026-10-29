"""Analytic-limit tests of the COMSOL-independent reference model (spec §11.5)."""
import numpy as np
import pytest
from scipy.integrate import trapezoid

import reference_model as rm
from common.params import Q_E, evaluate_params


@pytest.fixture(scope="module")
def params():
    return evaluate_params()


def device(params, **kw):
    return rm.RefDevice.from_params(params, **kw)


@pytest.mark.parametrize("convention", list(rm.LIFETIME_CONVENTIONS))
def test_uniform_tau_no_auger_matches_cosh(params, convention):
    """n = n_b cosh((x-W/2)/L_a)/cosh(W/2L_a) within 1 % (n >> n_i, so the -n_i shift is negligible)."""
    dev = device(params, auger=False, tau_uniform=params["tau_long"], convention=convention)
    Vj = 0.6
    bp = rm.bias_point(dev, Vj)
    La = np.sqrt(dev.Da * dev.s * dev.tau_uniform)
    nb = dev.n_boundary(Vj)
    W = dev.Wi
    n_exact = dev.ni + (nb - dev.ni) * np.cosh((bp.x - W / 2) / La) / np.cosh(W / (2 * La))
    assert np.max(np.abs(bp.n / n_exact - 1)) < 0.01


def test_uniform_tau_short_lifetime_strong_curvature(params):
    """Same test with L_a << W_i (tau = 1 us), where the profile is far from flat."""
    dev = device(params, auger=False, tau_uniform=1e-6)
    bp = rm.bias_point(dev, 0.6)
    La = np.sqrt(dev.Da * dev.s * 1e-6)
    nb = dev.n_boundary(0.6)
    n_exact = dev.ni + (nb - dev.ni) * np.cosh((bp.x - dev.Wi / 2) / La) / np.cosh(dev.Wi / (2 * La))
    mask = n_exact > 1e3 * dev.ni
    assert np.max(np.abs(bp.n[mask] / n_exact[mask] - 1)) < 0.01


@pytest.mark.parametrize("rz_on", [0.0, 1.0])
def test_zero_bias_no_current_no_heating(params, rz_on):
    p = dict(params, rz_on=rz_on)
    dev = device(p)
    bp = rm.bias_point(dev, 0.0)
    assert bp.J == pytest.approx(0.0, abs=1e-15)
    TB, qB = rm._heat_config_B(dev, bp)
    TA, qA, *_ = rm._heat_config_A(dev, bp, 0.0)
    assert np.max(np.abs(TB - dev.T_room)) < 1e-12
    assert np.max(np.abs(TA - dev.T_room)) < 1e-12


@pytest.mark.parametrize("rz_on,Vj", [(0.0, 0.6), (0.0, 0.75), (1.0, 0.6), (1.0, 0.75)])
def test_energy_balance_closes(params, rz_on, Vj):
    """Total heat delivered to all reservoirs equals J*VF within 0.5 %."""
    dev = device(dict(params, rz_on=rz_on))
    bp = rm.bias_point(dev, Vj)
    P = bp.J * bp.VF                                   # W/m^2
    # bookkeeping: distributed heat + both end sinks
    assert (trapezoid(bp.H, bp.x) + 2 * bp.Q_b) == pytest.approx(P, rel=5e-3)
    # thermal solution, Config A: reservoirs at both ends + centre sink
    T, qx, qx0, qxL, Q_room, q_centre = rm._heat_config_A(dev, bp, 0.0)
    total = q_centre + (bp.Q_b - qx0) + (bp.Q_b + qxL)
    assert total == pytest.approx(P, rel=5e-3)
    assert -Q_room / dev.Ac + q_centre == pytest.approx(P, rel=5e-3)


def test_rect_lifetime(params):
    dev = device(dict(params, rz_on=1.0))
    xc = dev.x_centre
    t_in = 1 / (1 / dev.tau_long + 1 / dev.tau_short)
    assert dev.tau(np.array([xc]))[0] == pytest.approx(t_in, rel=1e-12)
    assert dev.tau(np.array([0.0]))[0] == pytest.approx(dev.tau_long, rel=1e-12)
    # half value at the nominal rectangle edge
    r_edge = rm.rect(np.array([xc + dev.w_rz / 2]), xc - dev.w_rz / 2, xc + dev.w_rz / 2)[0]
    assert r_edge == pytest.approx(0.5, abs=1e-12)


def test_ambipolar_diffusivity(params):
    dev = device(params)
    assert dev.Da * 1e4 == pytest.approx(18.25, abs=0.2)   # ~18 cm^2/s (spec §11.1)


def test_configA_dTmax_equals_configB_end_drop(params):
    """Symmetric bar: dT_sink at Q_room = 0 (Config A) equals T_room - T_end (Config B)."""
    dev = device(dict(params, rz_on=1.0))
    bp = rm.bias_point(dev, 0.65)
    *_, Q0, _ = rm._heat_config_A(dev, bp, 0.0)
    dTmax = -Q0 / rm.room_slope(dev)
    TB, _ = rm._heat_config_B(dev, bp)
    assert dTmax == pytest.approx(dev.T_room - TB[0], rel=1e-6)
    *_, Qz, _ = rm._heat_config_A(dev, bp, dTmax)
    assert abs(Qz) < 1e-9 * abs(Q0)


def test_uniform_lifetime_heats_ends_rz_cools_ends(params):
    """Spec §1 key outcomes: uniform tau -> ends warmer; engineered zone -> ends cooler, mK scale."""
    for rz, sign in ((0.0, +1), (1.0, -1)):
        dev = device(dict(params, rz_on=rz))
        bp = rm.bias_point(dev, 0.75)
        TB, _ = rm._heat_config_B(dev, bp)
        dT = TB[0] - dev.T_room
        assert np.sign(dT) == sign
        assert abs(dT) < 0.1          # plausibility (C7)


def test_iv_monotonic(params):
    dev = device(dict(params, rz_on=1.0))
    pts = rm.sweep_Vj(dev, Vj_max=0.8, dVj=0.05)
    J = np.array([p.J for p in pts])
    VF = np.array([p.VF for p in pts])
    assert np.all(np.diff(J) > 0) and np.all(np.diff(VF) > 0)


def test_solve_at_VF_hits_target(params):
    dev = device(params)
    pts = rm.sweep_Vj(dev, Vj_max=0.8, dVj=0.05)
    bp = rm.solve_at_VF(dev, 0.7, pts)
    assert bp.VF == pytest.approx(0.7, abs=1e-6)


def test_analytic_bound(params):
    dev = device(params)
    b = rm.analytic_bound(dev, 0.7)
    assert b["n_b_auger"] == pytest.approx(2 / dev.Wi * np.sqrt(dev.Da / dev.Ca))
    assert 0 < b["dT_bound"] <= b["dT_bound_auger"]
    Pi_side = (dev.Eg_eV + 3 * dev.Vt - 0.7) / 2 * Q_E
    assert b["dT_bound"] == pytest.approx(min(b["n_b"], b["n_b_auger"]) * dev.Da * Pi_side / dev.k)
    assert b["dT_bound"] < 0.1      # milli-kelvin scale


def test_thermophotonic_stub():
    assert rm.thermophotonic_cop(0.9, 1.4, 1.2) == pytest.approx(0.9 * 1.4 - 1.2)
    assert rm.thermophotonic_cools(0.9, 1.4, 1.2)          # 0.9 > 0.857
    assert not rm.thermophotonic_cools(0.8, 1.4, 1.2)      # 0.8 < 0.857
    assert not rm.thermophotonic_cools(1e-3, 1.12, 0.7)    # Si-like EQE
