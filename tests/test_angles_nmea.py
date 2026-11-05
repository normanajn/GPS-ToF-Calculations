import math
import pytest

from gps_tof.angles import parse_angle, parse_nmea, dms
from gps_tof import nmea

GGA = "$GPGGA,210341.002,4822.716417,N,09249.877638,W,1,12,0.71,382.823,M,-32.462,M,,*5D"
RMC = "$GPRMC,210341.002,A,4822.716417,N,09249.877638,W,0.000,0.00,070313,,,A*40"


@pytest.mark.parametrize("text,expected", [
    ("41 50 23 N", 41 + 50 / 60 + 23 / 3600),
    ("41:50:23N", 41 + 50 / 60 + 23 / 3600),
    ("41d50m23sN", 41 + 50 / 60 + 23 / 3600),
    ("41°50'23\"N", 41 + 50 / 60 + 23 / 3600),
    ("-88 16 13", -(88 + 16 / 60 + 13 / 3600)),
    ("88 16 13 W", -(88 + 16 / 60 + 13 / 3600)),
    ("48 22.715780 N", 48 + 22.715780 / 60),
    ("92:49.876930 W", -(92 + 49.876930 / 60)),
    ("41.839722", 41.839722),
    (41.839722, 41.839722),
    ("S 12.5", -12.5),
])
def test_parse_angle(text, expected):
    assert parse_angle(text) == pytest.approx(expected, abs=1e-12)


def test_parse_angle_rejects_bad_hemisphere_and_ranges():
    with pytest.raises(ValueError):
        parse_angle("41 50 23 E", "lat")
    with pytest.raises(ValueError):
        parse_angle("41 61 0 N")
    with pytest.raises(ValueError):
        parse_angle("95 0 0 N", "lat")
    with pytest.raises(ValueError):
        parse_angle("-41 50 23 N")


def test_nmea_coordinate_and_checksum():
    assert parse_nmea("4822.716417", "N") == pytest.approx(48 + 22.716417 / 60)
    assert parse_nmea("09249.877638", "W") == pytest.approx(-(92 + 49.877638 / 60))
    assert nmea.check(GGA) is True
    assert nmea.check(RMC) is True
    assert nmea.check(GGA[:-1] + "E") is False
    assert nmea.check("$POLYI,JN,18") is None


def test_gga_decoding_gives_ellipsoidal_height():
    g = nmea.parse_gga(GGA)
    assert g["lat_deg"] == pytest.approx(48.378606950, abs=1e-9)
    assert g["lon_deg"] == pytest.approx(-92.831293967, abs=1e-9)
    assert g["msl_altitude_m"] == 382.823
    assert g["geoid_separation_m"] == -32.462
    assert g["ellipsoidal_height_m"] == pytest.approx(350.361)   # equals the $POLYP altitude in the 2014 note
    assert g["satellites"] == 12 and g["fix_quality"] == 1
    assert nmea.parse_rmc_date(RMC) == "2013-03-07"


def test_sites_from_text():
    sites = nmea.sites_from_text(GGA + "\n" + RMC + "\n")
    assert len(sites) == 1
    assert sites[0]["datum"] == "msl" and sites[0]["geoid_separation_m"] == -32.462


def test_dms_roundtrip():
    s = dms(parse_angle("48 22.715780 N"), "lat")
    assert s.startswith("48° 22' 42.9468\" N")
    assert parse_angle(s) == pytest.approx(parse_angle("48 22.715780 N"), abs=1e-9)
