import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from gps_tof.config import merge, read_dotenv, parse_site_spec, parse_pair_spec
from gps_tof.model import Problem, Settings
from gps_tof import cli

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "nova.yaml"


def test_yaml_exponent_strings_are_coerced():
    s = Settings.from_dict({"clock_hz": "64.0e6", "apply_sagnac": "yes", "precision_digits": "3"})
    assert s.clock_hz == 64e6 and s.apply_sagnac is True and s.precision_digits == 3


def test_override_order(tmp_path, monkeypatch):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(yaml.safe_dump({"clock_hz": 1.0, "rounding": "floor", "precision_digits": 2,
                                   "sites": [{"name": "A", "lat": 1, "lon": 2}, {"name": "B", "lat": 3, "lon": 4}]}))
    dotenv = tmp_path / ".env"
    dotenv.write_text("GPS_TOF_CLOCK_HZ=2.0\nGPS_TOF_ROUNDING=ceil\nGPS_TOF_PRECISION_DIGITS=5\n")
    env = {"GPS_TOF_CLOCK_HZ": "3.0", "GPS_TOF_ROUNDING": "round"}
    m = merge(cfg, {"clock_hz": 4.0}, environ=env, dotenv_paths=[dotenv])
    p = m["problem"]
    assert p["clock_hz"] == 4.0            # command line wins
    assert p["rounding"] == "round"        # environment beats .env
    assert p["precision_digits"] == 5      # .env beats the file
    assert len(p["sites"]) == 2
    prob = Problem.from_dict(p)
    assert [b.source + ":" + b.target for b in prob.baselines] == ["a:b"]   # default: every pair


def test_dotenv_parsing(tmp_path):
    f = tmp_path / ".env"
    f.write_text("# comment\nexport GPS_TOF_FORMAT='md'\nGPS_TOF_OUTPUT=\"x.md\"\nBAD LINE\n")
    assert read_dotenv(f) == {"GPS_TOF_FORMAT": "md", "GPS_TOF_OUTPUT": "x.md"}


def test_site_and_pair_specs():
    d = parse_site_spec('name="Ash River" id=ash lat="48 22.715780 N" lon=92:49.876930W h=348.638 offset=0,0,-19.8 u_offset_m=2')
    assert d["id"] == "ash" and d["offset_enu_m"] == [0, 0, -19.8] and d["uncertainty"] == {"offset_m": 2.0}
    assert d["lat"] == pytest.approx(48.378596333)
    f = parse_site_spec("name=T fscs=100327.838,97780.188,626.743")
    assert f["fscs_xyz_ft"] == [100327.838, 97780.188, 626.743]
    assert parse_pair_spec("a:b:label:axis") == {"from": "a", "to": "b", "label": "label", "axis_to": "axis"}
    with pytest.raises(ValueError):
        parse_site_spec("lat=1 lon=2")


def test_cli_json_and_markdown(tmp_path, capsys):
    rc = cli.main(["-c", str(CFG), "-p", "nd:fd2", "--format", "json", "--no-timing-shifts"])
    assert rc == 0
    r = json.loads(capsys.readouterr().out)
    assert r["baselines"][0]["timing_shifts"] == []
    out = tmp_path / "rep"
    rc = cli.main(["-c", str(CFG), "--format", "all", "-o", str(out)])
    assert rc == 0
    assert (tmp_path / "rep.md").exists() and (tmp_path / "rep.txt").exists() and (tmp_path / "rep.json").exists()
    md = (tmp_path / "rep.md").read_text()
    assert "Correction ledger" in md and "Error budget" in md


def test_cli_adhoc_sites_without_config(capsys):
    rc = cli.main(["-c", os.devnull, "-s", "name=A lat=41:50:23N lon=88:16:13W h=-72", "-s", "name=B lat=\"48 22.715780 N\" lon=\"92 49.876930 W\" h=348.638",
                   "--format", "json", "--no-sensitivities"])
    assert rc == 0
    r = json.loads(capsys.readouterr().out)
    assert r["baselines"][0]["result"]["L_m"] == pytest.approx(809606.1622, abs=1e-3)


def test_cli_nmea_and_fscs_helpers(tmp_path, capsys):
    f = tmp_path / "fix.nmea"
    f.write_text("$GPGGA,210341.002,4822.716417,N,09249.877638,W,1,12,0.71,382.823,M,-32.462,M,,*5D\n")
    assert cli.main_nmea([str(f), "--yaml"]) == 0
    y = yaml.safe_load(capsys.readouterr().out)
    assert y["sites"][0]["datum"] == "msl"
    assert cli.main_fscs(["to-geodetic", "100000", "100000", "720"]) == 0
    out = capsys.readouterr().out
    assert "41.837309084" in out
