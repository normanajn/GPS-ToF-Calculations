"""Reproduce the 2013 Mathematica notebook, the 2014 note and the NuMI target cross-checks."""
import math
from pathlib import Path

import pytest

from gps_tof.model import Problem, Site, Baseline, Settings
from gps_tof.calc import compute_baseline, compute_all, chord, final_stage
from gps_tof.config import load_yaml

ROOT = Path(__file__).resolve().parents[1]
C = 299792458.0

FNAL = dict(name="FNAL", lat="41 50 23 N", lon="88 16 13 W")
ASH1 = dict(name="Ash1", lat="48 22.715780 N", lon="92 49.876930 W")


def problem(sites, baselines=None, shifts=None, **settings):
    d = {"sites": sites, "baselines": baselines or [], "timing_shifts": shifts or []}
    d.update(settings)
    return Problem.from_dict(d)


def test_2013_notebook_spherical_model():
    p = problem([dict(FNAL, height_m=228 - 300), dict(ASH1, height_m=348.0)], earth={"model": "sphere"})
    b = compute_baseline(p, p.baselines[0])
    assert b["result"]["L_m"] == pytest.approx(810429.1726392909, rel=1e-9)
    assert b["result"]["t_us"] == pytest.approx(2703.3007, abs=1e-4)


def test_2013_notebook_wgs84_result_and_total():
    shifts = [dict(name="MI", turns=141, buckets_per_turn=588, rf_hz=53.1034e6)]
    p = problem([dict(FNAL, height_m=228 - 300), dict(ASH1, height_m=348.638)], shifts=shifts)
    b = compute_baseline(p, p.baselines[0])
    assert b["result"]["L_m"] == pytest.approx(809606.1622206265, rel=1e-9)
    assert b["result"]["t_us"] == pytest.approx(2700.555469679716, rel=1e-9)
    assert b["result"]["ticks"] == pytest.approx(172835.5500595018, rel=1e-9)
    assert b["timing_shifts"][0]["ticks"] == pytest.approx(99920.38174580157, rel=1e-9)
    assert b["total"]["ticks"] == pytest.approx(272755.9318053034, rel=1e-9)
    assert b["total"]["ticks_int"] == 272756
    assert b["result"]["legacy_units"] == pytest.approx(5401.1109, abs=1e-4)


def test_longitude_sign_convention_does_not_change_distance():
    p1 = problem([dict(FNAL, height_m=-72), dict(ASH1, height_m=348.638)])
    p2 = problem([dict(FNAL, lon="88 16 13 E", height_m=-72), dict(ASH1, lon="92 49.876930 E", height_m=348.638)])
    L1 = compute_baseline(p1, p1.baselines[0])["result"]["L_m"]
    L2 = compute_baseline(p2, p2.baselines[0])["result"]["L_m"]
    assert L1 == pytest.approx(L2, abs=1e-9)
    # but the Sagnac term flips sign
    s1 = compute_baseline(p1, p1.baselines[0])["effects"]["sagnac_ns"]
    s2 = compute_baseline(p2, p2.baselines[0])["effects"]["sagnac_ns"]
    assert s1 == pytest.approx(-1.303, abs=0.01)
    assert s2 == pytest.approx(-s1, rel=1e-9)


def test_vertical_offset_equals_height_change_in_ledger():
    pa = problem([dict(FNAL, height_m=228, offset_enu_m=[0, 0, -300]), dict(ASH1, height_m=348.638)])
    pb = problem([dict(FNAL, height_m=228 - 300), dict(ASH1, height_m=348.638)])
    La = compute_baseline(pa, pa.baselines[0])["result"]["L_m"]
    Lb = compute_baseline(pb, pb.baselines[0])["result"]["L_m"]
    assert La == pytest.approx(Lb, abs=1e-6)


def test_2014_note_offsets_change():
    """The 2014-note offsets (ND 105+15 m, FD 12+7.8 m) lengthen the 2013 chord by about +10.1 m."""
    p = problem([dict(FNAL, height_m=228, offset_enu_m=[0, 0, -120]), dict(ASH1, height_m=348.638, offset_enu_m=[0, 0, -19.8])])
    b = compute_baseline(p, p.baselines[0])
    assert b["result"]["L_m"] - 809606.1622206265 == pytest.approx(10.1, abs=0.05)
    steps = [(r["step"], r["site"]) for r in b["ledger"]]
    assert steps == [("reference model", None), ("Earth model", None), ("vertical offset", "fnal"), ("vertical offset", "ash1")]
    # each vertical row must move L by (offset x sin(dip)) of its own site only
    rows = {r["site"]: r for r in b["ledger"] if r["site"]}
    assert rows["fnal"]["dL_m"] == pytest.approx(-120 * 0.0633, abs=0.05)
    assert rows["ash1"]["dL_m"] == pytest.approx(-19.8 * 0.0638, abs=0.02)
    assert b["ledger"][-1]["L_m"] == pytest.approx(b["result"]["L_m"], abs=1e-6)


