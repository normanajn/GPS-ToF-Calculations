"""Time-of-flight engine: endpoints, correction ledger, geometry, effects,
sensitivities and error budget for each baseline of a Problem."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from .angles import dms
from .constants import C, OMEGA_EARTH, ARCSEC
from .geodesy import (ELLIPSOIDS, Ellipsoid, geodetic_to_ecef, spherical_to_ecef, ecef_to_geodetic, enu_basis,
                      enu_to_ecef_offset, ecef_to_enu, azimuth_elevation, angle_between,
                      vsub, vadd, norm, unit, dot, cross, Vec3)
from .model import Problem, Site, Baseline, Settings, TimingShift, OpeningAngle, BeamAxis


# ------------------------------------------------------------------ endpoints
class Stage:
    """Which corrections are applied when placing a site's endpoint."""
    __slots__ = ("model", "datum", "vertical", "horizontal", "normal")

    def __init__(self, model: str, datum: bool, vertical: bool, horizontal: bool, normal: str):
        self.model, self.datum, self.vertical, self.horizontal, self.normal = model, datum, vertical, horizontal, normal


def _ellipsoid(settings: Settings, model: str) -> Optional[Ellipsoid]:
    return None if model == "sphere" else ELLIPSOIDS[model]


def site_point(site: Site, settings: Settings, stage: Stage) -> Vec3:
    h = site.h_ellipsoidal if stage.datum else site.height_m
    if stage.model == "sphere":
        p = spherical_to_ecef(site.lat_rad, site.lon_rad, h, settings.sphere_radius_m)
    else:
        p = geodetic_to_ecef(site.lat_rad, site.lon_rad, h, ELLIPSOIDS[stage.model])
    de, dn, du = site.offset_enu_m
    d = (de if stage.horizontal else 0.0, dn if stage.horizontal else 0.0, du if stage.vertical else 0.0)
    if d != (0.0, 0.0, 0.0):
        p = vadd(p, enu_to_ecef_offset(d, site.lat_rad, site.lon_rad, stage.normal, p))
    return p


def final_stage(settings: Settings, model: Optional[str] = None, normal: Optional[str] = None) -> Stage:
    return Stage(model or settings.earth_model, True, True, True, normal or settings.offset_normal)


def chord(a: Site, b: Site, settings: Settings, stage: Stage) -> float:
    return norm(vsub(site_point(b, settings, stage), site_point(a, settings, stage)))


# ---------------------------------------------------------------- utilities
def _ticks(t: float, s: Settings) -> float:
    return t * s.clock_hz


def _tick_s(s: Settings) -> float:
    return 1.0 / s.clock_hz


def _round(x: float, mode: str) -> int:
    if mode == "floor":
        return int(math.floor(x))
    if mode == "ceil":
        return int(math.ceil(x))
    return int(math.floor(x + 0.5))


# ---------------------------------------------------------------- beam axis
def axis_frame(problem: Problem, force: bool = False) -> Optional[Dict[str, Any]]:
    """Geometry of the global beam axis: origin ECEF, unit direction, and a
    transverse basis (h = horizontal-right looking downstream, v = up-ish).
    Returns None when no axis is defined or axis reporting is switched off
    (unless ``force``, used to resolve axis_position sites)."""
    ax = problem.beam_axis
    if ax is None or (not force and not problem.settings.report_axis):
        return None
    s = problem.settings
    st = final_stage(s)
    o, th = problem.site(ax.origin), problem.site(ax.through)
    po, pt = site_point(o, s, st), site_point(th, s, st)
    d = vsub(pt, po)
    u = unit(d)
    _, _, up = enu_basis(o.lat_rad, o.lon_rad)
    h = unit(cross(u, up))            # horizontal, to the right when looking along the axis
    v = cross(h, u)                   # completes the right-handed frame, points "up" transverse to the axis
    az, el = azimuth_elevation(u, o.lat_rad, o.lon_rad)
    return {"label": ax.label or "%s -> %s" % (o.name, th.name), "origin": o.name, "origin_id": o.id,
            "through": th.name, "through_id": th.id, "length_m": norm(d),
            "azimuth_at_origin_deg": math.degrees(az), "elevation_at_origin_deg": math.degrees(el),
            "p0": po, "u": u, "h": h, "v": v}


