import math
from pathlib import Path

import pytest

from gps_tof.model import Problem, OpeningAngle
from gps_tof.calc import compute_opening_angle, compute_all, site_point, final_stage
from gps_tof.geodesy import vsub, angle_between, norm
from gps_tof.config import load_yaml, parse_angle_spec
from gps_tof import cli

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def nova():
    return Problem.from_dict(load_yaml(ROOT / "config" / "nova.yaml"))


def test_opening_angle_matches_vector_angle_and_is_symmetric(nova):
    oa = compute_opening_angle(nova, OpeningAngle("target", "nd-1015", "fd2"))
    s = nova.settings
    st = final_stage(s)
    pv, pa, pb = (site_point(nova.site(k), s, st) for k in ("target", "nd-1015", "fd2"))
    assert oa["angle_rad"] == pytest.approx(angle_between(vsub(pa, pv), vsub(pb, pv)), rel=1e-12)
    ob = compute_opening_angle(nova, OpeningAngle("target", "fd2", "nd-1015"))
    assert ob["angle_rad"] == pytest.approx(oa["angle_rad"], rel=1e-12)
    assert ob["dL_m"] == pytest.approx(-oa["dL_m"], rel=1e-12)
    # components: the total angle is the quadrature sum of the horizontal and vertical parts (small angles)
    assert math.hypot(oa["horizontal_component_mrad"], oa["vertical_component_mrad"]) == pytest.approx(oa["angle_mrad"], rel=1e-4)
    assert oa["a_transverse_from_vb_m"] == pytest.approx(oa["L_a_m"] * math.sin(oa["angle_rad"]))
    assert oa["L_a_m"] == pytest.approx(1015.08, abs=0.05) and oa["L_b_m"] == pytest.approx(810564.6, abs=0.1)


def test_nova_target_opening_angle_value(nova):
    oa = compute_opening_angle(nova, OpeningAngle("target", "nd-1015", "fd2", axis_to="decay-end"))
    assert oa["angle_mrad"] == pytest.approx(10.44, abs=0.01)
    assert oa["vertical_component_mrad"] == pytest.approx(-10.20, abs=0.01)
    assert oa["horizontal_component_mrad"] == pytest.approx(-2.24, abs=0.01)
    assert oa["a_transverse_from_vb_m"] == pytest.approx(1015.08 * math.sin(10.4403e-3), abs=0.02)
    assert oa["off_axis_a_mrad"] == pytest.approx(12.47, abs=0.03)   # local axis target -> decay-end
    assert oa["off_axis_b_mrad"] == pytest.approx(14.58, abs=0.01)
    assert oa["same_side_of_axis"] is True


def test_surveyed_nd_and_fd_opening_angle(nova):
    """With both surveyed faces the ND lies almost on the target -> FD line."""
    oa = compute_opening_angle(nova, OpeningAngle("target", "nd", "fd"))
    assert oa["angle_mrad"] == pytest.approx(2.474, abs=0.005)
    assert oa["horizontal_component_mrad"] == pytest.approx(-1.99, abs=0.01)
    assert oa["vertical_component_mrad"] == pytest.approx(-1.47, abs=0.01)
    assert oa["a_transverse_from_vb_m"] == pytest.approx(2.46, abs=0.01)
    assert oa["L_a_m"] == pytest.approx(994.424, abs=0.005) and oa["L_b_m"] == pytest.approx(810509.171, abs=0.005)


def test_collinear_points_have_zero_opening_angle():
    p = Problem.from_dict({"sites": [
        {"name": "V", "id": "v", "lat": 0.0, "lon": 0.0, "height_m": 0.0},
        {"name": "A", "id": "a", "lat": 0.0, "lon": 0.0, "height_m": 1000.0},
        {"name": "B", "id": "b", "lat": 0.0, "lon": 0.0, "height_m": 5000.0}]})
    oa = compute_opening_angle(p, OpeningAngle("v", "a", "b"))
    assert oa["angle_mrad"] == pytest.approx(0.0, abs=1e-9)
    assert oa["path_via_a_minus_direct_m"] == pytest.approx(0.0, abs=1e-6)
    assert oa["dL_m"] == pytest.approx(4000.0, abs=1e-6)


def test_config_and_cli_angles(nova, capsys):
    assert len(nova.opening_angles) == 7
    r = compute_all(nova)
    assert [x["label"] for x in r["opening_angles"]] == [x.label for x in nova.opening_angles]
    assert parse_angle_spec("target:nd:fd2:lbl:decay-end") == {"vertex": "target", "a": "nd", "b": "fd2", "label": "lbl", "axis_to": "decay-end"}
    with pytest.raises(ValueError):
        parse_angle_spec("target:nd")
    rc = cli.main(["-c", str(ROOT / "config" / "nova.yaml"), "-p", "target:nd", "-a", "target:nd-1015:fd2", "--format", "md", "--no-sensitivities"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "## Opening angles" in out and "10.44" in out
