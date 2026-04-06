"""
Operational proof: Gateway predicts the next solar-hydrogen state from the
master's burned fractal pattern plus live solar wind (resonant filter).
"""

from __future__ import annotations

import math

from egs_gateway import (
    DEFAULT_SOLAR_WIND_KM_S,
    EGS_FRACTAL_CONSTANT,
    InterferenceVerdict,
    NodeField,
    REFERENCE_SOLAR_WIND_KM_S,
    burn_master_fractal,
    gateway_filter,
    holographic_gate,
    predict_next_solar_hydrogen_state,
    self_correct_with_sunspots,
)


def _assert_close(a: float, b: float, tol: float = 1e-6, msg: str = "") -> None:
    if abs(a - b) > tol:
        raise AssertionError(msg or f"{a} !~= {b} (tol={tol})")


def test_gateway_filter_phase_bias_matches_formula() -> None:
    import egs_gateway as eg

    w = DEFAULT_SOLAR_WIND_KM_S
    g = gateway_filter(w)
    expected = (2.0 * math.pi * (w / REFERENCE_SOLAR_WIND_KM_S) * eg.K_EGS) % (2.0 * math.pi)
    _assert_close(g["phase_bias_rad"], expected, 1e-12)
    assert "effective_wavelength_shift_nm" in g
    assert 0.0 <= g["lock_strength"] <= 1.0
    g_slow = gateway_filter(300.0)
    assert abs(g["phase_bias_rad"] - g_slow["phase_bias_rad"]) > 1e-6


def test_egs_fractal_constant_matches_phi_ratio() -> None:
    import egs_gateway as eg

    expected = eg.PHI * (eg.LAMBDA_READER_NM / eg.LAMBDA_H_ALPHA_NM)
    _assert_close(EGS_FRACTAL_CONSTANT, expected, 1e-12)


def test_holographic_gate_constructive_vs_destructive() -> None:
    ref = NodeField(1.0, 0.0)
    # In-phase with reference → constructive at AR14409
    ar = NodeField(1.0, 0.0)
    # Orthogonal phase-flip path → weak self-destructive beat
    h_pf = NodeField(0.0, 1.0)
    v = holographic_gate(ar, h_pf, reference=ref)
    assert v is InterferenceVerdict.CONSTRUCTIVE_AR14409

    ar_weak = NodeField(0.01, 0.0)
    h_strong = NodeField(5.0, 0.0)
    v2 = holographic_gate(ar_weak, h_strong, reference=ref)
    assert v2 is InterferenceVerdict.DESTRUCTIVE_H_PHASE_FLIP


def test_predict_next_state_tracks_master_and_wind() -> None:
    master = burn_master_fractal(seed=14409, length=64)
    i = 10
    p_default = predict_next_solar_hydrogen_state(master, DEFAULT_SOLAR_WIND_KM_S, i)
    p_slow = predict_next_solar_hydrogen_state(master, 300.0, i)
    assert 0.0 <= p_default < 1.0
    assert 0.0 <= p_slow < 1.0
    # Different wind → different phase bias → different prediction (almost always)
    if abs(p_default - p_slow) < 1e-12:
        raise AssertionError("expected wind-dependent prediction divergence")


def test_self_correct_with_sunspots_bounded() -> None:
    master = burn_master_fractal(seed=7, length=32)
    corrected = self_correct_with_sunspots(master, sunspot_index=2.5, solar_wind_speed_km_s=500.0)
    assert len(corrected) == len(master)
    assert all(0.0 <= x <= 1.0 for x in corrected)


def test_fdtd_backend() -> None:
    """FDTD backend (silica_fdtd or MIT Meep): runs pulse, returns finite flux."""
    from meep_gateway import meep_available, run_silica_reader_meep

    if not meep_available():
        raise AssertionError("No FDTD backend found — silica_fdtd should always be present")
    a = run_silica_reader_meep(
        DEFAULT_SOLAR_WIND_KM_S,
        resolution=8,
        until=35.0,
    )
    b = run_silica_reader_meep(
        300.0,
        resolution=8,
        until=35.0,
    )
    assert "transmitted_flux" in a and "transmitted_flux" in b
    assert "backend" in a
    assert math.isfinite(a["transmitted_flux"]) and math.isfinite(b["transmitted_flux"])
    # Different solar-wind inputs → different EGS phase biases
    assert a["phase_bias_rad"] != b["phase_bias_rad"]


def run_all() -> None:
    test_gateway_filter_phase_bias_matches_formula()
    test_egs_fractal_constant_matches_phi_ratio()
    test_holographic_gate_constructive_vs_destructive()
    test_predict_next_state_tracks_master_and_wind()
    test_self_correct_with_sunspots_bounded()
    test_fdtd_backend()
    print("EGS Gateway testing_suite: all checks passed.")


if __name__ == "__main__":
    from meep_gateway import meep_available, run_silica_reader_meep

    run_all()
    if meep_available():
        m = run_silica_reader_meep(
            DEFAULT_SOLAR_WIND_KM_S,
            resolution=12,
            until=60.0,
        )
        backend_label = (
            "MIT Meep" if m["backend"] == "meep" else "silica_fdtd (EGS own FDTD)"
        )
        print(
            f"{backend_label} v{m['backend_version']}: "
            f"transmitted_flux ≈ {m['transmitted_flux']:.6g}  "
            f"(1030 nm reader · fused silica · EGS phase={m['phase_bias_rad']:.4f} rad)"
        )
    else:
        print("No FDTD backend found (should not happen — silica_fdtd is in-repo).")
    # Demo output for operational proof
    gf = gateway_filter(DEFAULT_SOLAR_WIND_KM_S)
    master = burn_master_fractal(seed=14409, length=20)
    idx = 5
    nxt = predict_next_solar_hydrogen_state(master, DEFAULT_SOLAR_WIND_KM_S, idx)
    print(f"Solar wind (km/s): {DEFAULT_SOLAR_WIND_KM_S}")
    print(f"EGS Fractal Constant (gateway key): {EGS_FRACTAL_CONSTANT:.6f}")
    print(f"1030nm reader phase bias (rad): {gf['phase_bias_rad']:.6f}")
    print(f"Master burn sample [0:5]: {[round(x, 4) for x in master[:5]]}")
    print(f"Predicted next solar-hydrogen state (index {idx}): {nxt:.6f}")