def point_vs_axis(p: Vec3, frame: Dict[str, Any]) -> Dict[str, Any]:
    """Off-axis angle at the axis origin, distance along the axis, transverse
    distance and its right/up components, for an ECEF point."""
    r = vsub(p, frame["p0"])
    along = dot(r, frame["u"])
    right = dot(r, frame["h"])
    up = dot(r, frame["v"])
    trans = math.hypot(right, up)
    ang = angle_between(r, frame["u"]) if norm(r) > 0.0 else 0.0
    return {"off_axis_mrad": ang * 1e3, "off_axis_deg": math.degrees(ang), "along_axis_m": along,
            "transverse_m": trans, "transverse_right_m": right, "transverse_up_m": up,
            "clock_angle_deg": math.degrees(math.atan2(right, up)) if trans > 1e-6 else None,
            "distance_from_origin_m": norm(r)}


def direction_vs_axis(v: Vec3, frame: Dict[str, Any]) -> Dict[str, Any]:
    """Angle between a chord direction and the axis direction, with its
    components in the axis transverse frame."""
    u = unit(v)
    ang = angle_between(u, frame["u"])
    return {"angle_mrad": ang * 1e3, "angle_deg": math.degrees(ang),
            "right_component_mrad": 1e3 * math.atan2(dot(u, frame["h"]), dot(u, frame["u"])),
            "up_component_mrad": 1e3 * math.atan2(dot(u, frame["v"]), dot(u, frame["u"]))}


