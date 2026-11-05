import math
from pathlib import Path

import pytest

from gps_tof.model import Problem, Baseline, OpeningAngle
from gps_tof.calc import compute_all, compute_baseline, compute_opening_angle, axis_frame, point_vs_axis, direction_vs_axis, site_point, final_stage
from gps_tof.geodesy import vsub, norm, dot
from gps_tof.config import load_yaml
from gps_tof import cli

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def nova():
    return Problem.from_dict(load_yaml(ROOT / "config" / "nova.yaml"))


def test_axis_frame_is_orthonormal_and_points_at_soudan(nova):
    f = axis_frame(nova)
    assert f["origin_id"] == "target" and f["through_id"] == "minos-fd"
    for a in ("u", "h", "v"):
        assert norm(f[a]) == pytest.approx(1.0, abs=1e-12)
    assert abs(dot(f["u"], f["h"])) < 1e-12 and abs(dot(f["u"], f["v"])) < 1e-12 and abs(dot(f["h"], f["v"])) < 1e-12
    assert f["azimuth_at_origin_deg"] == pytest.approx(336.094, abs=0.001)
    assert f["elevation_at_origin_deg"] == pytest.approx(-3.3406, abs=0.001)
    assert f["length_m"] == pytest.approx(735344.6, abs=0.1)


def test_sites_relative_to_axis(nova):
    r = compute_all(nova)
    by = {s["id"]: s["vs_axis"] for s in r["sites"]}
    assert by["target"]["off_axis_mrad"] == 0.0 and by["target"]["along_axis_m"] == 0.0
    assert by["minos-fd"]["off_axis_mrad"] == pytest.approx(0.0, abs=1e-9)
    assert by["minos-fd"]["transverse_m"] == pytest.approx(0.0, abs=1e-6)
    assert by["minos-fd"]["clock_angle_deg"] is None
    assert by["minos-fd"]["along_axis_m"] == pytest.approx(735344.6, abs=0.1)
    fd = by["fd2"]
    assert fd["off_axis_mrad"] == pytest.approx(14.575, abs=0.002)
    assert math.hypot(fd["transverse_right_m"], fd["transverse_up_m"]) == pytest.approx(fd["transverse_m"])
    assert math.hypot(fd["along_axis_m"], fd["transverse_m"]) == pytest.approx(fd["distance_from_origin_m"])
    assert fd["transverse_right_m"] < 0 and fd["transverse_up_m"] < 0     # Ash River is left of and below the Soudan line
    assert fd["transverse_m"] == pytest.approx(11814, abs=2)             # "12 km west of the beam axis"
    assert by["decay-end"]["off_axis_mrad"] < 0.05                       # TDR design axis agrees with target -> MINOS FD
    assert by["nd"]["off_axis_mrad"] == pytest.approx(13.34, abs=0.01)


def test_baseline_reports_chord_vs_axis(nova):
    b = compute_baseline(nova, Baseline("target", "fd2"))
    bx = b["beam_axis"]
    assert bx["chord_vs_axis"]["angle_mrad"] == pytest.approx(bx["target"]["off_axis_mrad"], rel=1e-9)   # chord from the origin
    assert math.hypot(bx["chord_vs_axis"]["right_component_mrad"], bx["chord_vs_axis"]["up_component_mrad"]) == pytest.approx(bx["chord_vs_axis"]["angle_mrad"], rel=1e-4)
    b2 = compute_baseline(nova, Baseline("nd", "fd2"))
    assert b2["beam_axis"]["chord_vs_axis"]["angle_mrad"] == pytest.approx(14.58, abs=0.01)
    b3 = compute_baseline(nova, Baseline("target", "minos-fd"))
    assert b3["beam_axis"]["chord_vs_axis"]["angle_mrad"] == pytest.approx(0.0, abs=1e-9)


def test_opening_angle_uses_global_axis(nova):
    oa = compute_opening_angle(nova, OpeningAngle("target", "nd", "fd2"))
    bx = oa["beam_axis"]
    assert bx["a"]["off_axis_mrad"] == pytest.approx(13.34, abs=0.01)
    assert bx["b"]["off_axis_mrad"] == pytest.approx(14.575, abs=0.002)
    assert bx["a_chord_vs_axis"]["angle_mrad"] == pytest.approx(bx["a"]["off_axis_mrad"], rel=1e-9)


def test_axis_cli_and_no_axis(capsys):
    cfg = str(ROOT / "config" / "nova.yaml")
    assert cli.main(["-c", cfg, "-p", "target:fd2", "--no-sensitivities", "--no-axis", "--format", "json"]) == 0
    import json
    r = json.loads(capsys.readouterr().out)
    assert r["beam_axis"] is None and r["baselines"][0]["beam_axis"] is None and "vs_axis" not in r["sites"][0]
    assert cli.main(["-c", cfg, "-p", "target:fd2", "--no-sensitivities", "-x", "target:decay-end:TDR axis", "--format", "md"]) == 0
    out = capsys.readouterr().out
    assert "## Beam axis: TDR axis" in out and "chord vs axis (mrad)" not in out   # single baseline: no summary table
    assert "opening angle chord vs beam axis (TDR axis)" in out


def test_axis_validation():
    with pytest.raises(ValueError):
        Problem.from_dict({"sites": [{"name": "A", "id": "a", "lat": 0, "lon": 0}, {"name": "B", "id": "b", "lat": 1, "lon": 1}],
                           "beam_axis": {"from": "a", "to": "a"}})
    with pytest.raises(KeyError):
        Problem.from_dict({"sites": [{"name": "A", "id": "a", "lat": 0, "lon": 0}, {"name": "B", "id": "b", "lat": 1, "lon": 1}],
                           "beam_axis": {"from": "a", "to": "zz"}})
