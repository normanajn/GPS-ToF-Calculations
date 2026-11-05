"""Earth models, ECEF transforms and local (ENU) frames.  Pure stdlib."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence, Tuple

from .constants import WGS84_A, WGS84_B, GRS80_A, GRS80_INV_F

Vec3 = Tuple[float, float, float]


@dataclass(frozen=True)
class Ellipsoid:
    name: str
    a: float
    b: float

    @property
    def f(self) -> float:
        return (self.a - self.b) / self.a

    @property
    def e2(self) -> float:
        """first eccentricity squared"""
        return (self.a * self.a - self.b * self.b) / (self.a * self.a)

    @property
    def ep2(self) -> float:
        """second eccentricity squared"""
        return (self.a * self.a - self.b * self.b) / (self.b * self.b)

    @property
    def e(self) -> float:
        return math.sqrt(self.e2)


WGS84 = Ellipsoid("WGS84", WGS84_A, WGS84_B)
GRS80 = Ellipsoid("GRS80", GRS80_A, GRS80_A * (1.0 - 1.0 / GRS80_INV_F))

ELLIPSOIDS = {"wgs84": WGS84, "grs80": GRS80}


# ---------------------------------------------------------------- vectors
def vsub(a: Sequence[float], b: Sequence[float]) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vadd(a: Sequence[float], b: Sequence[float]) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vscale(a: Sequence[float], s: float) -> Vec3:
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Sequence[float], b: Sequence[float]) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a: Sequence[float]) -> float:
    return math.sqrt(dot(a, a))


def unit(a: Sequence[float]) -> Vec3:
    n = norm(a)
    return (a[0] / n, a[1] / n, a[2] / n)


def angle_between(a: Sequence[float], b: Sequence[float]) -> float:
    """Numerically stable angle between two vectors (rad)."""
    na, nb = norm(a), norm(b)
    c = cross(a, b)
    return math.atan2(norm(c), dot(a, b)) if na and nb else 0.0


# ------------------------------------------------------------- transforms
def prime_vertical_radius(lat: float, ell: Ellipsoid = WGS84) -> float:
    """N(phi) = a / sqrt(1 - e^2 sin^2 phi)"""
    s = math.sin(lat)
    return ell.a / math.sqrt(1.0 - ell.e2 * s * s)


def geodetic_to_ecef(lat: float, lon: float, h: float, ell: Ellipsoid = WGS84) -> Vec3:
    """Geodetic (rad, rad, m above ellipsoid) -> ECEF (m), standard axes:
    X through (0, 0), Y through (0, 90E), Z along the pole."""
    n = prime_vertical_radius(lat, ell)
    cl, sl = math.cos(lat), math.sin(lat)
    return ((n + h) * cl * math.cos(lon),
            (n + h) * cl * math.sin(lon),
            (n * (1.0 - ell.e2) + h) * sl)


def geodetic_to_ecef_as_printed(lat: float, lon: float, h: float, ell: Ellipsoid = WGS84) -> Vec3:
    """Eq. 17 of the 2014 note as printed: Z = (b^2/a^2)(N + h) sin(phi).
    Kept only to quantify that erratum."""
    n = prime_vertical_radius(lat, ell)
    cl, sl = math.cos(lat), math.sin(lat)
    return ((n + h) * cl * math.cos(lon),
            (n + h) * cl * math.sin(lon),
            (1.0 - ell.e2) * (n + h) * sl)


def spherical_to_ecef(lat: float, lon: float, h: float, radius: float) -> Vec3:
    """Spherical Earth of the given radius; same axis convention as ECEF."""
    r = radius + h
    cl = math.cos(lat)
    return (r * cl * math.cos(lon), r * cl * math.sin(lon), r * math.sin(lat))


def ecef_to_geodetic(p: Sequence[float], ell: Ellipsoid = WGS84) -> Tuple[float, float, float]:
    """ECEF -> geodetic (lat rad, lon rad, h m).  Iterative; converges to < 1e-12 rad."""
    x, y, z = p
    lon = math.atan2(y, x)
    r = math.hypot(x, y)
    if r == 0.0:
        return (math.copysign(math.pi / 2, z), lon, abs(z) - ell.b)
    lat = math.atan2(z, r * (1.0 - ell.e2))
    for _ in range(25):
        n = prime_vertical_radius(lat, ell)
        h = r / math.cos(lat) - n
        new = math.atan2(z, r * (1.0 - ell.e2 * n / (n + h)))
        if abs(new - lat) < 1e-14:
            lat = new
            break
        lat = new
    n = prime_vertical_radius(lat, ell)
    h = r / math.cos(lat) - n
    return lat, lon, h


def enu_basis(lat: float, lon: float) -> Tuple[Vec3, Vec3, Vec3]:
    """Unit vectors (East, North, Up) of the local geodetic frame, in ECEF."""
    sl, cl = math.sin(lat), math.cos(lat)
    so, co = math.sin(lon), math.cos(lon)
    e = (-so, co, 0.0)
    n = (-sl * co, -sl * so, cl)
    u = (cl * co, cl * so, sl)
    return e, n, u


def enu_to_ecef_offset(d_enu: Sequence[float], lat: float, lon: float,
                       up: str = "geodetic", p: Sequence[float] = None) -> Vec3:
    """Rotate a local (dE, dN, dU) displacement into ECEF.  ``up='radial'`` uses
    the geocentric direction p/|p| as 'up' (plane tangent to a sphere), which
    is what the 2014 note describes; East and North stay geodetic."""
    e, n, u = enu_basis(lat, lon)
    if up == "radial":
        if p is None:
            raise ValueError("radial up needs the ECEF position")
        u = unit(p)
    elif up != "geodetic":
        raise ValueError("up must be 'geodetic' or 'radial'")
    return (d_enu[0] * e[0] + d_enu[1] * n[0] + d_enu[2] * u[0],
            d_enu[0] * e[1] + d_enu[1] * n[1] + d_enu[2] * u[1],
            d_enu[0] * e[2] + d_enu[1] * n[2] + d_enu[2] * u[2])


def ecef_to_enu(v: Sequence[float], lat: float, lon: float) -> Vec3:
    e, n, u = enu_basis(lat, lon)
    return (dot(v, e), dot(v, n), dot(v, u))


def azimuth_elevation(v: Sequence[float], lat: float, lon: float) -> Tuple[float, float]:
    """Azimuth (rad, clockwise from geodetic North) and elevation (rad, + above
    the local horizontal) of ECEF direction ``v`` seen from a point at lat/lon."""
    de, dn, du = ecef_to_enu(v, lat, lon)
    az = math.atan2(de, dn) % (2.0 * math.pi)
    el = math.atan2(du, math.hypot(de, dn))
    return az, el
