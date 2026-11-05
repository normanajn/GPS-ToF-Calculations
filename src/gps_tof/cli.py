"""Command-line entry points: gps-tof, gps-tof-nmea, gps-tof-fscs."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from . import __version__
from .angles import parse_angle, dms
from .calc import compute_all
from .config import merge, default_config_path, SCALARS
from .model import Problem
from .report import render
from . import nmea as nmea_mod
from . import fermilab_site


def _add_setting_args(p: argparse.ArgumentParser):
    g = p.add_argument_group("settings overrides (command line > environment > .env > config file)")
    g.add_argument("--project", help="report title")
    g.add_argument("--clock-hz", dest="clock_hz", type=float, help="tick clock frequency (default 64e6)")
    g.add_argument("--legacy-unit-s", dest="legacy_unit_s", type=float, help="legacy time unit in s (default 500e-9)")
    g.add_argument("--earth-model", dest="earth_model", choices=["wgs84", "grs80", "sphere"])
    g.add_argument("--sphere-radius-m", dest="sphere_radius_m", type=float)
    g.add_argument("--offset-normal", dest="offset_normal", choices=["geodetic", "radial"],
                   help="'up' direction used for antenna->endpoint offsets")
    g.add_argument("--apply-sagnac", dest="apply_sagnac", action="store_const", const=True, default=None,
                   help="add the Sagnac term to the total")
    g.add_argument("--rounding", choices=["round", "floor", "ceil"])
    g.add_argument("--precision-digits", dest="precision_digits", type=int)
    g.add_argument("--neutrino-mass-ev", dest="neutrino_mass_ev", type=float)
    g.add_argument("--neutrino-energy-gev", dest="neutrino_energy_gev", type=float)
    g.add_argument("--window-before-us", dest="window_before_us", type=float)
    g.add_argument("--window-after-us", dest="window_after_us", type=float)
    g.add_argument("--microslice-us", dest="microslice_us", type=float)
    g.add_argument("--no-sensitivities", dest="sensitivities", action="store_const", const=False, default=None)
    g.add_argument("--arcsec-step", dest="arcsec_step", type=float)
    g.add_argument("--height-step-m", dest="height_step_m", type=float)
    g.add_argument("--offset-step-m", dest="offset_step_m", type=float)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gps-tof",
        description="Straight-line time of flight between surveyed sites, with a ledger of every "
                    "correction, sensitivities and an error budget.",
        epilog="Example: gps-tof -c config/nova.yaml --format md -o report")
    p.add_argument("-c", "--config", help="YAML configuration (default: config/gps-tof.yaml or config/nova.yaml)")
    p.add_argument("-s", "--site", action="append", metavar="SPEC",
                   help="add a site: 'name=X lat=41:50:23N lon=88:16:13W h=228 [datum=msl geoid=-33] "
                        "[offset=E,N,U] [fscs=x,y,z] [id=..] [u_lat_arcsec=..]'  (repeatable)")
    p.add_argument("-p", "--pair", action="append", metavar="FROM:TO[:LABEL[:AXIS]]",
                   help="baseline between two site ids (repeatable; default: every pair of sites)")
    p.add_argument("--nmea", action="append", metavar="FILE", help="add sites from $GPGGA sentences in FILE")
    p.add_argument("--no-timing-shifts", action="store_true", help="ignore timing_shifts from the config")
    p.add_argument("-f", "--format", choices=["text", "md", "json", "all"], help="output format (default text)")
    p.add_argument("-o", "--output", help="write report to this path (with --format all: base name)")
    p.add_argument("--dump-config", action="store_true", help="print the merged configuration as YAML and exit")
    p.add_argument("--list-sites", action="store_true", help="print the resolved sites and exit")
    p.add_argument("-V", "--version", action="version", version="gps-tof " + __version__)
    _add_setting_args(p)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    p = build_parser()
    a = p.parse_args(argv)
    cli: Dict[str, Any] = {k: getattr(a, k) for k in SCALARS}
    cli.update({"config": a.config, "format": a.format, "output": a.output, "site": a.site, "pair": a.pair,
                "no_timing_shifts": a.no_timing_shifts})
    extra = []
    for f in a.nmea or []:
        txt = Path(f).read_text(encoding="utf-8", errors="replace")
        extra.extend(nmea_mod.sites_from_text(txt, name_prefix=Path(f).stem))
    cli["extra_sites"] = extra
    try:
        merged = merge(default_config_path(), cli)
        if a.dump_config:
            sys.stdout.write(yaml.safe_dump(merged["problem"], sort_keys=False, allow_unicode=True))
            return 0
        problem = Problem.from_dict(merged["problem"])
    except (ValueError, KeyError, OSError) as e:
        p.error(str(e))
        return 2
    if a.list_sites:
        for s in problem.sites:
            print("%-14s %-36s %s %s h=%.3f (%s) offset=%s" % (s.id, s.name, dms(s.lat, "lat"), dms(s.lon, "lon"),
                                                               s.height_m, s.datum, s.offset_enu_m))
        return 0
    result = compute_all(problem)
    fmt = merged["run"].get("format") or "text"
    out = merged["run"].get("output")
    if fmt == "all":
        if not out:
            p.error("--format all needs --output BASE")
        base = Path(out)
        for f, ext in (("md", ".md"), ("text", ".txt"), ("json", ".json")):
            path = base.with_suffix(ext) if base.suffix in (".md", ".txt", ".json") else Path(str(base) + ext)
            path.write_text(render(result, f), encoding="utf-8")
            print("wrote", path)
        return 0
    text = render(result, fmt)
    if out:
        Path(out).write_text(text, encoding="utf-8")
        print("wrote", out)
    else:
        sys.stdout.write(text)
    return 0


# ------------------------------------------------------------ gps-tof-nmea
def main_nmea(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="gps-tof-nmea",
                                description="Validate NMEA 0183 checksums, decode $GPGGA fixes and print "
                                            "gps-tof site entries (YAML) for them.")
    p.add_argument("files", nargs="*", help="files with NMEA sentences (default: stdin)")
    p.add_argument("--yaml", action="store_true", help="print only the YAML site entries")
    p.add_argument("--name", default=None, help="name prefix for generated sites")
    p.add_argument("-V", "--version", action="version", version="gps-tof-nmea " + __version__)
    a = p.parse_args(argv)
    texts = [Path(f).read_text(encoding="utf-8", errors="replace") for f in a.files] if a.files else [sys.stdin.read()]
    bad = 0
    all_sites = []
    for name, txt in zip(a.files or ["stdin"], texts):
        if not a.yaml:
            print("== %s" % name)
            for line in txt.splitlines():
                line = line.strip()
                if not line.startswith("$"):
                    continue
                ok = nmea_mod.check(line)
                tag = "no checksum" if ok is None else ("valid" if ok else "INVALID (computed %s)" % nmea_mod.checksum(line))
                if ok is False:
                    bad += 1
                print("  %-7s %s" % (line[:6], tag))
                if "GGA" in line[:6] and ok is not False:
                    g = nmea_mod.parse_gga(line)
                    print("          %s UTC  lat %.8f  lon %.8f  fix %s  sats %s  HDOP %s  H(MSL) %s m  N %s m  h %s m" % (
                        g["utc"], g["lat_deg"], g["lon_deg"], g["fix_quality"], g["satellites"], g["hdop"],
                        g["msl_altitude_m"], g["geoid_separation_m"], g["ellipsoidal_height_m"]))
                if "RMC" in line[:6]:
                    print("          date %s" % nmea_mod.parse_rmc_date(line))
        all_sites.extend(nmea_mod.sites_from_text(txt, a.name or Path(name).stem))
    if all_sites:
        if not a.yaml:
            print("\n# gps-tof site entries:")
        sys.stdout.write(yaml.safe_dump({"sites": all_sites}, sort_keys=False, allow_unicode=True))
    return 1 if bad else 0


# ------------------------------------------------------------ gps-tof-fscs
def main_fscs(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="gps-tof-fscs",
                                description="Convert between Fermilab site coordinates (FSCS/DUSAF, US survey "
                                            "feet) and geodetic NAD83/WGS84 coordinates (Beams-doc-1148).")
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("to-geodetic", help="x y z (ft) -> lat lon h")
    g.add_argument("x", type=float); g.add_argument("y", type=float); g.add_argument("z", type=float)
    g.add_argument("--geoid", type=float, default=fermilab_site.GEOID_N_A0_M, help="geoid separation N (m)")
    f = sub.add_parser("from-geodetic", help="lat lon h(ellipsoidal, m) -> x y z (ft)")
    f.add_argument("lat"); f.add_argument("lon"); f.add_argument("h", type=float)
    f.add_argument("--geoid", type=float, default=fermilab_site.GEOID_N_A0_M)
    b = sub.add_parser("bearing", help="beam-sheet bearing (deg ccw from site East) -> geodetic azimuth")
    b.add_argument("bearing", type=float)
    p.add_argument("-V", "--version", action="version", version="gps-tof-fscs " + __version__)
    a = p.parse_args(argv)
    if a.cmd == "to-geodetic":
        lat, lon, h = fermilab_site.fscs_to_geodetic(a.x, a.y, a.z, a.geoid)
        print("lat %.9f  (%s)" % (lat, dms(lat, "lat")))
        print("lon %.9f  (%s)" % (lon, dms(lon, "lon")))
        print("h   %.4f m ellipsoidal   (H = %.4f m NAVD88, N = %.5f m)" % (h, h - a.geoid, a.geoid))
    elif a.cmd == "from-geodetic":
        x, y, z = fermilab_site.geodetic_to_fscs(parse_angle(a.lat, "lat"), parse_angle(a.lon, "lon"), a.h, a.geoid)
        print("x %.4f ft  y %.4f ft  z %.4f ft (DUSAF datum)" % (x, y, z))
    else:
        print("geodetic azimuth %.5f deg" % fermilab_site.fscs_bearing_to_azimuth(a.bearing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
