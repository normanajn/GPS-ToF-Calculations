import math
from pathlib import Path

import pytest

from gps_tof.model import Problem, OpeningAngle
from gps_tof.calc import compute_all, compute_face, compute_opening_angle, frame_from_sites, point_vs_axis, site_point, final_stage
from gps_tof.config import load_yaml

ROOT = Path(__file__).resolve().parents[1]
HW = 2.0081875   # 79.0625 in


@pytest.fixture(scope="module")
def nova():
    return Problem.from_dict(load_yaml(ROOT / "config" / "nova.yaml"))


def test_edge_sites_are_derived_in_the_survey_frame(nova):
    ids = {s.id for s in nova.sites}
    assert {"nd-left", "nd-right", "nd-top", "nd-bottom", "fd-left", "fd-right", "fd-top", "fd-bottom"} <= ids
    f = frame_from_sites(nova, nova.site("mczero"), nova.site("minos-fd"))
    st = final_stage(nova.settings)
    for edge, dr, du in (("left", -HW, 0.0), ("right", +HW, 0.0), ("top", 0.0, +HW), ("bottom", 0.0, -HW)):
        va = point_vs_axis(site_point(nova.site("nd-" + edge), nova.settings, st), f)
        assert va["along_axis_m"] == pytest.approx(993.350283, abs=1e-6)
        assert va["transverse_right_m"] == pytest.approx(-11.565 + dr, abs=1e-6)
        assert va["transverse_up_m"] == pytest.approx(-3.643551 + du, abs=1e-6)
    assert nova.site("nd-left").derived_from == "nd" and nova.site("nd-left").edge == "left"


def test_face_report_angles(nova):
    face = compute_face(nova, nova.site("nd"))
    pts = {r["edge"]: r for r in face["points"]}
    assert [r["edge"] for r in face["points"]] == ["left", "center", "right", "top", "bottom"]
    # the face is 2*HW wide at ~994 m from the origin
    sub = face["subtended_at_axis_origin_mrad"]
    assert sub["left_right"] == pytest.approx(4.039, abs=0.005)
    assert sub["top_bottom"] == pytest.approx(4.039, abs=0.005)
    # left edge is further from the (eastern) axis than the right edge
    assert pts["left"]["vs_axis"]["off_axis_mrad"] > pts["center"]["vs_axis"]["off_axis_mrad"] > pts["right"]["vs_axis"]["off_axis_mrad"]
    assert pts["left"]["vs_axis"]["off_axis_mrad"] == pytest.approx(14.13, abs=0.01)
    assert pts["center"]["vs_axis"]["off_axis_mrad"] == pytest.approx(12.19, abs=0.01)
    assert pts["right"]["vs_axis"]["off_axis_mrad"] == pytest.approx(10.29, abs=0.01)
    # the edge points are 2*HW apart
    d = math.dist(pts["left"]["ecef_m"], pts["right"]["ecef_m"])
    assert d == pytest.approx(2 * HW, abs=1e-6)
    # opening-angle variants for every configured angle that involves the ND
    labels = [v["label"] for v in face["opening_angles"]]
    assert "Target: ND vs FD (both surveyed)" in labels
    v = [x for x in face["opening_angles"] if x["label"] == "Target: ND vs FD (both surveyed)"][0]
    e = {x["edge"]: x for x in v["edges"]}
    assert e["center"]["angle_mrad"] == pytest.approx(2.474, abs=0.005)
    assert e["left"]["angle_mrad"] == pytest.approx(1.472, abs=0.005)
    assert e["right"]["angle_mrad"] == pytest.approx(4.270, abs=0.005)
    # each variant equals a direct opening-angle computation with the edge site
    direct = compute_opening_angle(nova, OpeningAngle("target", "nd-left", "fd"))
    assert e["left"]["angle_mrad"] == pytest.approx(direct["angle_mrad"], rel=1e-12)


def test_compute_all_carries_faces_and_edge_sites(nova):
    r = compute_all(nova)
    assert [f["site_id"] for f in r["faces"]] == ["nd", "fd"]
    ids = [s["id"] for s in r["sites"]]
    assert "nd-left" in ids and "fd-right" in ids
    edge = [s for s in r["sites"] if s["id"] == "nd-right"][0]
    assert edge["derived_from"] == "nd" and edge["edge"] == "right" and "vs_axis" in edge


def test_face_on_a_geodetic_site_uses_the_global_axis_and_validates():
    base = load_yaml(ROOT / "config" / "nova.yaml")
    d = dict(base)
    d["sites"] = [s for s in base["sites"] if s["id"] in ("target", "minos-fd")] + [
        {"name": "G", "id": "g", "lat": 41.84, "lon": -88.27, "height_m": 100.0, "face": {"half_width_m": 1.5}}]
    d["baselines"] = [{"from": "target", "to": "g"}]
    d["opening_angles"] = []
    p = Problem.from_dict(d)
    f = compute_face(p, p.site("g"))
    pts = {r["edge"]: r for r in f["points"]}
    assert pts["right"]["vs_axis"]["transverse_right_m"] - pts["center"]["vs_axis"]["transverse_right_m"] == pytest.approx(1.5, abs=1e-6)
    assert pts["left"]["vs_axis"]["along_axis_m"] == pytest.approx(pts["center"]["vs_axis"]["along_axis_m"], abs=1e-6)
    assert "top" not in pts
    with pytest.raises(ValueError):
        Problem.from_dict({"sites": [{"name": "A", "id": "a", "lat": 0, "lon": 0, "face": {"half_width_m": 1}},
                                     {"name": "B", "id": "b", "lat": 1, "lon": 1}]})
    with pytest.raises(ValueError):
        Problem.from_dict({"sites": [{"name": "A", "id": "a", "lat": 0, "lon": 0, "face": {"depth_m": 1}},
                                     {"name": "B", "id": "b", "lat": 1, "lon": 1}], "beam_axis": {"from": "a", "to": "b"}})
