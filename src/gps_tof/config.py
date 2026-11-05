"""Configuration: YAML file < .env < environment < command line.

Environment variables are prefixed ``GPS_TOF_`` and map onto the scalar
settings (``GPS_TOF_CLOCK_HZ``, ``GPS_TOF_EARTH_MODEL``, ...), plus
``GPS_TOF_CONFIG``, ``GPS_TOF_FORMAT`` and ``GPS_TOF_OUTPUT``.
"""
from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .angles import parse_angle

ENV_PREFIX = "GPS_TOF_"

# settings that may be overridden by environment / command line, with their type
SCALARS: Dict[str, type] = {
    "project": str, "clock_hz": float, "legacy_unit_s": float, "earth_model": str,
    "sphere_radius_m": float, "offset_normal": str, "apply_sagnac": bool, "rounding": str,
    "precision_digits": int, "neutrino_mass_ev": float, "neutrino_energy_gev": float,
    "window_before_us": float, "window_after_us": float, "microslice_us": float,
    "sensitivities": bool, "report_axis": bool, "arcsec_step": float, "height_step_m": float, "offset_step_m": float,
}
RUN_KEYS: Dict[str, type] = {"config": str, "format": str, "output": str}


def _coerce(v: str, typ: type) -> Any:
    if typ is bool:
        return str(v).strip().lower() in ("1", "true", "yes", "on")
    return typ(v)


def read_dotenv(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if k.startswith("export "):
            k = k[7:].strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        out[k] = v
    return out


def env_overrides(environ: Dict[str, str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, typ in list(SCALARS.items()) + list(RUN_KEYS.items()):
        name = ENV_PREFIX + key.upper()
        if name in environ and environ[name] != "":
            out[key] = _coerce(environ[name], typ)
    return out


def load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        d = yaml.safe_load(f) or {}
    if not isinstance(d, dict):
        raise ValueError("%s: top level must be a mapping" % path)
    return d


def default_config_path() -> Optional[Path]:
    for cand in (Path("config/gps-tof.yaml"), Path("config/nova.yaml")):
        if cand.is_file():
            return cand
    return None


def parse_site_spec(spec: str) -> Dict[str, Any]:
    """``name=FNAL lat=41:50:23N lon=88:16:13W h=228 datum=msl geoid=-33 offset=0,0,-120``
    (shell-style quoting allowed, e.g. name="Ash River Ant-2")."""
    d: Dict[str, Any] = {}
    for tok in shlex.split(spec):
        if "=" not in tok:
            raise ValueError("site spec token %r is not key=value" % tok)
        k, v = tok.split("=", 1)
        k = k.strip().lower()
        if k in ("name", "id", "datum", "note", "offset_note", "source", "notes"):
            d["offset_note" if k == "note" else k] = v
        elif k == "lat":
            d["lat"] = parse_angle(v, "lat")
        elif k == "lon":
            d["lon"] = parse_angle(v, "lon")
        elif k in ("h", "height", "height_m"):
            d["height_m"] = float(v)
        elif k in ("geoid", "geoid_separation_m", "ng"):
            d["geoid_separation_m"] = float(v)
        elif k in ("offset", "offset_enu_m"):
            d["offset_enu_m"] = [float(x) for x in v.split(",")]
        elif k in ("fscs", "fscs_xyz_ft", "dusaf"):
            d["fscs_xyz_ft"] = [float(x) for x in v.split(",")]
        elif k in ("cable_m", "cable_length_m"):
            d["cable_length_m"] = float(v)
        elif k in ("vf", "cable_velocity_factor"):
            d["cable_velocity_factor"] = float(v)
        elif k == "cable_delay_ns":
            d["cable_delay_ns"] = float(v)
        elif k.startswith("u_"):
            d.setdefault("uncertainty", {})[k[2:]] = float(v)
        else:
            raise ValueError("unknown site spec key %r" % k)
    if "name" not in d:
        raise ValueError("site spec needs name=...")
    if "fscs_xyz_ft" not in d and ("lat" not in d or "lon" not in d):
        raise ValueError("site %s: give lat= and lon=, or fscs=x,y,z" % d["name"])
    return d


def parse_pair_spec(spec: str) -> Dict[str, str]:
    parts = spec.split(":")
    if len(parts) < 2:
        raise ValueError("pair spec must be FROM:TO[:LABEL[:AXIS_TO]]")
    d = {"from": parts[0], "to": parts[1]}
    if len(parts) > 2 and parts[2]:
        d["label"] = parts[2]
    if len(parts) > 3 and parts[3]:
        d["axis_to"] = parts[3]
    return d


def parse_angle_spec(spec: str) -> Dict[str, str]:
    parts = spec.split(":")
    if len(parts) < 3:
        raise ValueError("angle spec must be VERTEX:A:B[:LABEL[:AXIS_TO]]")
    d = {"vertex": parts[0], "a": parts[1], "b": parts[2]}
    if len(parts) > 3 and parts[3]:
        d["label"] = parts[3]
    if len(parts) > 4 and parts[4]:
        d["axis_to"] = parts[4]
    return d


def merge(config_path: Optional[Path], cli: Dict[str, Any], environ: Optional[Dict[str, str]] = None,
          dotenv_paths: Optional[List[Path]] = None) -> Dict[str, Any]:
    """Return the merged problem dict plus run keys, applying the override order
    command line > environment > .env > config file > defaults."""
    environ = dict(os.environ if environ is None else environ)
    dotenv: Dict[str, str] = {}
    for p in (dotenv_paths or [Path(".env"), Path("config/.env")]):
        dotenv.update(read_dotenv(p))
    layered = dict(dotenv)
    layered.update(environ)           # real environment beats .env
    ov = env_overrides(layered)
    run = {k: ov.pop(k) for k in list(RUN_KEYS) if k in ov}
    cfg_path = cli.get("config") or run.get("config") or (config_path.as_posix() if config_path else None)
    data: Dict[str, Any] = load_yaml(Path(cfg_path)) if cfg_path else {}
    data.update(ov)
    for k in SCALARS:
        if cli.get(k) is not None:
            data[k] = cli[k]
    sites = list(data.get("sites") or [])
    for spec in cli.get("site") or []:
        sites.append(parse_site_spec(spec))
    for d in cli.get("extra_sites") or []:
        sites.append(d)
    data["sites"] = sites
    if cli.get("pair"):
        data["baselines"] = [parse_pair_spec(p) for p in cli["pair"]]
    if cli.get("axis"):
        parts = cli["axis"].split(":")
        if len(parts) < 2:
            raise ValueError("axis spec must be ORIGIN:THROUGH[:LABEL]")
        data["beam_axis"] = {"from": parts[0], "to": parts[1], "label": parts[2] if len(parts) > 2 else ""}
    if cli.get("no_axis"):
        data["report_axis"] = False
    if cli.get("angle"):
        data["opening_angles"] = [parse_angle_spec(x) for x in cli["angle"]]
    if cli.get("no_timing_shifts"):
        data["timing_shifts"] = []
    for k in RUN_KEYS:
        if cli.get(k) is not None:
            run[k] = cli[k]
    run.setdefault("config", cfg_path)
    return {"problem": data, "run": run}
