"""Fermilab Site Coordinate System (FSCS / "DUSAF" site coordinates).

Definition: B. Oshinowo, "Fermilab Coordinate Systems", Beams-doc-1148
(MI-0209), v4.0, 1997.  The FSCS:XYH plane is a double stereographic
projection (NAD83 / GRS80) with origin at monument A0, rotated so that +Y
points along geodetic azimuth 38° 16' 48.01429", scaled by F0 to true scale
at 720 ft above the DUSAF datum, with false coordinates (100000, 100000) ft.
Heights:  h_ellipsoidal = H_DUSAF + dH_NAVD88 + N_geoid,
with dH_NAVD88 = -0.17308 m and N(A0) = -32.78456 m (GEOID93).

Beam sheets in the NuMI Technical Design Report quote element positions in
this system in feet (x east, y north, z elevation).  The geoid height is
taken as constant across the site (the GEOID93 slope over the NuMI beamline
is a few cm), which is far below the metre-level accuracy of the design
coordinates themselves.
"""
from __future__ import annotations

import math
from typing import Sequence, Tuple

from .angles import parse_angle
from .constants import US_SURVEY_FOOT
from .geodesy import GRS80
from .projection import ObliqueStereographic

A0_LAT_DEG = parse_angle("41 50 14.312704 N", "lat")
A0_LON_DEG = parse_angle("88 15 41.143123 W", "lon")
A0_H_ELL_M = 186.49880
Y_AXIS_AZIMUTH_DEG = parse_angle("38 16 48.01429")
FALSE_XY_FT = 100000.0
Z0_FT = 720.0
F0 = 1.000029251309483
DH_NAVD88_M = -0.17308
GEOID_N_A0_M = -32.78456
FT = US_SURVEY_FOOT

_proj = ObliqueStereographic(GRS80, math.radians(A0_LAT_DEG), math.radians(A0_LON_DEG), k0=1.0)
_alpha = math.radians(Y_AXIS_AZIMUTH_DEG)


def geodetic_to_fscs(lat_deg: float, lon_deg: float, h_ell_m: float,
                     geoid_n_m: float = GEOID_N_A0_M) -> Tuple[float, float, float]:
    """Geodetic (NAD83≈WGS84) -> FSCS (x, y, z) in US survey feet."""
    E, N = _proj.forward(math.radians(lat_deg), math.radians(lon_deg))
    # rotate so +Y is along azimuth alpha: Y = N cos a + E sin a ; X = E cos a - N sin a
    X = E * math.cos(_alpha) - N * math.sin(_alpha)
    Y = N * math.cos(_alpha) + E * math.sin(_alpha)
    x_ft = (F0 * X) / FT + FALSE_XY_FT
    y_ft = (F0 * Y) / FT + FALSE_XY_FT
    H_dusaf = h_ell_m - DH_NAVD88_M - geoid_n_m
    return x_ft, y_ft, H_dusaf / FT


def fscs_to_geodetic(x_ft: float, y_ft: float, z_ft: float,
                     geoid_n_m: float = GEOID_N_A0_M) -> Tuple[float, float, float]:
    """FSCS (x, y, z) in US survey feet -> (lat deg, lon deg, h ellipsoidal m)."""
    X = (x_ft - FALSE_XY_FT) * FT / F0
    Y = (y_ft - FALSE_XY_FT) * FT / F0
    E = X * math.cos(_alpha) + Y * math.sin(_alpha)
    N = -X * math.sin(_alpha) + Y * math.cos(_alpha)
    lat, lon = _proj.inverse(E, N)
    h = z_ft * FT + DH_NAVD88_M + geoid_n_m
    return math.degrees(lat), math.degrees(lon), h


def fscs_bearing_to_azimuth(bearing_deg_ccw_from_east: float) -> float:
    """TDR beam-sheet bearing (ccw from site +X/East) -> geodetic azimuth (deg,
    clockwise from North) at A0.  Meridian convergence away from A0 is not
    applied (it is ~1" per 100 m here)."""
    fscs_az = (90.0 - bearing_deg_ccw_from_east) % 360.0
    return (fscs_az + Y_AXIS_AZIMUTH_DEG) % 360.0
