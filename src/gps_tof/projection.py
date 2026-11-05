"""Oblique (double) stereographic projection, EPSG method 9809.

The ellipsoid is mapped conformally to a sphere (Gauss), then the sphere is
projected stereographically to the plane.  This is the projection the
Fermilab Survey, Alignment and Geodesy group uses for the Fermilab Site
Coordinate System (Beams-doc-1148).  Formulas follow the EPSG Guidance Note
7-2.  Verified against the EPSG worked example (Amersfoort / RD New).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

from .geodesy import Ellipsoid


@dataclass(frozen=True)
class ObliqueStereographic:
    ell: Ellipsoid
    lat0: float          # rad
    lon0: float          # rad
    k0: float = 1.0
    false_e: float = 0.0
    false_n: float = 0.0

    # --- derived constants -------------------------------------------------
    def _consts(self):
        e = self.ell.e
        e2 = self.ell.e2
        s0 = math.sin(self.lat0)
        c0 = math.cos(self.lat0)
        rho0 = self.ell.a * (1.0 - e2) / (1.0 - e2 * s0 * s0) ** 1.5
        nu0 = self.ell.a / math.sqrt(1.0 - e2 * s0 * s0)
        R = math.sqrt(rho0 * nu0)
        n = math.sqrt(1.0 + e2 * c0 ** 4 / (1.0 - e2))
        S1 = (1.0 + s0) / (1.0 - s0)
        S2 = (1.0 - e * s0) / (1.0 + e * s0)
        w1 = (S1 * S2 ** e) ** n
        sin_chi0 = (w1 - 1.0) / (w1 + 1.0)
        c = (n + s0) * (1.0 - sin_chi0) / ((n - s0) * (1.0 + sin_chi0))
        w2 = c * w1
        chi0 = math.asin((w2 - 1.0) / (w2 + 1.0))
        return R, n, c, chi0

    def forward(self, lat: float, lon: float) -> Tuple[float, float]:
        """(lat, lon) rad -> (Easting, Northing) m."""
        e = self.ell.e
        R, n, c, chi0 = self._consts()
        Lam0 = self.lon0
        Lam = n * (lon - Lam0) + Lam0
        s = math.sin(lat)
        Sa = (1.0 + s) / (1.0 - s)
        Sb = (1.0 - e * s) / (1.0 + e * s)
        w = c * (Sa * Sb ** e) ** n
        chi = math.asin((w - 1.0) / (w + 1.0))
        dl = Lam - Lam0
        B = 1.0 + math.sin(chi) * math.sin(chi0) + math.cos(chi) * math.cos(chi0) * math.cos(dl)
        E = self.false_e + 2.0 * R * self.k0 * math.cos(chi) * math.sin(dl) / B
        N = self.false_n + 2.0 * R * self.k0 * (math.sin(chi) * math.cos(chi0)
                                                 - math.cos(chi) * math.sin(chi0) * math.cos(dl)) / B
        return E, N

    def inverse(self, E: float, N: float) -> Tuple[float, float]:
        """(Easting, Northing) m -> (lat, lon) rad."""
        e = self.ell.e
        e2 = self.ell.e2
        R, n, c, chi0 = self._consts()
        Lam0 = self.lon0
        dE = E - self.false_e
        dN = N - self.false_n
        g = 2.0 * R * self.k0 * math.tan(math.pi / 4.0 - chi0 / 2.0)
        h = 4.0 * R * self.k0 * math.tan(chi0) + g
        i = math.atan2(dE, h + dN)
        j = math.atan2(dE, g - dN) - i
        chi = chi0 + 2.0 * math.atan((dN - dE * math.tan(j / 2.0)) / (2.0 * R * self.k0))
        Lam = j + 2.0 * i + Lam0
        lon = (Lam - Lam0) / n + Lam0
        # isometric latitude on the sphere -> ellipsoid, iterate
        psi = 0.5 * math.log((1.0 + math.sin(chi)) / (c * (1.0 - math.sin(chi)))) / n
        lat = 2.0 * math.atan(math.exp(psi)) - math.pi / 2.0
        for _ in range(30):
            s = math.sin(lat)
            psi_i = math.log(math.tan(lat / 2.0 + math.pi / 4.0) * ((1.0 - e * s) / (1.0 + e * s)) ** (e / 2.0))
            new = lat - (psi_i - psi) * math.cos(lat) * (1.0 - e2 * s * s) / (1.0 - e2)
            if abs(new - lat) < 1e-14:
                lat = new
                break
            lat = new
        return lat, lon
