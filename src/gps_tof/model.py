"""Input model: sites, baselines, timing shifts and run settings."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

from .angles import parse_angle
from .constants import (DEFAULT_CLOCK_HZ, DEFAULT_LEGACY_UNIT_S, C, WGS84_A)
from . import fermilab_site


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


@dataclass
class Site:
    """A surveyed point plus the displacement to the physics endpoint.

    Coordinates are given either geodetically (lat, lon, height) or as
    Fermilab site coordinates (fscs_xyz_ft).  ``datum`` says what ``height_m``
    is: 'ellipsoid' (WGS84 h, what the transform needs) or 'msl' (orthometric
    H; then h = H + geoid_separation_m).  ``offset_enu_m`` is the vector from
    the surveyed point to the endpoint (e.g. antenna -> detector front-face
    centre) in the local East/North/Up frame, metres; a detector 120 m below
    the antenna is (0, 0, -120).
    """
    name: str
    lat: float = 0.0            # decimal degrees
    lon: float = 0.0            # decimal degrees, east positive
    height_m: float = 0.0
    datum: str = "ellipsoid"
    geoid_separation_m: Optional[float] = None
    offset_enu_m: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    offset_note: str = ""
    id: str = ""
    fscs_xyz_ft: Optional[Tuple[float, float, float]] = None
    axis_position: Optional[Dict[str, Any]] = None   # along_m + (right_m, up_m | off_axis_mrad, clock_deg) [+ frame]
    face: Optional[Dict[str, float]] = None           # {half_width_m[, half_height_m]}: derives edge sites
    derived_from: str = ""                           # parent site id for derived edge points
    edge: str = ""                                   # left | right | top | bottom
    cable_length_m: Optional[float] = None
    cable_velocity_factor: Optional[float] = None
    cable_delay_ns: Optional[float] = None
    uncertainty: Dict[str, float] = field(default_factory=dict)
    source: str = ""
    notes: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = _slug(self.name)
        if self.datum not in ("ellipsoid", "msl"):
            raise ValueError("site %s: datum must be 'ellipsoid' or 'msl'" % self.name)
        if self.datum == "msl" and self.geoid_separation_m is None:
            raise ValueError("site %s: datum 'msl' needs geoid_separation_m" % self.name)
        self.offset_enu_m = tuple(float(x) for x in self.offset_enu_m)
        if len(self.offset_enu_m) != 3:
            raise ValueError("site %s: offset_enu_m needs three values" % self.name)
        if self.fscs_xyz_ft is not None:
            x, y, z = (float(v) for v in self.fscs_xyz_ft)
            self.fscs_xyz_ft = (x, y, z)
            lat, lon, h = fermilab_site.fscs_to_geodetic(x, y, z)
            self.lat, self.lon, self.height_m = lat, lon, h
            self.datum = "ellipsoid"
            self.geoid_separation_m = fermilab_site.GEOID_N_A0_M

    # heights -------------------------------------------------------------
    @property
    def h_ellipsoidal(self) -> float:
        if self.datum == "msl":
            return self.height_m + float(self.geoid_separation_m)
        return self.height_m

    @property
    def lat_rad(self) -> float:
        return math.radians(self.lat)

    @property
    def lon_rad(self) -> float:
        return math.radians(self.lon)

    @property
    def cable_delay_s(self) -> Optional[float]:
        if self.cable_delay_ns is not None:
            return self.cable_delay_ns * 1e-9
        if self.cable_length_m is not None:
            vf = self.cable_velocity_factor or 0.66
            return self.cable_length_m / (vf * C)
        return None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Site":
        d = dict(d)
        name = d.pop("name")
        kw: Dict[str, Any] = {}
        if d.get("axis_position") is not None:
            raw = dict(d.pop("axis_position"))
            frame = raw.pop("frame", None)
            ap: Dict[str, Any] = {k: float(v) for k, v in raw.items()}
            if frame is not None:
                if not isinstance(frame, dict) or "origin" not in frame or "through" not in frame:
                    raise ValueError("site %s: axis_position.frame needs origin and through site ids" % name)
                ap["frame_origin"] = str(frame["origin"])
                ap["frame_through"] = str(frame["through"])
            if "along_m" not in ap:
                raise ValueError("site %s: axis_position needs along_m" % name)
            if not (("right_m" in ap and "up_m" in ap) or ("off_axis_mrad" in ap and "clock_deg" in ap)):
                raise ValueError("site %s: axis_position needs right_m+up_m or off_axis_mrad+clock_deg" % name)
            kw["axis_position"] = ap
            d.pop("lat", None); d.pop("lon", None); d.pop("height_m", None); d.pop("fscs_xyz_ft", None)
            kw["lat"], kw["lon"], kw["height_m"] = 0.0, 0.0, 0.0   # resolved by Problem.from_dict
        elif "fscs_xyz_ft" in d and d["fscs_xyz_ft"] is not None:
            kw["fscs_xyz_ft"] = tuple(d.pop("fscs_xyz_ft"))
            d.pop("lat", None); d.pop("lon", None); d.pop("height_m", None)
        else:
            kw["lat"] = parse_angle(d.pop("lat"), "lat")
            kw["lon"] = parse_angle(d.pop("lon"), "lon")
            kw["height_m"] = float(d.pop("height_m", 0.0))
        for k in ("geoid_separation_m", "cable_length_m", "cable_velocity_factor", "cable_delay_ns"):
            if d.get(k) is not None:
                d[k] = float(d[k])
        if d.get("uncertainty"):
            d["uncertainty"] = {k: float(v) for k, v in d["uncertainty"].items()}
        if d.get("face") is not None:
            face = {k: float(v) for k, v in dict(d.pop("face")).items()}
            if "half_width_m" not in face and "half_height_m" not in face:
                raise ValueError("site %s: face needs half_width_m and/or half_height_m" % name)
            kw["face"] = face
        for k in ("datum", "geoid_separation_m", "offset_enu_m", "offset_note", "id",
                  "cable_length_m", "cable_velocity_factor", "cable_delay_ns",
                  "uncertainty", "source", "notes", "derived_from", "edge"):
            if k in d and d[k] is not None:
                kw[k] = d.pop(k)
        if "offset_enu_m" in kw:
            kw["offset_enu_m"] = tuple(float(x) for x in kw["offset_enu_m"])
        if d:
            raise ValueError("site %s: unknown keys %s" % (name, sorted(d)))
        return cls(name=name, **kw)

    def replace(self, **changes) -> "Site":
        d = asdict(self)
        d.pop("fscs_xyz_ft", None)   # already folded into lat/lon/h
        d.pop("axis_position", None)  # already resolved to lat/lon/h
        d.pop("face", None)
        d.update(changes)
        return Site(**d)


@dataclass
class Baseline:
    source: str          # site id of the emitter / upstream end
    target: str          # site id of the receiver / downstream end
    label: str = ""
    axis_to: str = ""    # optional site id defining a reference axis from the source (off-axis angle)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Baseline":
        return cls(source=str(d["from"]), target=str(d["to"]), label=str(d.get("label", "")),
                   axis_to=str(d.get("axis_to", "") or ""))


@dataclass
class BeamAxis:
    """Reference axis: the line from site ``origin`` through site ``through``
    (for NuMI: target -> MINOS far detector).  Every site, baseline and opening
    angle is reported relative to it."""
    origin: str
    through: str
    label: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BeamAxis":
        return cls(origin=str(d.get("from", d.get("origin"))), through=str(d.get("to", d.get("through"))),
                   label=str(d.get("label", "")))


@dataclass
class OpeningAngle:
    """Angle at ``vertex`` between the chords vertex->a and vertex->b."""
    vertex: str
    a: str
    b: str
    label: str = ""
    axis_to: str = ""    # optional site defining a reference axis from the vertex

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "OpeningAngle":
        return cls(vertex=str(d["vertex"]), a=str(d["a"]), b=str(d["b"]), label=str(d.get("label", "")),
                   axis_to=str(d.get("axis_to", "") or ""))


@dataclass
class TimingShift:
    """A fixed offset added to the flight time (e.g. an accelerator timing
    reference change).  Give either ``seconds`` or turns*buckets/rf_hz."""
    name: str
    seconds: Optional[float] = None
    turns: Optional[float] = None
    buckets_per_turn: Optional[float] = None
    rf_hz: Optional[float] = None
    rf_uncertainty_hz: Optional[float] = None
    notes: str = ""

    @property
    def t_rev_s(self) -> Optional[float]:
        if self.buckets_per_turn is not None and self.rf_hz:
            return self.buckets_per_turn / self.rf_hz
        return None

    @property
    def value_s(self) -> float:
        if self.seconds is not None:
            return float(self.seconds)
        if self.turns is not None and self.t_rev_s is not None:
            return self.turns * self.t_rev_s
        raise ValueError("timing shift %s: give seconds or turns+buckets_per_turn+rf_hz" % self.name)

    @property
    def rf_sensitivity_s_per_hz(self) -> Optional[float]:
        """d(shift)/d(f_RF) = -shift / f_RF"""
        if self.turns is not None and self.rf_hz:
            return -self.value_s / self.rf_hz
        return None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TimingShift":
        d = dict(d)
        for k in ("seconds", "turns", "buckets_per_turn", "rf_hz", "rf_uncertainty_hz"):
            if d.get(k) is not None:
                d[k] = float(d[k])
        return cls(**d)


@dataclass
class Settings:
    project: str = "GPS time-of-flight"
    clock_hz: float = DEFAULT_CLOCK_HZ
    legacy_unit_s: float = DEFAULT_LEGACY_UNIT_S
    earth_model: str = "wgs84"            # wgs84 | grs80 | sphere
    sphere_radius_m: float = WGS84_A
    offset_normal: str = "geodetic"       # geodetic | radial
    apply_sagnac: bool = False
    rounding: str = "round"               # round | floor | ceil
    precision_digits: int = 4
    neutrino_mass_ev: Optional[float] = None
    neutrino_energy_gev: Optional[float] = None
    window_before_us: Optional[float] = None
    window_after_us: Optional[float] = None
    microslice_us: Optional[float] = None
    sensitivities: bool = True
    report_axis: bool = True              # False: keep beam_axis for resolving axis_position sites, but do not report it
    arcsec_step: float = 1.0
    height_step_m: float = 1.0
    offset_step_m: float = 1.0
    notes: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Settings":
        d = dict(d)
        earth = d.pop("earth", None) or {}
        if "model" in earth:
            d["earth_model"] = earth["model"]
        if "sphere_radius_m" in earth:
            d["sphere_radius_m"] = earth["sphere_radius_m"]
        phys = d.pop("physics", None) or {}
        for k in ("neutrino_mass_ev", "neutrino_energy_gev"):
            if k in phys:
                d[k] = phys[k]
        win = d.pop("trigger_window", None) or {}
        for k, dst in (("before_us", "window_before_us"), ("after_us", "window_after_us"),
                       ("microslice_us", "microslice_us")):
            if k in win:
                d[dst] = win[k]
        sens = d.pop("sensitivity", None) or {}
        for k, dst in (("enabled", "sensitivities"), ("arcsec_step", "arcsec_step"),
                       ("height_step_m", "height_step_m"), ("offset_step_m", "offset_step_m")):
            if k in sens:
                d[dst] = sens[k]
        fields = cls.__dataclass_fields__  # type: ignore[attr-defined]
        unknown = set(d) - set(fields)
        if unknown:
            raise ValueError("unknown settings keys: %s" % sorted(unknown))
        # YAML 1.1 reads "64.0e6" as a string (exponent needs a sign); coerce numeric fields
        for k, v in list(d.items()):
            typ = fields[k].type
            if v is None:
                continue
            if "float" in str(typ):
                d[k] = float(v)
            elif "int" in str(typ):
                d[k] = int(v)
            elif "bool" in str(typ) and isinstance(v, str):
                d[k] = v.strip().lower() in ("1", "true", "yes", "on")
        s = cls(**d)
        if s.earth_model not in ("wgs84", "grs80", "sphere"):
            raise ValueError("earth model must be wgs84, grs80 or sphere")
        if s.offset_normal not in ("geodetic", "radial"):
            raise ValueError("offset_normal must be geodetic or radial")
        if s.rounding not in ("round", "floor", "ceil"):
            raise ValueError("rounding must be round, floor or ceil")
        return s


@dataclass
class Problem:
    settings: Settings
    sites: List[Site]
    baselines: List[Baseline]
    timing_shifts: List[TimingShift] = field(default_factory=list)
    opening_angles: List[OpeningAngle] = field(default_factory=list)
    beam_axis: Optional[BeamAxis] = None

    def site(self, key: str) -> Site:
        for s in self.sites:
            if s.id == key or s.name == key:
                return s
        raise KeyError("no site with id or name %r (have %s)" % (key, [s.id for s in self.sites]))

    def _derive_face_edges(self) -> None:
        """For every site with a ``face``, add left/right (and top/bottom) edge
        sites in the same beamline frame (or the global beam-axis frame)."""
        from .calc import axis_frame, point_vs_axis, site_point, final_stage   # lazy
        parents = [s for s in self.sites if s.face]
        if not parents:
            return
        new: List[Site] = []
        for s in parents:
            hw = s.face.get("half_width_m")
            hh = s.face.get("half_height_m")
            edges = []
            if hw:
                edges += [("left", -hw, 0.0), ("right", +hw, 0.0)]
            if hh:
                edges += [("top", 0.0, +hh), ("bottom", 0.0, -hh)]
            if s.axis_position is not None:
                base = dict(s.axis_position)
            else:
                if self.beam_axis is None:
                    raise ValueError("site %s: face edges need beam_axis or an axis_position frame" % s.name)
                frame = axis_frame(self, force=True)
                va = point_vs_axis(site_point(s, self.settings, final_stage(self.settings)), frame)
                base = {"along_m": va["along_axis_m"], "right_m": va["transverse_right_m"], "up_m": va["transverse_up_m"]}
            if "right_m" not in base:   # polar form: convert to right/up first
                r = base["along_m"] * math.tan(base["off_axis_mrad"] * 1e-3)
                base["right_m"] = r * math.sin(math.radians(base["clock_deg"]))
                base["up_m"] = r * math.cos(math.radians(base["clock_deg"]))
                base.pop("off_axis_mrad"); base.pop("clock_deg")
            for edge, dr, du in edges:
                ap = {k: v for k, v in base.items() if k in ("along_m", "right_m", "up_m", "frame_origin", "frame_through")}
                ap["right_m"] = base["right_m"] + dr
                ap["up_m"] = base["up_m"] + du
                new.append(Site(name="%s, %s edge" % (s.name, edge), id="%s-%s" % (s.id, edge),
                                axis_position=ap, uncertainty=dict(s.uncertainty),
                                source=s.source, derived_from=s.id, edge=edge,
                                notes="%+.4f m %s of the face centre in the beamline frame" % (dr if dr else du, "right" if dr else "up")))
        ids = {x.id for x in self.sites}
        for x in new:
            if x.id in ids:
                raise ValueError("derived edge site id %s already exists" % x.id)
        self.sites.extend(new)

    def _resolve_axis_positions(self) -> None:
        """Sites given as (along, right, up) in the beam-axis frame get their
        geodetic coordinates from the axis origin and direction."""
        pending = [s for s in self.sites if s.axis_position is not None]
        if not pending:
            return
        from .calc import axis_frame, frame_from_sites   # lazy: calc imports this module
        from .geodesy import ecef_to_geodetic, WGS84
        global_frame = None
        for s in pending:
            ap = s.axis_position
            if "frame_origin" in ap:
                o, th = self.site(ap["frame_origin"]), self.site(ap["frame_through"])
                for x in (o, th):
                    if x.axis_position is not None:
                        raise ValueError("site %s: frame site %s is itself given in an axis frame" % (s.name, x.name))
                frame = frame_from_sites(self, o, th)
                ap["frame"] = "%s -> %s" % (o.id, th.id)
            else:
                if self.beam_axis is None:
                    raise ValueError("site %s uses axis_position but no beam_axis is defined" % s.name)
                for key in (self.beam_axis.origin, self.beam_axis.through):
                    if self.site(key).axis_position is not None:
                        raise ValueError("beam_axis site %s cannot itself be given in the axis frame" % key)
                if global_frame is None:
                    global_frame = axis_frame(self, force=True)
                frame = global_frame
                ap["frame"] = "%s -> %s" % (self.beam_axis.origin, self.beam_axis.through)
            along = ap["along_m"]
            if "right_m" in ap:
                right, up = ap["right_m"], ap["up_m"]
            else:
                r = along * math.tan(ap["off_axis_mrad"] * 1e-3)
                right, up = r * math.sin(math.radians(ap["clock_deg"])), r * math.cos(math.radians(ap["clock_deg"]))
            u, h, v, p0 = frame["u"], frame["h"], frame["v"], frame["p0"]
            pt = tuple(p0[i] + along * u[i] + right * h[i] + up * v[i] for i in range(3))
            lat, lon, hh = ecef_to_geodetic(pt, WGS84)
            s.lat, s.lon, s.height_m = math.degrees(lat), math.degrees(lon), hh
            s.datum = "ellipsoid"
            s.geoid_separation_m = None
            ap["right_m"], ap["up_m"] = right, up

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Problem":
        d = dict(d)
        sites = [Site.from_dict(s) for s in d.pop("sites", [])]
        if not sites:
            raise ValueError("no sites given")
        ids = [s.id for s in sites]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            raise ValueError("duplicate site ids: %s" % sorted(dup))
        bl = [Baseline.from_dict(b) for b in d.pop("baselines", []) or []]
        if not bl:
            bl = [Baseline(sites[i].id, sites[j].id)
                  for i in range(len(sites)) for j in range(i + 1, len(sites))]
        shifts = [TimingShift.from_dict(t) for t in d.pop("timing_shifts", []) or []]
        angles = [OpeningAngle.from_dict(x) for x in d.pop("opening_angles", []) or []]
        ax = d.pop("beam_axis", None)
        axis = BeamAxis.from_dict(ax) if ax else None
        settings = Settings.from_dict(d)
        p = cls(settings=settings, sites=sites, baselines=bl, timing_shifts=shifts, opening_angles=angles, beam_axis=axis)
        if axis:
            p.site(axis.origin); p.site(axis.through)
            if p.site(axis.origin) is p.site(axis.through):
                raise ValueError("beam_axis needs two different sites")
        p._derive_face_edges()
        p._resolve_axis_positions()
        for b in p.baselines:
            p.site(b.source); p.site(b.target)
            if b.axis_to:
                p.site(b.axis_to)
        for oa in p.opening_angles:
            p.site(oa.vertex); p.site(oa.a); p.site(oa.b)
            if oa.axis_to:
                p.site(oa.axis_to)
        return p