def test_msl_datum_step():
    p = problem([dict(FNAL, height_m=228, datum="msl", geoid_separation_m=-33.0), dict(ASH1, height_m=348.638)])
    b = compute_baseline(p, p.baselines[0])
    datum = [r for r in b["ledger"] if r["step"] == "height datum"]
    assert len(datum) == 1
    assert datum[0]["dL_m"] == pytest.approx(-2.08, abs=0.02)   # 2014 note sec. 11.3


def test_sensitivities_match_note():
    p = problem([dict(FNAL, height_m=-72), dict(ASH1, height_m=348.638)])
    b = compute_baseline(p, p.baselines[0])
    s = {(r["site"], r["kind"]): r["dL_m"] for r in b["sensitivities"] if r["site"]}
    # the 2014 note quotes -9.62 / +9.62 for the longitudes because it used mirrored (east-positive)
    # longitudes; with physical west-negative longitudes moving FNAL east lengthens the chord
    assert s[("fnal", "lat")] == pytest.approx(-27.98, abs=0.02)
    assert s[("fnal", "lon")] == pytest.approx(+9.62, abs=0.02)
    assert s[("ash1", "lat")] == pytest.approx(27.24, abs=0.02)
    assert s[("ash1", "lon")] == pytest.approx(-9.62, abs=0.02)
    assert s[("fnal", "height")] == pytest.approx(0.0630, abs=5e-4)
    g = b["geometry"]
    assert g["azimuth_at_source_deg"] == pytest.approx(335.3, abs=0.1)
    assert g["elevation_at_source_deg"] == pytest.approx(-3.613, abs=0.01)
    assert g["central_angle_deg"] == pytest.approx(7.290, abs=0.002)
    assert g["arc_minus_chord_m"] == pytest.approx(544, abs=2)


def test_error_budget_quantization():
    p = problem([dict(FNAL, height_m=-72, uncertainty={"quantization_arcsec": 1.0}), dict(ASH1, height_m=348.638)])
    b = compute_baseline(p, p.baselines[0])
    items = {i["source"]: i for i in b["error_budget"]["items"]}
    rms = [v for k, v in items.items() if "RMS" in k][0]
    worst = [v for k, v in items.items() if "worst" in k][0]
    assert rms["sigma_ticks"] == pytest.approx(1.8, abs=0.1)
    assert worst["sigma_ticks"] == pytest.approx(4.0, abs=0.1)


def test_trigger_window_and_rounding():
    p = problem([dict(FNAL, height_m=-72), dict(ASH1, height_m=348.638)],
                trigger_window={"before_us": 20, "after_us": 30, "microslice_us": 50}, rounding="floor")
    b = compute_baseline(p, p.baselines[0])
    w = b["window"]
    assert w["tof_hi_ticks"] - w["tof_lo_ticks"] == pytest.approx(3200.0)
    assert (w["microslices_min"], w["microslices_max"]) == (1, 2)
    assert b["result"]["ticks_int"] == 172835


# ---------------------------------------------------------------- NuMI target
@pytest.fixture(scope="module")
def nova():
    return Problem.from_dict(load_yaml(ROOT / "config" / "nova.yaml"))


def test_target_position_from_tdr_beam_sheet(nova):
    t = nova.site("target")
    assert t.lat == pytest.approx(41.83197, abs=2e-5)
    assert t.lon == pytest.approx(-88.26553, abs=2e-5)
    assert t.height_m == pytest.approx(158.07, abs=0.05)


def test_target_to_minos_fd_matches_published_distance(nova):
    """MINOS NIM paper: 735,338.0 m from the upstream end of horn 1 (design target is 1.5 m upstream)."""
    b = compute_baseline(nova, Baseline("target", "minos-fd", axis_to="decay-end"))
    assert b["result"]["L_m"] == pytest.approx(735338.0, abs=10.0)
    assert b["geometry"]["off_axis_angle_mrad"] < 0.1        # the beam axis points at Soudan
    assert b["geometry"]["azimuth_at_source_deg"] == pytest.approx(336.098, abs=0.01)   # 1999 geodetic survey
    assert b["geometry"]["elevation_at_source_deg"] == pytest.approx(-3.34, abs=0.01)


def test_beam_axis_and_off_axis_angle(nova):
    b = compute_baseline(nova, Baseline("target", "decay-end"))
    assert b["result"]["L_m"] == pytest.approx((3522.04627 - 1146.09958) * 0.3048006096, abs=0.05)   # beam-sheet stations
    b = compute_baseline(nova, Baseline("target", "fd2", axis_to="decay-end"))
    assert b["geometry"]["off_axis_angle_mrad"] == pytest.approx(14.6, abs=0.1)
    assert b["result"]["L_m"] == pytest.approx(810565, abs=5)
    assert b["result"]["L_m"] - compute_baseline(nova, Baseline("nd", "fd2"))["result"]["L_m"] == pytest.approx(1015, abs=1)
    assert b["result"]["L_m"] - compute_baseline(nova, Baseline("nd-under-mast", "fd2"))["result"]["L_m"] == pytest.approx(948, abs=2)


def test_compute_all_runs_every_configured_baseline(nova):
    r = compute_all(nova)
    assert len(r["baselines"]) == len(nova.baselines) == 9
    assert all(b["ledger"][-1]["L_m"] == pytest.approx(b["result"]["L_m"]) for b in r["baselines"])
