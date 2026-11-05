"""Physical constants, ellipsoid parameters and default time bases."""
import math

C = 299792458.0                     # speed of light, m/s (exact)
OMEGA_EARTH = 7.2921150e-5          # Earth rotation rate, rad/s (IERS)
ARCSEC = math.pi / (180.0 * 3600.0)  # rad per arcsecond
FOOT = 0.3048                       # international foot, m (DUSAF uses US survey ft = 0.3048006096 m)
US_SURVEY_FOOT = 1200.0 / 3937.0    # 0.30480060960... m

# WGS84 / GRS80.  GPS fixes are WGS84; Fermilab site surveys are NAD83/GRS80.
# The two ellipsoids differ in b by 0.1 mm, irrelevant here.
WGS84_A = 6378137.0
WGS84_B = 6356752.31424518
WGS84_INV_F = 298.257223563
GRS80_A = 6378137.0
GRS80_INV_F = 298.257222101

DEFAULT_CLOCK_HZ = 64.0e6           # NOvA timing-system clock
DEFAULT_LEGACY_UNIT_S = 500.0e-9    # legacy Global Trigger unit
