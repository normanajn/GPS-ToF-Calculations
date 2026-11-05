"""gps_tof: geodetic time-of-flight calculations between surveyed sites.

The package turns a set of site coordinates (GPS antenna fixes, Fermilab site
coordinates, or NMEA sentences) into straight-line (chord) flight paths,
times of flight in SI and clock-tick units, and a ledger of every correction
applied on the way, together with sensitivities and an error budget.
"""

__version__ = "0.5.0"

from .model import Site, Baseline, TimingShift, OpeningAngle, BeamAxis, Settings  # noqa: F401
from .calc import compute_baseline, compute_opening_angle, compute_all  # noqa: F401