def _site_summary(site: Site, settings: Settings, frame: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    st = final_stage(settings)
    p_ant = site_point(site, settings, Stage(settings.earth_model, True, False, False, settings.offset_normal))
    p_end = site_point(site, settings, st)
    ell = _ellipsoid(settings, settings.earth_model) or ELLIPSOIDS["wgs84"]
    la, lo, h = ecef_to_geodetic(p_end, ell)
    d: Dict[str, Any] = {
        "name": site.name, "id": site.id,
        "lat_deg": site.lat, "lon_deg": site.lon,
        "lat_dms": dms(site.lat, "lat"), "lon_dms": dms(site.lon, "lon"),
        "height_given_m": site.height_m, "datum": site.datum,
        "geoid_separation_m": site.geoid_separation_m,
        "h_ellipsoidal_m": site.h_ellipsoidal,
        "offset_enu_m": list(site.offset_enu_m), "offset_note": site.offset_note,
        "fscs_xyz_ft": list(site.fscs_xyz_ft) if site.fscs_xyz_ft else None,
        "axis_position": dict(site.axis_position) if site.axis_position else None,
        "ecef_surveyed_m": list(p_ant), "ecef_endpoint_m": list(p_end),
        "endpoint_lat_deg": math.degrees(la), "endpoint_lon_deg": math.degrees(lo), "endpoint_h_m": h,
        "cable_delay_ns": (site.cable_delay_s * 1e9) if site.cable_delay_s is not None else None,
        "uncertainty": dict(site.uncertainty), "source": site.source, "notes": site.notes,
    }
    if frame is not None:
        d["vs_axis"] = point_vs_axis(p_end, frame)
    return d


# ------------------------------------------------------------------- ledger
def build_ledger(a: Site, b: Site, s: Settings) -> List[Dict[str, Any]]:
    """Ordered list of correction steps from the reference model to the final
    chord.  Each step holds the running L and the change it introduced."""
    main = s.earth_model
    ref = "sphere" if main != "sphere" else "wgs84"
    nrm = s.offset_normal
    steps: List[Tuple[str, str, Stage]] = []
    desc_ref = ("spherical Earth, R = %.3f m" % s.sphere_radius_m) if ref == "sphere" else "WGS84 ellipsoid"
    desc_main = ("spherical Earth, R = %.3f m" % s.sphere_radius_m) if main == "sphere" else ("%s ellipsoid" % main.upper())
    steps.append(("reference model", "%s; heights as given; surveyed points, no offsets" % desc_ref,
                  Stage(ref, False, False, False, nrm)))
    steps.append(("Earth model", "%s; heights as given; surveyed points, no offsets" % desc_main,
                  Stage(main, False, False, False, nrm)))
    # datum per site: evaluate with A converted, then both
    datum_sites = [x for x in (a, b) if x.datum == "msl"]
    # We cannot apply per-site datum with a single Stage flag, so build explicit site variants.
    ledger: List[Dict[str, Any]] = []
    prevL = None
    L1 = None

    def add(step: str, desc: str, L: float, site_id: Optional[str] = None):
        nonlocal prevL, L1
        dL = 0.0 if prevL is None else L - prevL
        if L1 is None and step == "Earth model":
            L1 = L
        cum = 0.0 if L1 is None else L - L1
        ledger.append({
            "step": step, "description": desc, "site": site_id,
            "L_m": L, "dL_m": dL, "dt_ns": dL / C * 1e9, "dticks": _ticks(dL / C, s),
            "t_us": L / C * 1e6, "ticks": _ticks(L / C, s),
            "cum_dL_m": cum, "cum_dt_ns": cum / C * 1e9, "cum_dticks": _ticks(cum / C, s),
        })
        prevL = L

    for name, desc, st in steps:
        add(name, desc, chord(a, b, s, st))

    # progressive application using site clones that carry only the corrections applied so far
    chain = Stage(main, False, True, True, nrm)   # the clones decide which offsets exist
    cur_a = a.replace(offset_enu_m=(0.0, 0.0, 0.0))
    cur_b = b.replace(offset_enu_m=(0.0, 0.0, 0.0))

    def set_cur(x: Site, new: Site):
        nonlocal cur_a, cur_b
        if x is a:
            cur_a = new
        else:
            cur_b = new

    def cur(x: Site) -> Site:
        return cur_a if x is a else cur_b

    for x in datum_sites:
        set_cur(x, cur(x).replace(height_m=x.h_ellipsoidal, datum="ellipsoid", geoid_separation_m=None))
        add("height datum", "%s: MSL altitude %.3f m -> ellipsoidal %.3f m (geoid separation %+.3f m)"
            % (x.name, x.height_m, x.h_ellipsoidal, x.geoid_separation_m), chord(cur_a, cur_b, s, chain), x.id)
    for x in (a, b):
        if x.offset_enu_m[2] != 0.0:
            set_cur(x, cur(x).replace(offset_enu_m=(0.0, 0.0, x.offset_enu_m[2])))
            add("vertical offset", "%s: endpoint %+.3f m along the local %s vertical%s"
                % (x.name, x.offset_enu_m[2], nrm, (" (%s)" % x.offset_note) if x.offset_note else ""),
                chord(cur_a, cur_b, s, chain), x.id)
    for x in (a, b):
        if x.offset_enu_m[0] != 0.0 or x.offset_enu_m[1] != 0.0:
            set_cur(x, cur(x).replace(offset_enu_m=tuple(x.offset_enu_m)))
            add("horizontal offset", "%s: endpoint moved %+.3f m East, %+.3f m North"
                % (x.name, x.offset_enu_m[0], x.offset_enu_m[1]), chord(cur_a, cur_b, s, chain), x.id)
    # final consistency: the progressive chain must equal the direct final stage
    Lfin = chord(a, b, s, final_stage(s))
    if abs(Lfin - prevL) > 1e-6:
        raise AssertionError("ledger does not close: %.9f vs %.9f" % (Lfin, prevL))
    return ledger


# ----------------------------------------------------------------- geometry
def geometry(a: Site, b: Site, s: Settings, pa: Vec3, pb: Vec3, axis_point: Optional[Vec3] = None) -> Dict[str, Any]:
    v = vsub(pb, pa)
    L = norm(v)
    u = unit(v)
    gamma = angle_between(pa, pb)
    rm = 0.5 * (norm(pa) + norm(pb))
    az_a, el_a = azimuth_elevation(u, a.lat_rad, a.lon_rad)
    az_b, el_b = azimuth_elevation(vsub(pa, pb), b.lat_rad, b.lon_rad)  # back azimuth, from B looking to A
    e, n, up = ecef_to_enu(v, a.lat_rad, a.lon_rad)
    # deepest point of the chord below the ellipsoid (approx: sample)
    ell = _ellipsoid(s, s.earth_model) or ELLIPSOIDS["wgs84"]
    min_h = None
    for i in range(0, 201):
        f = i / 200.0
        p = vadd(pa, (v[0] * f, v[1] * f, v[2] * f))
        _, _, h = ecef_to_geodetic(p, ell)
        if min_h is None or h < min_h[0]:
            min_h = (h, f)
    g: Dict[str, Any] = {
        "chord_m": L,
        "central_angle_deg": math.degrees(gamma),
        "surface_arc_mean_radius_m": rm * gamma,
        "arc_minus_chord_m": rm * gamma - L,
        "arc_minus_chord_ticks": _ticks((rm * gamma - L) / C, s),
        "sagitta_m": rm * (1.0 - math.cos(gamma / 2.0)),
        "deepest_point_h_m": min_h[0], "deepest_point_fraction": min_h[1],
        "azimuth_at_source_deg": math.degrees(az_a),
        "elevation_at_source_deg": math.degrees(el_a),
        "back_azimuth_at_target_deg": math.degrees(az_b),
        "elevation_at_target_deg": -math.degrees(el_b),
        "target_enu_from_source_m": [e, n, up],
        "unit_vector_ecef": list(u),
    }
    if axis_point is not None:
        ax = vsub(axis_point, pa)
        g["off_axis_angle_mrad"] = 1e3 * angle_between(v, ax)
        g["axis_azimuth_deg"] = math.degrees(azimuth_elevation(ax, a.lat_rad, a.lon_rad)[0])
        g["axis_elevation_deg"] = math.degrees(azimuth_elevation(ax, a.lat_rad, a.lon_rad)[1])
    return g


# ------------------------------------------------------------ sensitivities
def sensitivities(a: Site, b: Site, s: Settings, L: float) -> List[Dict[str, Any]]:
    out = []
    st = final_stage(s)

    def row(label: str, Lv: float, kind: str, site: Optional[str] = None, per: str = ""):
        dL = Lv - L
        out.append({"label": label, "site": site, "kind": kind, "per": per,
                    "dL_m": dL, "dt_ns": dL / C * 1e9, "dticks": _ticks(dL / C, s)})

    arc = s.arcsec_step
    dh = s.height_step_m
    dm = s.offset_step_m
    for x, other, first in ((a, b, True), (b, a, False)):
        def L_of(xx: Site) -> float:
            return chord(xx, other, s, st) if first else chord(other, xx, s, st)
        row("%s: height %+g m" % (x.name, dh), L_of(x.replace(height_m=x.height_m + dh)), "height", x.id, "per %g m" % dh)
        row("%s: latitude %+g\"" % (x.name, arc), L_of(x.replace(lat=x.lat + arc / 3600.0)), "lat", x.id, "per %g\"" % arc)
        row("%s: longitude %+g\"" % (x.name, arc), L_of(x.replace(lon=x.lon + arc / 3600.0)), "lon", x.id, "per %g\"" % arc)
        o = x.offset_enu_m
        row("%s: endpoint %+g m East" % (x.name, dm), L_of(x.replace(offset_enu_m=(o[0] + dm, o[1], o[2]))), "east", x.id, "per %g m" % dm)
        row("%s: endpoint %+g m North" % (x.name, dm), L_of(x.replace(offset_enu_m=(o[0], o[1] + dm, o[2]))), "north", x.id, "per %g m" % dm)
    if any(v != 0.0 for v in a.offset_enu_m + b.offset_enu_m):
        alt = "radial" if s.offset_normal == "geodetic" else "geodetic"
        row("offsets along the %s normal instead of %s" % (alt, s.offset_normal),
            chord(a, b, s, final_stage(s, normal=alt)), "method")
    if s.earth_model != "sphere":
        row("spherical Earth (R = %.0f m) at the final endpoints" % s.sphere_radius_m,
            chord(a, b, s, final_stage(s, model="sphere")), "model")
        other_ell = "grs80" if s.earth_model == "wgs84" else "wgs84"
        row("%s ellipsoid instead of %s" % (other_ell.upper(), s.earth_model.upper()),
            chord(a, b, s, final_stage(s, model=other_ell)), "model")
    return out


def error_budget(a: Site, b: Site, s: Settings, sens: List[Dict[str, Any]],
                 shifts: List[TimingShift], effects: Dict[str, Any]) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    by = {(r["site"], r["kind"]): r for r in sens}

    def add(source: str, sigma_s: float, kind: str, combine: bool, note: str = ""):
        items.append({"source": source, "sigma_ns": sigma_s * 1e9, "sigma_ticks": _ticks(sigma_s, s),
                      "type": kind, "combined": combine, "note": note})

    for x in (a, b):
        u = x.uncertainty or {}
        for key, kind, scale, unit_ in (("lat_arcsec", "lat", 1.0 / s.arcsec_step, "\""),
                                        ("lon_arcsec", "lon", 1.0 / s.arcsec_step, "\""),
                                        ("height_m", "height", 1.0 / s.height_step_m, " m")):
            if key in u and (x.id, kind) in by:
                dL = abs(by[(x.id, kind)]["dL_m"]) * scale * float(u[key])
                add("%s: %s ±%g%s (1σ)" % (x.name, kind, u[key], unit_), dL / C, "systematic", True)
        if "offset_m" in u:
            # gradient of L w.r.t. endpoint position is the unit chord vector, so the worst
            # case is 1 m of L per metre of offset error (along the chord)
            add("%s: endpoint offset ±%g m, worst case along the chord" % (x.name, u["offset_m"]),
                float(u["offset_m"]) / C, "systematic", True)
        if "quantization_arcsec" in u and (x.id, "lat") in by:
            q = float(u["quantization_arcsec"])
            slat = abs(by[(x.id, "lat")]["dL_m"]) / s.arcsec_step
            slon = abs(by[(x.id, "lon")]["dL_m"]) / s.arcsec_step
            rms = math.hypot(slat, slon) * q / math.sqrt(12.0)
            worst = 0.5 * q * (slat + slon)
            add("%s: coordinate quantization %g\" (RMS of uniform rounding)" % (x.name, q), rms / C, "precision", True)
            add("%s: coordinate quantization %g\" (worst case)" % (x.name, q), worst / C, "precision", False)
    for t in shifts:
        if t.rf_uncertainty_hz and t.rf_sensitivity_s_per_hz is not None:
            add("%s: RF frequency ±%g Hz" % (t.name, t.rf_uncertainty_hz),
                abs(t.rf_sensitivity_s_per_hz) * t.rf_uncertainty_hz, "systematic", True)
    add("integer rounding of the final tick count", 0.5 * _tick_s(s), "convention", False)
    if effects.get("sagnac_ns") is not None and not s.apply_sagnac:
        add("Sagnac term (not applied)", abs(effects["sagnac_ns"]) * 1e-9, "neglected", False)
    rss = math.sqrt(sum(i["sigma_ticks"] ** 2 for i in items if i["combined"]))
    lin = sum(abs(i["sigma_ticks"]) for i in items if i["combined"])
    return {"items": items, "rss_ticks": rss, "rss_ns": rss * _tick_s(s) * 1e9,
            "linear_sum_ticks": lin, "linear_sum_ns": lin * _tick_s(s) * 1e9}


# ------------------------------------------------------------------ effects
def effects(a: Site, b: Site, s: Settings, pa: Vec3, pb: Vec3, t: float) -> Dict[str, Any]:
    # Sagnac: Δt = ω (x_a y_b − y_a x_b) / c²  (ECEF, physical longitudes)
    sag = OMEGA_EARTH * (pa[0] * pb[1] - pa[1] * pb[0]) / (C * C)
    out: Dict[str, Any] = {"sagnac_s": sag, "sagnac_ns": sag * 1e9, "sagnac_ticks": _ticks(sag, s),
                           "sagnac_applied": s.apply_sagnac}
    if s.neutrino_mass_ev is not None and s.neutrino_energy_gev:
        r = s.neutrino_mass_ev / (s.neutrino_energy_gev * 1e9)
        dt = t * 0.5 * r * r
        out.update({"neutrino_mass_ev": s.neutrino_mass_ev, "neutrino_energy_gev": s.neutrino_energy_gev,
                    "neutrino_delay_s": dt, "neutrino_delay_ns": dt * 1e9})
    cables = []
    for x in (a, b):
        d = x.cable_delay_s
        if d is not None:
            cables.append({"site": x.name, "delay_ns": d * 1e9, "delay_ticks": _ticks(d, s),
                           "length_m": x.cable_length_m, "velocity_factor": x.cable_velocity_factor})
    out["cables"] = cables
    return out


# ------------------------------------------------------------------- driver
def compute_baseline(problem: Problem, bl: Baseline) -> Dict[str, Any]:
    s = problem.settings
    a, b = problem.site(bl.source), problem.site(bl.target)
    st = final_stage(s)
    pa, pb = site_point(a, s, st), site_point(b, s, st)
    L = norm(vsub(pb, pa))
    t = L / C
    ticks = _ticks(t, s)
    n_int = _round(ticks, s.rounding)
    ledger = build_ledger(a, b, s)
    frame = axis_frame(problem)
    axis_pt = site_point(problem.site(bl.axis_to), s, st) if getattr(bl, "axis_to", "") else None
    geo = geometry(a, b, s, pa, pb, axis_pt)
    axis_info = None
    if frame is not None:
        axis_info = {"label": frame["label"], "chord_vs_axis": direction_vs_axis(vsub(pb, pa), frame),
                     "source": point_vs_axis(pa, frame), "target": point_vs_axis(pb, frame)}
    eff = effects(a, b, s, pa, pb, t)
    shifts = []
    for ts in problem.timing_shifts:
        v = ts.value_s
        row = {"name": ts.name, "seconds": v, "us": v * 1e6, "ticks": _ticks(v, s), "notes": ts.notes}
        if ts.t_rev_s is not None:
            row.update({"turns": ts.turns, "buckets_per_turn": ts.buckets_per_turn, "rf_hz": ts.rf_hz,
                        "t_rev_us": ts.t_rev_s * 1e6, "ticks_per_turn": _ticks(ts.t_rev_s, s),
                        "ticks_per_khz_rf": abs(ts.rf_sensitivity_s_per_hz) * 1e3 * s.clock_hz})
        shifts.append(row)
    t_shift = sum(r["seconds"] for r in shifts)
    t_tot = t + t_shift + (eff["sagnac_s"] if s.apply_sagnac else 0.0)
    ticks_tot = _ticks(t_tot, s)
    n_tot = _round(ticks_tot, s.rounding)
    result = {
        "L_m": L, "t_s": t, "t_us": t * 1e6, "ticks": ticks,
        "ticks_int": n_int, "rounding": s.rounding, "rounding_residual_ns": (n_int - ticks) * _tick_s(s) * 1e9,
        "legacy_units": t / s.legacy_unit_s,
        "clock_hz": s.clock_hz, "tick_ns": _tick_s(s) * 1e9, "metres_per_tick": C * _tick_s(s),
    }
    total = {
        "t_s": t_tot, "t_us": t_tot * 1e6, "ticks": ticks_tot, "ticks_int": n_tot,
        "rounding_residual_ns": (n_tot - ticks_tot) * _tick_s(s) * 1e9,
        "shift_us": t_shift * 1e6, "shift_ticks": _ticks(t_shift, s), "includes_sagnac": s.apply_sagnac,
    }
    window = None
    if s.window_before_us is not None and s.window_after_us is not None:
        lo = t - s.window_before_us * 1e-6
        hi = t + s.window_after_us * 1e-6
        window = {"before_us": s.window_before_us, "after_us": s.window_after_us,
                  "width_us": s.window_before_us + s.window_after_us,
                  "tof_lo_ticks": _ticks(lo, s), "tof_hi_ticks": _ticks(hi, s),
                  "total_lo_ticks": _ticks(lo + t_shift, s), "total_hi_ticks": _ticks(hi + t_shift, s)}
        if s.microslice_us:
            w, m = s.window_before_us + s.window_after_us, s.microslice_us
            window.update({"microslice_us": m, "microslice_ticks": _ticks(m * 1e-6, s),
                           "microslices_min": int(math.ceil(w / m)),
                           "microslices_max": int(math.floor(w / m)) + 1,
                           "record_max_us": (int(math.floor(w / m)) + 1) * m})
    sens = sensitivities(a, b, s, L) if s.sensitivities else []
    budget = error_budget(a, b, s, sens, problem.timing_shifts, eff) if s.sensitivities else None
    return {
        "label": bl.label or "%s -> %s" % (a.name, b.name),
        "source": _site_summary(a, s, frame), "target": _site_summary(b, s, frame),
        "axis_to": getattr(bl, "axis_to", "") or None,
        "beam_axis": axis_info,
        "ledger": ledger, "result": result, "geometry": geo, "effects": eff,
        "timing_shifts": shifts, "total": total, "window": window,
        "sensitivities": sens, "error_budget": budget,
    }


def compute_opening_angle(problem: Problem, oa: OpeningAngle) -> Dict[str, Any]:
    """Angle at the vertex between the chords vertex->a and vertex->b, with its
    horizontal/vertical decomposition at the vertex, the transverse distance of
    each endpoint from the other chord, and the difference in flight time."""
    s = problem.settings
    v, a, b = problem.site(oa.vertex), problem.site(oa.a), problem.site(oa.b)
    st = final_stage(s)
    pv, pa, pb = site_point(v, s, st), site_point(a, s, st), site_point(b, s, st)
    va, vb = vsub(pa, pv), vsub(pb, pv)
    La, Lb = norm(va), norm(vb)
    ang = angle_between(va, vb)
    az_a, el_a = azimuth_elevation(va, v.lat_rad, v.lon_rad)
    az_b, el_b = azimuth_elevation(vb, v.lat_rad, v.lon_rad)
    daz = (math.degrees(az_b - az_a) + 180.0) % 360.0 - 180.0
    out: Dict[str, Any] = {
        "label": oa.label or "%s: %s vs %s" % (v.name, a.name, b.name),
        "vertex": v.name, "vertex_id": v.id, "a": a.name, "a_id": a.id, "b": b.name, "b_id": b.id,
        "angle_rad": ang, "angle_deg": math.degrees(ang), "angle_mrad": ang * 1e3,
        "angle_dms": "%d° %02d' %06.3f\"" % (int(math.degrees(ang)), int(math.degrees(ang) * 60) % 60, (math.degrees(ang) * 3600) % 60),
        "L_a_m": La, "L_b_m": Lb,
        "azimuth_a_deg": math.degrees(az_a), "elevation_a_deg": math.degrees(el_a),
        "azimuth_b_deg": math.degrees(az_b), "elevation_b_deg": math.degrees(el_b),
        "delta_azimuth_deg": daz, "delta_elevation_deg": math.degrees(el_b - el_a),
        "horizontal_component_mrad": daz * math.pi / 180.0 * 1e3 * math.cos(0.5 * (el_a + el_b)),
        "vertical_component_mrad": (el_b - el_a) * 1e3,
        "a_transverse_from_vb_m": La * math.sin(ang),    # distance of a's endpoint from the line vertex->b
        "b_transverse_from_va_m": Lb * math.sin(ang),
        "a_along_vb_m": La * math.cos(ang),              # projection of vertex->a onto vertex->b
        "dL_m": Lb - La, "dt_us": (Lb - La) / C * 1e6, "dticks": _ticks((Lb - La) / C, s),
        # the a endpoint seen as a point on the way to b: its flight-time advance over the straight projection
        "path_via_a_minus_direct_m": (La + norm(vsub(pb, pa))) - Lb,
        "unit_a_ecef": list(unit(va)), "unit_b_ecef": list(unit(vb)),
        "axis_to": oa.axis_to or None,
    }
    frame = axis_frame(problem)
    if frame is not None:
        out["beam_axis"] = {"label": frame["label"],
                            "a_chord_vs_axis": direction_vs_axis(va, frame), "b_chord_vs_axis": direction_vs_axis(vb, frame),
                            "a": point_vs_axis(pa, frame), "b": point_vs_axis(pb, frame), "vertex": point_vs_axis(pv, frame)}
    if oa.axis_to:
        pax = site_point(problem.site(oa.axis_to), s, st)
        ax = vsub(pax, pv)
        out["off_axis_a_mrad"] = 1e3 * angle_between(va, ax)
        out["off_axis_b_mrad"] = 1e3 * angle_between(vb, ax)
        # signed angle about the axis: positive if a and b lie on the same side of the axis
        na, nb = cross(ax, va), cross(ax, vb)
        out["same_side_of_axis"] = bool(dot(na, nb) > 0.0)
        out["azimuth_about_axis_deg"] = math.degrees(angle_between(na, nb)) if norm(na) and norm(nb) else None
    return out


def compute_all(problem: Problem) -> Dict[str, Any]:
    from . import __version__
    import datetime
    s = problem.settings
    frame = axis_frame(problem)
    axis_summary = None
    if frame is not None:
        axis_summary = {k: frame[k] for k in ("label", "origin", "origin_id", "through", "through_id", "length_m",
                                              "azimuth_at_origin_deg", "elevation_at_origin_deg")}
        axis_summary["unit_ecef"] = list(frame["u"])
        axis_summary["origin_ecef"] = list(frame["p0"])
    return {
        "project": s.project, "generated": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "gps_tof_version": __version__,
        "settings": {k: getattr(s, k) for k in s.__dataclass_fields__},  # type: ignore[attr-defined]
        "beam_axis": axis_summary,
        "sites": [_site_summary(x, s, frame) for x in problem.sites],
        "baselines": [compute_baseline(problem, b) for b in problem.baselines],
        "opening_angles": [compute_opening_angle(problem, oa) for oa in problem.opening_angles],
    }
