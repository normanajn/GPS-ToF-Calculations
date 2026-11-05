"""NMEA 0183 helpers: checksum, $GPGGA / $GPRMC decoding, site extraction."""
from __future__ import annotations

from typing import Dict, List, Optional

from .angles import parse_nmea


def checksum(sentence: str) -> str:
    s = sentence.strip()
    body = s[1:s.index("*")] if "*" in s else s[1:]
    x = 0
    for ch in body:
        x ^= ord(ch)
    return "%02X" % x


def check(sentence: str) -> Optional[bool]:
    """True/False if the sentence carries a checksum, None if it has none."""
    s = sentence.strip()
    if "*" not in s:
        return None
    stated = s[s.index("*") + 1:s.index("*") + 3].upper()
    return stated == checksum(s)


def _f(x: str) -> Optional[float]:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def parse_gga(sentence: str) -> Dict[str, object]:
    """Decode a $--GGA sentence.  Altitude is orthometric (MSL); the geoid
    separation field gives h = H + N."""
    s = sentence.strip()
    if "*" in s:
        s = s[:s.index("*")]
    f = s.split(",")
    if len(f) < 12 or not f[0].endswith("GGA"):
        raise ValueError("not a GGA sentence: %r" % sentence)
    lat = parse_nmea(f[2], f[3]) if f[2] else None
    lon = parse_nmea(f[4], f[5]) if f[4] else None
    H = _f(f[9])
    Ng = _f(f[11])
    out = {
        "sentence": f[0], "utc": f[1], "lat_deg": lat, "lon_deg": lon,
        "fix_quality": int(f[6]) if f[6] else None,
        "satellites": int(f[7]) if f[7] else None,
        "hdop": _f(f[8]), "msl_altitude_m": H, "geoid_separation_m": Ng,
        "ellipsoidal_height_m": (H + Ng) if (H is not None and Ng is not None) else None,
        "checksum_ok": check(sentence),
    }
    return out


def parse_rmc_date(sentence: str) -> Optional[str]:
    f = sentence.strip().split(",")
    if len(f) > 9 and f[0].endswith("RMC") and len(f[9]) == 6:
        d = f[9]
        return "20%s-%s-%s" % (d[4:6], d[2:4], d[0:2])
    return None


def sites_from_text(text: str, name_prefix: str = "GGA fix") -> List[Dict[str, object]]:
    """Return one site dict (config-schema keys) per GGA sentence found."""
    out = []
    n = 0
    for line in text.splitlines():
        line = line.strip()
        if "GGA" in line and line.startswith("$"):
            g = parse_gga(line)
            if g["lat_deg"] is None:
                continue
            n += 1
            d = {
                "name": "%s %d (%s UTC)" % (name_prefix, n, g["utc"]),
                "lat": g["lat_deg"], "lon": g["lon_deg"],
                "height_m": g["msl_altitude_m"], "datum": "msl",
                "geoid_separation_m": g["geoid_separation_m"],
                "source": line,
            }
            out.append(d)
    return out
