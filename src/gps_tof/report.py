"""Render a computed result (from calc.compute_all) as text, Markdown or JSON."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence


# ------------------------------------------------------------------ tables
class Table:
    def __init__(self, header: Sequence[str], align: Optional[Sequence[str]] = None):
        self.header = list(header)
        self.align = list(align) if align else ["l"] + ["r"] * (len(header) - 1)
        self.rows: List[List[str]] = []

    def add(self, *cells: Any):
        self.rows.append([("" if c is None else str(c)) for c in cells])

    def markdown(self) -> str:
        out = ["| " + " | ".join(self.header) + " |",
               "|" + "|".join((":---" if a == "l" else "---:") for a in self.align) + "|"]
        for r in self.rows:
            out.append("| " + " | ".join(c.replace("|", "\\|") for c in r) + " |")
        return "\n".join(out)

    def text(self) -> str:
        cols = len(self.header)
        w = [len(self.header[i]) for i in range(cols)]
        for r in self.rows:
            for i, c in enumerate(r):
                w[i] = max(w[i], len(c))

        def fmt(r):
            return "  ".join((c.ljust(w[i]) if self.align[i] == "l" else c.rjust(w[i])) for i, c in enumerate(r))
        lines = [fmt(self.header), "  ".join("-" * x for x in w)]
        lines += [fmt(r) for r in self.rows]
        return "\n".join(lines)


class Doc:
    """Minimal document builder that renders to Markdown or plain text."""
    def __init__(self, fmt: str, digits: int):
        self.fmt = fmt
        self.d = digits
        self.parts: List[str] = []

    def h(self, level: int, text: str):
        if self.fmt == "md":
            self.parts.append("\n" + "#" * level + " " + text + "\n")
        else:
            bar = "=" if level <= 1 else ("-" if level == 2 else ".")
            self.parts.append("\n" + text + "\n" + bar * len(text) + "\n")

    def p(self, text: str):
        self.parts.append(text + "\n")

    def kv(self, pairs: Sequence[Sequence[Any]]):
        t = Table(["quantity", "value"], ["l", "l"])
        for k, v in pairs:
            t.add(k, v)
        self.table(t)

    def table(self, t: Table):
        self.parts.append((t.markdown() if self.fmt == "md" else t.text()) + "\n")

    def bullet(self, items: Sequence[str]):
        for it in items:
            self.parts.append(("- " if self.fmt == "md" else "  * ") + it)
        self.parts.append("")

    def render(self) -> str:
        return "\n".join(self.parts).strip() + "\n"

    # number formatting
    def n(self, x: Any, digits: Optional[int] = None) -> str:
        if x is None:
            return "-"
        if isinstance(x, bool):
            return "yes" if x else "no"
        if isinstance(x, int):
            return "{:,}".format(x)
        if isinstance(x, float):
            d = self.d if digits is None else digits
            return "{:,.{d}f}".format(x, d=d)
        return str(x)

    def sn(self, x: Any, digits: Optional[int] = None) -> str:
        """signed number"""
        if x is None:
            return "-"
        d = self.d if digits is None else digits
        return "{:+,.{d}f}".format(x, d=d)


# ------------------------------------------------------------------ render
def _site_block(doc: Doc, s: Dict[str, Any], role: str):
    doc.h(3, "%s: %s" % (role, s["name"]))
    rows = [
        ("latitude", "%s  (%.9f°)" % (s["lat_dms"], s["lat_deg"])),
        ("longitude", "%s  (%.9f°, east positive)" % (s["lon_dms"], s["lon_deg"])),
        ("height as given", "%s m (%s)" % (doc.n(s["height_given_m"], 3), s["datum"])),
    ]
    if s["geoid_separation_m"] is not None:
        rows.append(("geoid separation N", "%s m" % doc.n(s["geoid_separation_m"], 3)))
    rows.append(("ellipsoidal height h", "%s m" % doc.n(s["h_ellipsoidal_m"], 3)))
    if s["fscs_xyz_ft"]:
        rows.append(("Fermilab site coordinates (ft)", "x %.3f, y %.3f, z %.3f" % tuple(s["fscs_xyz_ft"])))
    if s.get("axis_position"):
        ap = s["axis_position"]
        rows.append(("given in the beamline frame %s (along, right, up)" % ap.get("frame", "axis"),
                     "along %.3f m, right %+.3f m, up %+.3f m; lat/lon/h above are derived" % (ap["along_m"], ap["right_m"], ap["up_m"])))
    o = s["offset_enu_m"]
    rows.append(("surveyed point -> endpoint (E, N, U)", "%+.3f, %+.3f, %+.3f m%s" % (o[0], o[1], o[2],
                 ("  (" + s["offset_note"] + ")") if s["offset_note"] else "")))
    rows.append(("ECEF of surveyed point", "(%.3f, %.3f, %.3f) m" % tuple(s["ecef_surveyed_m"])))
    rows.append(("ECEF of endpoint", "(%.3f, %.3f, %.3f) m" % tuple(s["ecef_endpoint_m"])))
    rows.append(("endpoint geodetic", "%.9f°, %.9f°, h = %.3f m" % (s["endpoint_lat_deg"], s["endpoint_lon_deg"], s["endpoint_h_m"])))
    if s["cable_delay_ns"] is not None:
        rows.append(("antenna cable delay", "%s ns (calibration, not part of ToF)" % doc.n(s["cable_delay_ns"], 2)))
    if s["uncertainty"]:
        rows.append(("uncertainties", ", ".join("%s = %g" % kv for kv in sorted(s["uncertainty"].items()))))
    if s["source"]:
        rows.append(("source", s["source"]))
    if s["notes"]:
        rows.append(("notes", s["notes"]))
    doc.kv(rows)


def render_baseline(doc: Doc, b: Dict[str, Any], st: Dict[str, Any]):
    r = b["result"]
    doc.h(2, "Baseline: %s" % b["label"])
    _site_block(doc, b["source"], "Source")
    _site_block(doc, b["target"], "Target")

    doc.h(3, "Result")
    doc.kv([
        ("Earth model", st["earth_model"] + (" (R = %s m)" % doc.n(st["sphere_radius_m"], 3) if st["earth_model"] == "sphere" else "")),
        ("offset normal", st["offset_normal"]),
        ("chord length L", "%s m" % doc.n(r["L_m"])),
        ("time of flight t = L/c", "%s µs" % doc.n(r["t_us"], 6)),
        ("clock", "%s MHz (%.4f ns/tick, %.4f m/tick)" % (doc.n(r["clock_hz"] / 1e6, 4), r["tick_ns"], r["metres_per_tick"])),
        ("ticks (exact)", doc.n(r["ticks"], 4)),
        ("ticks (%s)" % r["rounding"], "%s  (residual %s ns)" % (doc.n(r["ticks_int"]), doc.sn(r["rounding_residual_ns"], 2))),
        ("legacy units (%g ns)" % (st["legacy_unit_s"] * 1e9), doc.n(r["legacy_units"], 4)),
    ])

    doc.h(3, "Correction ledger")
    doc.p("Each row is one change to the endpoints, applied in order. ΔL is the change from the "
          "previous row; the cumulative column is measured from the chosen Earth model with no corrections.")
    t = Table(["step", "applied", "L (m)", "ΔL (m)", "Δt (ns)", "Δticks", "cum. Δticks"], ["l", "l", "r", "r", "r", "r", "r"])
    for row in b["ledger"]:
        t.add(row["step"], row["description"], doc.n(row["L_m"], 3), doc.sn(row["dL_m"], 3),
              doc.sn(row["dt_ns"], 2), doc.sn(row["dticks"], 3), doc.sn(row["cum_dticks"], 3))
    doc.table(t)

    if b["timing_shifts"]:
        doc.h(3, "Timing shifts and combined offset")
        t = Table(["shift", "value (µs)", "ticks", "detail"], ["l", "r", "r", "l"])
        for sh in b["timing_shifts"]:
            detail = ""
            if "t_rev_us" in sh:
                detail = "%g turns × %g buckets / %s MHz: T_rev = %s µs = %s ticks/turn; %s ticks per kHz of RF error" % (
                    sh["turns"], sh["buckets_per_turn"], doc.n(sh["rf_hz"] / 1e6, 4), doc.n(sh["t_rev_us"], 6),
                    doc.n(sh["ticks_per_turn"], 3), doc.n(sh["ticks_per_khz_rf"], 3))
            if sh.get("notes"):
                detail = (detail + "; " if detail else "") + sh["notes"]
            t.add(sh["name"], doc.n(sh["us"], 6), doc.n(sh["ticks"], 3), detail)
        doc.table(t)
    tot = b["total"]
    doc.kv([
        ("time of flight", "%s µs = %s ticks" % (doc.n(r["t_us"], 6), doc.n(r["ticks"], 3))),
        ("sum of timing shifts", "%s µs = %s ticks" % (doc.n(tot["shift_us"], 6), doc.n(tot["shift_ticks"], 3))),
        ("Sagnac included", doc.n(tot["includes_sagnac"])),
        ("total offset", "%s µs = %s ticks" % (doc.n(tot["t_us"], 6), doc.n(tot["ticks"], 3))),
        ("total, integer (%s)" % r["rounding"], "%s ticks (residual %s ns)" % (doc.n(tot["ticks_int"]), doc.sn(tot["rounding_residual_ns"], 2))),
    ])

    if b["window"]:
        w = b["window"]
        doc.h(3, "Trigger window")
        rows = [("window", "[t − %g µs, t + %g µs), width %g µs" % (w["before_us"], w["after_us"], w["width_us"])),
                ("relative to flight time only", "[%s, %s) ticks" % (doc.n(w["tof_lo_ticks"], 2), doc.n(w["tof_hi_ticks"], 2))),
                ("relative to flight time + shifts", "[%s, %s) ticks" % (doc.n(w["total_lo_ticks"], 2), doc.n(w["total_hi_ticks"], 2)))]
        if "microslice_us" in w:
            rows += [("microslice", "%g µs = %s ticks" % (w["microslice_us"], doc.n(w["microslice_ticks"], 1))),
                     ("microslices overlapped", "%d to %d (record up to %g µs)" % (w["microslices_min"], w["microslices_max"], w["record_max_us"]))]
        doc.kv(rows)

    g = b["geometry"]
    doc.h(3, "Chord geometry")
    rows = [("geocentric central angle", "%s°" % doc.n(g["central_angle_deg"], 5)),
            ("surface arc at mean radius", "%s m" % doc.n(g["surface_arc_mean_radius_m"], 1)),
            ("arc − chord", "%s m (%s ticks)" % (doc.n(g["arc_minus_chord_m"], 2), doc.n(g["arc_minus_chord_ticks"], 2))),
            ("sagitta", "%s m" % doc.n(g["sagitta_m"], 1)),
            ("deepest point of chord", "h = %s m at %.0f %% of the path" % (doc.n(g["deepest_point_h_m"], 1), 100 * g["deepest_point_fraction"])),
            ("azimuth at source (from North)", "%s°" % doc.n(g["azimuth_at_source_deg"], 5)),
            ("elevation at source", "%s° (negative = dips below horizontal)" % doc.n(g["elevation_at_source_deg"], 5)),
            ("back azimuth at target", "%s°" % doc.n(g["back_azimuth_at_target_deg"], 5)),
            ("elevation at target", "%s° (positive = arrives rising)" % doc.n(g["elevation_at_target_deg"], 5)),
            ("target in source ENU frame", "E %s, N %s, U %s m" % tuple(doc.n(v, 1) for v in g["target_enu_from_source_m"]))]
    if b.get("beam_axis"):
        bx = b["beam_axis"]
        cv = bx["chord_vs_axis"]
        rows += [("opening angle chord vs beam axis (%s)" % bx["label"], "%s mrad = %s° (right %s, up %s mrad)" % (
                     doc.n(cv["angle_mrad"], 4), doc.n(cv["angle_deg"], 6), doc.sn(cv["right_component_mrad"], 4), doc.sn(cv["up_component_mrad"], 4))),
                 ("source off-axis at the axis origin", "%s mrad; %s m along, %s m transverse (right %s, up %s)" % (
                     doc.n(bx["source"]["off_axis_mrad"], 4), doc.n(bx["source"]["along_axis_m"], 3), doc.n(bx["source"]["transverse_m"], 3),
                     doc.sn(bx["source"]["transverse_right_m"], 3), doc.sn(bx["source"]["transverse_up_m"], 3))),
                 ("target off-axis at the axis origin", "%s mrad; %s m along, %s m transverse (right %s, up %s)" % (
                     doc.n(bx["target"]["off_axis_mrad"], 4), doc.n(bx["target"]["along_axis_m"], 3), doc.n(bx["target"]["transverse_m"], 3),
                     doc.sn(bx["target"]["transverse_right_m"], 3), doc.sn(bx["target"]["transverse_up_m"], 3)))]
    if "off_axis_angle_mrad" in g:
        rows += [("reference axis (source → %s)" % b["axis_to"], "azimuth %s°, elevation %s°" % (doc.n(g["axis_azimuth_deg"], 5), doc.n(g["axis_elevation_deg"], 5))),
                 ("off-axis angle of this baseline", "%s mrad" % doc.n(g["off_axis_angle_mrad"], 3))]
    doc.kv(rows)

    e = b["effects"]
    doc.h(3, "Effects outside the geometric flight time")
    t = Table(["effect", "ns", "ticks", "status"], ["l", "r", "r", "l"])
    t.add("Sagnac (Earth rotation, ECEF frame)", doc.sn(e["sagnac_ns"], 3), doc.sn(e["sagnac_ticks"], 4),
          "applied to total" if e["sagnac_applied"] else "not applied")
    if "neutrino_delay_ns" in e:
        t.add("neutrino mass delay (m = %g eV, E = %g GeV)" % (e["neutrino_mass_ev"], e["neutrino_energy_gev"]),
              "%.3e" % e["neutrino_delay_ns"], "%.3e" % (e["neutrino_delay_ns"] * 1e-9 * st["clock_hz"]), "negligible")
    for c in e["cables"]:
        t.add("antenna cable delay, %s" % c["site"], doc.n(c["delay_ns"], 2), doc.n(c["delay_ticks"], 3), "receiver calibration, not ToF")
    doc.table(t)

    if b["sensitivities"]:
        doc.h(3, "Sensitivities")
        doc.p("Change of the chord for a unit change of each input, evaluated at the final endpoints.")
        t = Table(["variation", "ΔL (m)", "Δt (ns)", "Δticks"])
        for s_ in b["sensitivities"]:
            t.add(s_["label"], doc.sn(s_["dL_m"], 4), doc.sn(s_["dt_ns"], 3), doc.sn(s_["dticks"], 4))
        doc.table(t)

    if b["error_budget"]:
        eb = b["error_budget"]
        doc.h(3, "Error budget")
        t = Table(["source", "ns", "ticks", "type", "in RSS"], ["l", "r", "r", "l", "l"])
        for i in eb["items"]:
            t.add(i["source"], doc.n(i["sigma_ns"], 2), doc.n(i["sigma_ticks"], 3), i["type"], "yes" if i["combined"] else "no")
        doc.table(t)
        doc.kv([("root-sum-square of combined items", "%s ticks = %s ns" % (doc.n(eb["rss_ticks"], 3), doc.n(eb["rss_ns"], 1))),
                ("linear sum of combined items", "%s ticks = %s ns" % (doc.n(eb["linear_sum_ticks"], 3), doc.n(eb["linear_sum_ns"], 1)))])


def render(result: Dict[str, Any], fmt: str = "md") -> str:
    if fmt == "json":
        return json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if fmt not in ("md", "text"):
        raise ValueError("format must be md, text or json")
    st = result["settings"]
    doc = Doc(fmt, int(st.get("precision_digits", 4)))
    doc.h(1, "%s: time-of-flight report" % result["project"])
    doc.p("Generated %s by gps-tof %s." % (result["generated"], result["gps_tof_version"]))
    doc.h(2, "Settings")
    doc.kv([("Earth model", st["earth_model"]), ("offset normal", st["offset_normal"]),
            ("clock", "%s Hz" % doc.n(st["clock_hz"], 0)), ("legacy unit", "%g ns" % (st["legacy_unit_s"] * 1e9)),
            ("rounding", st["rounding"]), ("Sagnac applied", doc.n(st["apply_sagnac"])),
            ("sensitivity steps", "%g\", %g m height, %g m offset" % (st["arcsec_step"], st["height_step_m"], st["offset_step_m"]))])
    doc.h(2, "Sites")
    t = Table(["id", "name", "latitude", "longitude", "h given (m)", "datum", "h ell. (m)", "offset E,N,U (m)"],
              ["l", "l", "l", "l", "r", "l", "r", "l"])
    for s in result["sites"]:
        t.add(s["id"], s["name"], s["lat_dms"], s["lon_dms"], doc.n(s["height_given_m"], 3), s["datum"],
              doc.n(s["h_ellipsoidal_m"], 3), "%+g, %+g, %+g" % tuple(s["offset_enu_m"]))
    doc.table(t)
    if result.get("beam_axis"):
        ax = result["beam_axis"]
        doc.h(2, "Beam axis: %s" % ax["label"])
        doc.kv([("origin", ax["origin"]), ("passes through", ax["through"]),
                ("length origin → through", "%s m" % doc.n(ax["length_m"], 3)),
                ("azimuth at origin", "%s°" % doc.n(ax["azimuth_at_origin_deg"], 5)),
                ("elevation at origin", "%s° (negative = dips below the local horizontal)" % doc.n(ax["elevation_at_origin_deg"], 5)),
                ("unit vector (ECEF)", "(%.9f, %.9f, %.9f)" % tuple(ax["unit_ecef"]))])
        doc.p("Every site endpoint relative to the axis: the off-axis angle is measured at the origin between the axis "
              "and the line origin → endpoint; 'right' is to the right looking downstream along the axis, 'up' is the "
              "transverse direction closest to the local vertical at the origin; the clock angle is 0° above the axis, "
              "90° to the right.")
        t = Table(["id", "site", "off-axis (mrad)", "off-axis (deg)", "along axis (m)", "transverse (m)", "right (m)", "up (m)", "clock (deg)"],
                  ["l", "l", "r", "r", "r", "r", "r", "r", "r"])
        for s in result["sites"]:
            va = s.get("vs_axis")
            if va:
                t.add(s["id"], s["name"], doc.n(va["off_axis_mrad"], 4), doc.n(va["off_axis_deg"], 5), doc.n(va["along_axis_m"], 3),
                      doc.n(va["transverse_m"], 3), doc.sn(va["transverse_right_m"], 3), doc.sn(va["transverse_up_m"], 3),
                      doc.n(va["clock_angle_deg"], 2) if va["clock_angle_deg"] is not None else "-")
        doc.table(t)
    if len(result["baselines"]) > 1:
        doc.h(2, "Summary of baselines")
        has_axis = any(b.get("beam_axis") for b in result["baselines"])
        hdr = ["baseline", "L (m)", "ToF (µs)", "ticks", "total ticks", "total int"] + (["chord vs axis (mrad)"] if has_axis else [])
        t = Table(hdr)
        for b in result["baselines"]:
            row = [b["label"], doc.n(b["result"]["L_m"], 3), doc.n(b["result"]["t_us"], 6), doc.n(b["result"]["ticks"], 3),
                   doc.n(b["total"]["ticks"], 3), doc.n(b["total"]["ticks_int"])]
            if has_axis:
                row.append(doc.n(b["beam_axis"]["chord_vs_axis"]["angle_mrad"], 4) if b.get("beam_axis") else "-")
            t.add(*row)
        doc.table(t)
    if result.get("opening_angles"):
        doc.h(2, "Opening angles")
        doc.p("Angle at the vertex site between two chords, from the fully corrected endpoints. The transverse "
              "distance is how far one endpoint lies from the straight line through the vertex and the other endpoint.")
        has_axis = any(oa.get("beam_axis") for oa in result["opening_angles"])
        hdr = ["angle", "vertex", "chord a", "chord b", "angle (mrad)", "angle (deg)", "horiz. (mrad)", "vert. (mrad)"]
        if has_axis:
            hdr += ["a vs axis (mrad)", "b vs axis (mrad)"]
        t = Table(hdr, ["l", "l", "l", "l"] + ["r"] * (len(hdr) - 4))
        for oa in result["opening_angles"]:
            row = [oa["label"], oa["vertex"], oa["a"], oa["b"], doc.n(oa["angle_mrad"], 4), doc.n(oa["angle_deg"], 6),
                   doc.n(oa["horizontal_component_mrad"], 4), doc.n(oa["vertical_component_mrad"], 4)]
            if has_axis:
                bx = oa.get("beam_axis")
                row += [doc.n(bx["a_chord_vs_axis"]["angle_mrad"], 4) if bx else "-", doc.n(bx["b_chord_vs_axis"]["angle_mrad"], 4) if bx else "-"]
            t.add(*row)
        doc.table(t)
        for oa in result["opening_angles"]:
            doc.h(3, oa["label"])
            rows = [
                ("opening angle", "%s mrad = %s° = %s" % (doc.n(oa["angle_mrad"], 4), doc.n(oa["angle_deg"], 6), oa["angle_dms"])),
                ("chord a: vertex → %s" % oa["a"], "L = %s m, azimuth %s°, elevation %s°" % (doc.n(oa["L_a_m"], 3), doc.n(oa["azimuth_a_deg"], 5), doc.n(oa["elevation_a_deg"], 5))),
                ("chord b: vertex → %s" % oa["b"], "L = %s m, azimuth %s°, elevation %s°" % (doc.n(oa["L_b_m"], 3), doc.n(oa["azimuth_b_deg"], 5), doc.n(oa["elevation_b_deg"], 5))),
                ("horizontal / vertical components at the vertex", "Δazimuth %s° (%s mrad), Δelevation %s° (%s mrad)" % (
                    doc.n(oa["delta_azimuth_deg"], 5), doc.n(oa["horizontal_component_mrad"], 4), doc.n(oa["delta_elevation_deg"], 5), doc.n(oa["vertical_component_mrad"], 4))),
                ("%s transverse to the line vertex → %s" % (oa["a"], oa["b"]), "%s m (along it: %s m)" % (doc.n(oa["a_transverse_from_vb_m"], 3), doc.n(oa["a_along_vb_m"], 3))),
                ("%s transverse to the line vertex → %s" % (oa["b"], oa["a"]), "%s m" % doc.n(oa["b_transverse_from_va_m"], 3)),
                ("chord b − chord a", "%s m = %s µs = %s ticks" % (doc.sn(oa["dL_m"], 3), doc.sn(oa["dt_us"], 6), doc.sn(oa["dticks"], 3))),
                ("path vertex → a → b minus direct vertex → b", "%s m" % doc.n(oa["path_via_a_minus_direct_m"], 4)),
            ]
            if oa.get("beam_axis"):
                bx = oa["beam_axis"]
                rows += [("chord a vs beam axis (%s)" % bx["label"], "%s mrad (right %s, up %s)" % (
                             doc.n(bx["a_chord_vs_axis"]["angle_mrad"], 4), doc.sn(bx["a_chord_vs_axis"]["right_component_mrad"], 4), doc.sn(bx["a_chord_vs_axis"]["up_component_mrad"], 4))),
                         ("chord b vs beam axis", "%s mrad (right %s, up %s)" % (
                             doc.n(bx["b_chord_vs_axis"]["angle_mrad"], 4), doc.sn(bx["b_chord_vs_axis"]["right_component_mrad"], 4), doc.sn(bx["b_chord_vs_axis"]["up_component_mrad"], 4))),
                         ("%s off-axis at the axis origin" % oa["a"], "%s mrad, %s m transverse" % (doc.n(bx["a"]["off_axis_mrad"], 4), doc.n(bx["a"]["transverse_m"], 3))),
                         ("%s off-axis at the axis origin" % oa["b"], "%s mrad, %s m transverse" % (doc.n(bx["b"]["off_axis_mrad"], 4), doc.n(bx["b"]["transverse_m"], 3)))]
            if oa.get("axis_to"):
                rows += [("off-axis angles w.r.t. vertex → %s" % oa["axis_to"], "a: %s mrad, b: %s mrad" % (doc.n(oa["off_axis_a_mrad"], 3), doc.n(oa["off_axis_b_mrad"], 3))),
                         ("a and b on the same side of the axis", doc.n(oa["same_side_of_axis"])),
                         ("azimuthal separation about the axis", "%s°" % doc.n(oa["azimuth_about_axis_deg"], 3))]
            doc.kv(rows)
    for b in result["baselines"]:
        render_baseline(doc, b, st)
    return doc.render()
