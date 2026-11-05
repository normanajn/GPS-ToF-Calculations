import math
import pytest

from gps_tof.geodesy import (WGS84, GRS80, Ellipsoid, geodetic_to_ecef, ecef_to_geodetic, enu_basis,
                             enu_to_ecef_offset, azimuth_elevation, norm, vsub, angle_between)
from gps_tof.projection import ObliqueStereographic
from gps_tof import fermilab_site as fs
from gps_tof.angles import parse_angle


def test_wgs84_constants():
    assert WGS84.e2 == pytest.approx(6.69437999014e-3, rel=1e-9)
    assert WGS84.a * (1 - 1 / 298.257223563) == pytest.approx(WGS84.b, abs=1e-6)
    assert abs(GRS80.b - WGS84.b) < 2e-4


def test_ecef_roundtrip():
    for lat, lon, h in [(41.8397, -88.2703, 228.0), (48.3786, -92.8313, 348.6), (-33.9, 151.2, -50.0), (89.9, 10.0, 1000.0)]:
        p = geodetic_to_ecef(math.radians(lat), math.radians(lon), h)
        la, lo, hh = ecef_to_geodetic(p)
        assert math.degrees(la) == pytest.approx(lat, abs=1e-10)
        assert math.degrees(lo) == pytest.approx(lon, abs=1e-10)
        assert hh == pytest.approx(h, abs=1e-6)


def test_vertical_enu_offset_equals_height_change():
    lat, lon = math.radians(41.84), math.radians(-88.27)
    p = geodetic_to_ecef(lat, lon, 228.0)
    q = geodetic_to_ecef(lat, lon, 228.0 - 120.0)
    d = enu_to_ecef_offset((0.0, 0.0, -120.0), lat, lon)
    assert norm(vsub((p[0] + d[0], p[1] + d[1], p[2] + d[2]), q)) < 1e-6


def test_enu_basis_orthonormal_and_azimuth():
    lat, lon = math.radians(41.84), math.radians(-88.27)
    e, n, u = enu_basis(lat, lon)
    for v in (e, n, u):
        assert norm(v) == pytest.approx(1.0)
    az, el = azimuth_elevation(n, lat, lon)
    assert az == pytest.approx(0.0, abs=1e-12) and el == pytest.approx(0.0, abs=1e-12)
    az, el = azimuth_elevation(e, lat, lon)
    assert math.degrees(az) == pytest.approx(90.0)


def test_epsg_9809_worked_example():
    """EPSG Guidance Note 7-2, Oblique Stereographic (Amersfoort / RD New)."""
    bessel = Ellipsoid("Bessel", 6377397.155, 6377397.155 * (1 - 1 / 299.15281))
    p = ObliqueStereographic(bessel, math.radians(parse_angle("52 09 22.178 N")), math.radians(parse_angle("5 23 15.500 E")),
                             k0=0.9999079, false_e=155000.0, false_n=463000.0)
    E, N = p.forward(math.radians(53.0), math.radians(6.0))
    assert E == pytest.approx(196105.283, abs=2e-3)
    assert N == pytest.approx(557057.739, abs=2e-3)
    lat, lon = p.inverse(E, N)
    assert math.degrees(lat) == pytest.approx(53.0, abs=1e-10)
    assert math.degrees(lon) == pytest.approx(6.0, abs=1e-10)


def test_fscs_origin_and_cfmi_control_point():
    x, y, z = fs.geodetic_to_fscs(fs.A0_LAT_DEG, fs.A0_LON_DEG, fs.A0_H_ELL_M)
    assert (x, y, z) == pytest.approx((100000.0, 100000.0, 720.0), abs=1e-4)
    lat, lon, h = fs.fscs_to_geodetic(100661.49800, 95856.98802, 715.664)   # CFMI, Beams-doc-1148 sec. 5
    assert lat == pytest.approx(parse_angle("41 49 38.134927 N"), abs=1e-9)
    assert lon == pytest.approx(parse_angle("88 16 08.184535 W"), abs=1e-9)
    assert h == pytest.approx(185.19035, abs=0.02)   # 1.3 cm: geoid slope A0 -> CFMI (constant-N approximation)


def test_mi60_azimuth_from_beam_sheet_bearing():
    # Beams-doc-1148 App. A: MI-60 straight has FSCS azimuth 301 13 53.9; TDR beam sheet bearing 148.76849
    assert fs.fscs_bearing_to_azimuth(148.76849) == pytest.approx(parse_angle("301 13 53.9") + fs.Y_AXIS_AZIMUTH_DEG, abs=2e-4)
