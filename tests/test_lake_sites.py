import math
from pathlib import Path

import pytest

from gps_tof.model import Problem, Baseline
from gps_tof.calc import compute_baseline, compute_all
from gps_tof.config import load_yaml
from gps_tof.angles import parse_angle

ROOT = Path(__file__).resolve().parents[1]
FT = 0.3048


@pytest.fixture(scope="module")
def nova():
    return Problem.from_dict(load_yaml(ROOT / "config" / "nova.yaml"))


def test_lake_sites_inputs(nova):
    v, t = nova.site("vermilion"), nova.site("two-harbors")
    assert v.lat == pytest.approx(parse_angle("47 50 49.43 N")) and v.lon == pytest.approx(parse_angle("92 17 46.34 W"))
    assert t.lat == pytest.approx(parse_angle("46 59 55.2 N")) and t.lon == pytest.approx(parse_angle("91 38 16.65 W"))
    # 100 ft below the lake surfaces: 1358 ft and 601.1 ft
    assert v.height_m == pytest.approx((1358 - 100) * FT, abs=0.01)
    assert t.height_m == pytest.approx((601.1 - 100) * FT, abs=0.01)
    assert v.datum == "msl" and t.datum == "msl"
    assert v.h_ellipsoidal == pytest.approx(v.height_m - 30.892) and t.h_ellipsoidal == pytest.approx(t.height_m - 29.103)


def test_lake_ledgers_show_the_datum_step(nova):
    b = compute_baseline(nova, Baseline("target", "vermilion"))
    steps = [(l["step"], l["site"]) for l in b["ledger"]]
    assert steps == [("reference model", None), ("Earth model", None), ("height datum", "vermilion")]
    # lowering the far end by |N_g| shortens the chord by about |N_g| sin(dip)
    dip = math.radians(-b["geometry"]["elevation_at_source_deg"])
    assert b["ledger"][-1]["dL_m"] == pytest.approx(-30.892 * math.sin(dip), rel=0.05)
    assert b["ledger"][-1]["L_m"] == pytest.approx(b["result"]["L_m"], abs=1e-6)


def test_lake_geometry_is_sensible(nova):
    r = compute_all(nova)
    by = {s["id"]: s["vs_axis"] for s in r["sites"]}
    # Lake Vermilion is a few km past Soudan, 2.3 km left of the axis; Two Harbors lies almost exactly in the
    # vertical plane of the axis (19 m right), 5.4 km above the extended axis line, 633 km along
    assert by["vermilion"]["along_axis_m"] == pytest.approx(739878, abs=5)
    assert by["vermilion"]["transverse_right_m"] == pytest.approx(-2323, abs=5)
    assert by["vermilion"]["off_axis_mrad"] == pytest.approx(3.174, abs=0.01)
    assert abs(by["two-harbors"]["transverse_right_m"]) < 50
    assert by["two-harbors"]["transverse_up_m"] == pytest.approx(5388, abs=5)
    assert by["two-harbors"]["off_axis_mrad"] == pytest.approx(8.507, abs=0.01)
    assert by["two-harbors"]["along_axis_m"] < by["vermilion"]["along_axis_m"]
    tv = compute_baseline(nova, Baseline("target", "vermilion"))["result"]
    tt = compute_baseline(nova, Baseline("target", "two-harbors"))["result"]
    assert tv["t_us"] == pytest.approx(tv["L_m"] / 299792458.0 * 1e6, rel=1e-12)
    assert tt["L_m"] < tv["L_m"]
