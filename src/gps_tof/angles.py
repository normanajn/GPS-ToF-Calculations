"""Angle parsing and formatting.

Accepted input forms for a latitude or longitude (all return decimal degrees):

* a number: ``41.839722`` (sign gives hemisphere)
* decimal with hemisphere: ``"41.839722 N"``, ``"88.270278W"``
* degrees minutes seconds: ``"41 50 23 N"``, ``"41:50:23N"``, ``"41d50m23sN"``,
  ``"41°50'23\"N"``, ``"-88 16 13"``
* degrees and decimal minutes: ``"48 22.715780 N"``, ``"92:49.876930 W"``
* NMEA ddmm.mmmm with a hemisphere field: use :func:`parse_nmea`
"""
from __future__ import annotations

import math
import re
from typing import Optional, Tuple, Union

_HEMI = {"N": 1.0, "S": -1.0, "E": 1.0, "W": -1.0}
_CLEAN = re.compile(r"[°º˚'′’\"″dDmMsS:]")


def parse_angle(value: Union[str, float, int], kind: Optional[str] = None) -> float:
    """Parse an angle to decimal degrees.  ``kind`` ('lat' or 'lon') is only used
    to validate the hemisphere letter and the range."""
    if isinstance(value, (int, float)):
        deg = float(value)
    else:
        s = str(value).strip().upper()
        if not s:
            raise ValueError("empty angle")
        sign = 1.0
        hemi = None
        if s[0] in _HEMI:
            hemi, s = s[0], s[1:]
        elif s[-1] in _HEMI:
            hemi, s = s[-1], s[:-1]
        if hemi is not None:
            sign = _HEMI[hemi]
            if kind == "lat" and hemi not in "NS":
                raise ValueError("latitude with hemisphere %r: %r" % (hemi, value))
            if kind == "lon" and hemi not in "EW":
                raise ValueError("longitude with hemisphere %r: %r" % (hemi, value))
        s = _CLEAN.sub(" ", s).strip()
        if s.startswith("-"):
            if hemi is not None:
                raise ValueError("both a sign and a hemisphere in %r" % (value,))
            sign = -1.0
            s = s[1:]
        elif s.startswith("+"):
            s = s[1:]
        parts = s.split()
        if not 1 <= len(parts) <= 3:
            raise ValueError("cannot parse angle %r" % (value,))
        try:
            nums = [float(p) for p in parts]
        except ValueError:
            raise ValueError("cannot parse angle %r" % (value,))
        if len(nums) > 1 and not (0 <= nums[1] < 60):
            raise ValueError("minutes out of range in %r" % (value,))
        if len(nums) > 2 and not (0 <= nums[2] < 60):
            raise ValueError("seconds out of range in %r" % (value,))
        deg = nums[0]
        if len(nums) > 1:
            deg += nums[1] / 60.0
        if len(nums) > 2:
            deg += nums[2] / 3600.0
        deg *= sign
    if kind == "lat" and not -90.0 <= deg <= 90.0:
        raise ValueError("latitude out of range: %r" % (value,))
    if kind == "lon" and not -180.0 <= deg <= 360.0:
        raise ValueError("longitude out of range: %r" % (value,))
    return deg


def parse_nmea(field: str, hemisphere: str) -> float:
    """NMEA ``ddmm.mmmm`` / ``dddmm.mmmm`` with hemisphere letter -> degrees."""
    v = float(field)
    d = math.floor(v / 100.0)
    deg = d + (v - 100.0 * d) / 60.0
    return deg * _HEMI[hemisphere.strip().upper()]


def dms(deg: float, kind: str = "lat", sec_digits: int = 4) -> str:
    """Format decimal degrees as D° M' S.ssss" H."""
    hemi = ("N" if deg >= 0 else "S") if kind == "lat" else ("E" if deg >= 0 else "W")
    a = abs(deg)
    d = int(a)
    m_full = (a - d) * 60.0
    m = int(m_full)
    s = (m_full - m) * 60.0
    s = round(s, sec_digits)
    if s >= 60.0:
        s -= 60.0
        m += 1
    if m >= 60:
        m -= 60
        d += 1
    return "%d° %02d' %0*.*f\" %s" % (d, m, sec_digits + 3, sec_digits, s, hemi)


def split_dm(deg: float) -> Tuple[int, float]:
    a = abs(deg)
    d = int(a)
    return d, (a - d) * 60.0
