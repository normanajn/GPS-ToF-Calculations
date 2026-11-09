#!/usr/bin/env python3
"""Generate the LaTeX tables of the technical note from reports/nova.json.

Usage:  python3 scripts/make_note_tables.py [--json reports/nova.json] [--out docs/note/generated]

Every number printed in the note comes from the JSON report written by
``gps-tof -c config/nova.yaml -f json``; this script turns it into tabular
bodies that the note \\input's, so the document cannot drift from the code.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def esc(s: str) -> str:
    s = str(s)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#"), ("$", r"\$"),
                 ("->", r"$\rightarrow$"), ("→", r"$\rightarrow$"), ("°", r"\textdegree{}"), ("′", "'"), ("″", "''"),
                 ("µ", r"\textmu{}"), ("×", r"$\times$"), ("−", "--"), ("±", r"$\pm$"), ("Δ", r"$\Delta$"), ("≈", r"$\approx$")):
        s = s.replace(a, b)
    return s


def dms(deg: float, kind: str) -> str:
    from gps_tof.angles import dms as _dms
    return esc(_dms(deg, kind))


def n(x, d=3):
    if x is None:
        return "--"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, int):
        return r"\num{%d}" % x
    return r"\num{%.*f}" % (d, x)


def sn(x, d=3):
    return "--" if x is None else r"\num{%+.*f}" % (d, x)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="reports/nova.json")
    ap.add_argument("--out", default="docs/note/generated")
    a = ap.parse_args()
    r = json.load(open(a.json))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sites = {s["id"]: s for s in r["sites"]}
    bl = {b["label"]: b for b in r["baselines"]}
    st = r["settings"]
    W = {}

    # ---- input positions -------------------------------------------------
    rows = []
    for sid in ("target", "mczero", "decay-end", "fnal-mast", "nd-under-mast", "fd1", "fd2", "fd3", "minos-fd", "vermilion", "two-harbors"):
        s = sites[sid]
        src = s["fscs_xyz_ft"]
        if src:
            given = "FSCS $x,y,z$ = %.3f, %.3f, %.3f ft" % tuple(src)
        elif s["datum"] == "msl":
            given = "%s, %s, $H$ = %s m (MSL), $N_g$ = %s m" % (dms(s["lat_deg"], "lat"), dms(s["lon_deg"], "lon"), n(s["height_given_m"], 3), n(s["geoid_separation_m"], 3))
        else:
            given = "%s, %s, $h$ = %s m (%s)" % (dms(s["lat_deg"], "lat"), dms(s["lon_deg"], "lon"), n(s["height_given_m"], 3), s["datum"])
        rows.append(r"%s & %s & %s & %s \\" % (esc(sid), esc(s["name"]), given, esc(s["source"])))
    W["inputs"] = "\n".join(rows)

    rows = []
    for sid in ("nd", "fd"):
        s = sites[sid]
        ap_ = s["axis_position"]
        rows.append(r"%s & %s & %s & %s & %s \\" % (esc(s["name"]), n(ap_["right_m"], 6), n(ap_["along_m"], 6), n(ap_["up_m"], 6), esc(ap_["frame"])))
    W["survey"] = "\n".join(rows)

    # ---- converted positions ---------------------------------------------
    rows = []
    for sid in ("target", "mczero", "decay-end", "nd", "nd-left", "nd-right", "fd", "fd-left", "fd-right", "minos-fd", "vermilion", "two-harbors", "nd-1015", "nd-under-mast", "fd2"):
        s = sites[sid]
        e = s["ecef_endpoint_m"]
        rows.append(r"%s & %s & %s & %s & %s & %s & %s \\" % (esc(sid), dms(s["endpoint_lat_deg"], "lat"), dms(s["endpoint_lon_deg"], "lon"),
                    n(s["endpoint_h_m"], 3), n(e[0], 3), n(e[1], 3), n(e[2], 3)))
    W["positions"] = "\n".join(rows)
    rows = []
    for sid in ("target", "mczero", "nd", "fd", "minos-fd", "vermilion", "two-harbors"):
        s = sites[sid]
        rows.append(r"%s & %s & %s & %s \\" % (esc(sid), r"\num{%.9f}" % s["endpoint_lat_deg"], r"\num{%.9f}" % s["endpoint_lon_deg"], n(s["endpoint_h_m"], 3)))
    W["positions_decimal"] = "\n".join(rows)

    # ---- baselines ---------------------------------------------------------
    rows = []
    for b in r["baselines"]:
        rr, tt = b["result"], b["total"]
        rows.append(r"%s & %s & %s & %s & %s & %s & %s \\" % (esc(b["label"]), n(rr["L_m"], 3), n(rr["t_us"], 6), n(rr["ticks"], 3),
                    n(tt["ticks"], 3), n(tt["ticks_int"]), n(b["beam_axis"]["chord_vs_axis"]["angle_mrad"], 4) if b.get("beam_axis") else "--"))
    W["baselines"] = "\n".join(rows)

    # spherical vs ellipsoid per baseline (ledger rows 0 and final)
    rows = []
    for b in r["baselines"]:
        L0 = b["ledger"][0]["L_m"]; L1 = b["ledger"][1]["L_m"]; Lf = b["result"]["L_m"]
        rows.append(r"%s & %s & %s & %s & %s & %s \\" % (esc(b["label"]), n(L0, 3), n(L1, 3), sn(L1 - L0, 3), n(Lf, 3), sn(Lf - L1, 3)))
    W["models"] = "\n".join(rows)

    def ledger(label):
        rows = []
        for l in bl[label]["ledger"]:
            rows.append(r"%s & %s & %s & %s & %s & %s \\" % (esc(l["step"]), esc(l["description"]), n(l["L_m"], 3), sn(l["dL_m"], 3), sn(l["dt_ns"], 2), sn(l["dticks"], 3)))
        return "\n".join(rows)
    W["ledger_ndfd"] = ledger("ND upstream face -> FD upstream face (both surveyed)")
    W["ledger_2014"] = ledger("ND under the mast -> FD from the Ant-2 fix (superseded 2014-note geometry)")

    def geom(label):
        g = bl[label]["geometry"]
        return [n(g["central_angle_deg"], 5), n(g["surface_arc_mean_radius_m"], 1), n(g["arc_minus_chord_m"], 2), n(g["sagitta_m"], 1),
                n(g["azimuth_at_source_deg"], 5), n(g["elevation_at_source_deg"], 5), n(g["elevation_at_target_deg"], 5), n(g["deepest_point_h_m"], 0)]
    rows = []
    for label, short in (("ND upstream face -> FD upstream face (both surveyed)", "ND $\\rightarrow$ FD"),
                         ("NuMI target -> FD upstream face (surveyed)", "target $\\rightarrow$ FD"),
                         ("NuMI target -> ND upstream face (surveyed)", "target $\\rightarrow$ ND"),
                         ("NuMI target -> MINOS FD (validation of the target position)", "target $\\rightarrow$ MINOS FD"),
                         ("NuMI target -> Lake Vermilion (-100 ft)", "target $\\rightarrow$ Lake Vermilion"),
                         ("NuMI target -> Lake Superior, Two Harbors (-100 ft)", "target $\\rightarrow$ Two Harbors")):
        rows.append(short + " & " + " & ".join(geom(label)) + r" \\")
    W["geometry"] = "\n".join(rows)

    # ---- beam axis -----------------------------------------------------------
    ax = r["beam_axis"]
    W["axis"] = r"%s & %s & %s & %s & %s \\" % (esc(ax["label"]), n(ax["length_m"], 3), n(ax["azimuth_at_origin_deg"], 5), n(ax["elevation_at_origin_deg"], 5),
                                                "(%.9f, %.9f, %.9f)" % tuple(ax["unit_ecef"]))
    rows = []
    for sid in ("target", "mczero", "decay-end", "nd", "fd", "minos-fd", "vermilion", "two-harbors", "nd-1015", "nd-under-mast", "fd2", "fnal-mast"):
        s = sites[sid]; va = s["vs_axis"]
        rows.append(r"%s & %s & %s & %s & %s & %s & %s \\" % (esc(sid), n(va["off_axis_mrad"], 4), n(va["along_axis_m"], 3), n(va["transverse_m"], 3),
                    sn(va["transverse_right_m"], 3), sn(va["transverse_up_m"], 3), n(va["clock_angle_deg"], 2) if va["clock_angle_deg"] is not None else "--"))
    W["vs_axis"] = "\n".join(rows)

    rows = []
    for oa in r["opening_angles"]:
        bx = oa.get("beam_axis") or {}
        rows.append(r"%s & %s & %s & %s & %s & %s & %s \\" % (esc(oa["label"]), n(oa["angle_mrad"], 4), sn(oa["horizontal_component_mrad"], 4), sn(oa["vertical_component_mrad"], 4),
                    n(oa["a_transverse_from_vb_m"], 3), n(bx["a_chord_vs_axis"]["angle_mrad"], 4) if bx else "--", n(bx["b_chord_vs_axis"]["angle_mrad"], 4) if bx else "--"))
    W["opening"] = "\n".join(rows)

    # ---- faces -----------------------------------------------------------------
    for f in r["faces"]:
        rows = []
        for pt in f["points"]:
            va = pt["vs_axis"]
            rows.append(r"%s & %s & %s & %s & %s & %s & %s & %s \\" % (pt["edge"], dms(pt["lat_deg"], "lat"), dms(pt["lon_deg"], "lon"), n(pt["h_m"], 3),
                        n(va["off_axis_mrad"], 4), sn(va["transverse_right_m"], 3), sn(va["transverse_up_m"], 3), n(va["clock_angle_deg"], 2)))
        W["face_" + f["site_id"].replace("-", "")] = "\n".join(rows)
        sb = f["subtended_at_axis_origin_mrad"]
        W["face_%s_subtended" % f["site_id"]] = "%s mrad (left--right) and %s mrad (top--bottom)" % (n(sb["left_right"], 4), n(sb["top_bottom"], 4))
        for v in f["opening_angles"]:
            if "FD (both surveyed)" in v["label"] or "surveyed) vs MINOS" in v["label"]:
                key = "face_%s_vs_%s" % (f["site_id"], "fd" if "FD (both" in v["label"] else "minos")
                W[key] = "\n".join(r"%s & %s & %s & %s & %s & %s \\" % (e["edge"], n(e["angle_mrad"], 4), sn(e["horizontal_component_mrad"], 4),
                                   sn(e["vertical_component_mrad"], 4), n(e["transverse_m"], 3), n(e["chord_vs_axis_mrad"], 4)) for e in v["edges"])

    # ---- timing --------------------------------------------------------------
    b = bl["ND upstream face -> FD upstream face (both surveyed)"]
    rr, tt, w = b["result"], b["total"], b["window"]
    W["clock"] = r"%s & %s & %s" % (n(rr["clock_hz"] / 1e6, 4), n(rr["tick_ns"], 4), n(rr["metres_per_tick"], 4))
    rows = []
    for lab in ("ND upstream face -> FD upstream face (both surveyed)", "NuMI target -> FD upstream face (surveyed)", "NuMI target -> ND upstream face (surveyed)",
                "MCZERO -> FD upstream face (surveyed; stationing 810,422.324 m)", "MCZERO -> ND upstream face (surveyed; stationing 993.350 m)",
                "NuMI target -> Lake Vermilion (-100 ft)", "ND upstream face -> Lake Vermilion (-100 ft)",
                "NuMI target -> Lake Superior, Two Harbors (-100 ft)", "ND upstream face -> Lake Superior, Two Harbors (-100 ft)"):
        x = bl[lab]; rr2, tt2 = x["result"], x["total"]
        rows.append(r"%s & %s & %s & %s & %s & %s & %s & %s \\" % (esc(lab), n(rr2["L_m"], 3), n(rr2["t_us"], 6), n(rr2["ticks"], 3), n(rr2["ticks_int"]),
                    sn(rr2["rounding_residual_ns"], 2), n(rr2["legacy_units"], 4), n(tt2["ticks"], 3)))
    W["timing"] = "\n".join(rows)
    sh = b["timing_shifts"][0]
    W["mishift"] = r"%s & %s & %s & %s & %s & %s & %s" % (n(sh["turns"], 0), n(sh["buckets_per_turn"], 0), n(sh["rf_hz"] / 1e6, 4), n(sh["t_rev_us"], 6), n(sh["ticks_per_turn"], 3), n(sh["us"], 6), n(sh["ticks"], 3))
    W["mishift_khz"] = n(sh["ticks_per_khz_rf"], 3)
    W["total"] = r"%s & %s & %s & %s & %s" % (n(rr["ticks"], 3), n(tt["shift_ticks"], 3), n(tt["ticks"], 3), n(tt["ticks_int"]), sn(tt["rounding_residual_ns"], 2))
    W["window"] = r"%s & %s & %s & %s & %s & %d--%d" % (n(w["tof_lo_ticks"], 2), n(w["tof_hi_ticks"], 2), n(w["total_lo_ticks"], 2), n(w["total_hi_ticks"], 2), n(w["microslice_ticks"], 0), w["microslices_min"], w["microslices_max"])
    e = b["effects"]
    rows = [r"Sagnac (Earth rotation, ECEF frame) & %s & %s & reported, not applied \\" % (sn(e["sagnac_ns"], 3), sn(e["sagnac_ticks"], 4)),
            r"neutrino mass delay ($m=\SI{%g}{eV}$, $E=\SI{%g}{GeV}$) & \num{%.2e} & \num{%.2e} & negligible \\" % (e["neutrino_mass_ev"], e["neutrino_energy_gev"], e["neutrino_delay_ns"], e["neutrino_delay_ns"] * 1e-9 * st["clock_hz"])]
    for c in e["cables"]:
        rows.append(r"antenna cable delay, %s & %s & %s & receiver calibration, not ToF \\" % (esc(c["site"]), n(c["delay_ns"], 2), n(c["delay_ticks"], 3)))
    W["effects"] = "\n".join(rows)

    rows = []
    for s_ in b["sensitivities"]:
        rows.append(r"%s & %s & %s & %s \\" % (esc(s_["label"]), sn(s_["dL_m"], 4), sn(s_["dt_ns"], 3), sn(s_["dticks"], 4)))
    W["sensitivities"] = "\n".join(rows)
    eb = b["error_budget"]
    rows = [r"%s & %s & %s & %s & %s \\" % (esc(i["source"]), n(i["sigma_ns"], 2), n(i["sigma_ticks"], 3), i["type"], "yes" if i["combined"] else "no") for i in eb["items"]]
    W["budget"] = "\n".join(rows)
    W["budget_rss"] = r"root-sum-square %s ticks (%s ns), linear sum %s ticks (%s ns)" % (n(eb["rss_ticks"], 3), n(eb["rss_ns"], 1), n(eb["linear_sum_ticks"], 3), n(eb["linear_sum_ns"], 1))

    # ---- validation ------------------------------------------------------------
    tm = bl["NuMI target -> MINOS FD (validation of the target position)"]
    fdv = sites["fd"]["vs_axis"]
    H = 1209.1058 * 0.3048
    W["validation"] = "\n".join([
        r"target $\rightarrow$ MINOS FD midpoint & %s m & \num{735338.0} m from horn 1 \citep{minos2008} & %s m \\" % (n(tm["result"]["L_m"], 1), sn(tm["result"]["L_m"] - 735338.0, 1)),
        r"beam azimuth at the target & %s\textdegree{} & 336.09788\textdegree{} \citep{bocean1999} & %s\textdegree{} \\" % (n(tm["geometry"]["azimuth_at_source_deg"], 5), sn(tm["geometry"]["azimuth_at_source_deg"] - 336.09788, 5)),
        r"beam dip at the target & %s\textdegree{} & 3.34349\textdegree{} \citep{numibeam2016} & %s\textdegree{} \\" % (n(-tm["geometry"]["elevation_at_source_deg"], 5), sn(-tm["geometry"]["elevation_at_source_deg"] - 3.34349, 5)),
        r"decay-pipe length (TDR stations) & %s m & 675 m \citep{numibeam2016} & -- \\" % n(bl["NuMI target -> decay-pipe end (TDR design axis)"]["result"]["L_m"] - (1307.48377 - 1146.09958) * 0.3048006096, 1),
        r"FD ellipsoidal height from the survey frame & %s m & $H + N_g = %.3f - 31.221 = %.3f$ m (GEOID18) & %s m \\" % (n(sites["fd"]["h_ellipsoidal_m"], 3), H, H - 31.221, sn(sites["fd"]["h_ellipsoidal_m"] - (H - 31.221), 2)),
        r"\quad same, with the receiver's geoid separation & %s m & $%.3f - 32.462 = %.3f$ m & %s m \\" % (n(sites["fd"]["h_ellipsoidal_m"], 3), H, H - 32.462, sn(sites["fd"]["h_ellipsoidal_m"] - (H - 32.462), 2)),
        r"MCZERO $\rightarrow$ FD chord vs $|(X,Y,Z)|$ & %s m & %s m & %s m \\" % (n(bl["MCZERO -> FD upstream face (surveyed; stationing 810,422.324 m)"]["result"]["L_m"], 4),
            n(math.sqrt(810422.323775**2 + 11037.455993**2 + 4162.644422**2), 4), sn(bl["MCZERO -> FD upstream face (surveyed; stationing 810,422.324 m)"]["result"]["L_m"] - math.sqrt(810422.323775**2 + 11037.455993**2 + 4162.644422**2), 6)),
        r"off-axis angle of the FD face & %s mrad & 14.6 mrad \citep{novasurvey} & -- \\" % n(fdv["off_axis_mrad"], 3),
    ])

    # ---- 2013 / 2014 reproduction (recomputed here with the package) -------
    from gps_tof.model import Problem
    from gps_tof.calc import compute_baseline
    def prob(sites_, shifts=None, **kw):
        d = {"sites": sites_, "timing_shifts": shifts or []}; d.update(kw); return Problem.from_dict(d)
    FN = dict(name="FNAL", lat="41 50 23 N", lon="88 16 13 W"); A1 = dict(name="Ash1", lat="48 22.715780 N", lon="92 49.876930 W")
    ps = prob([dict(FN, height_m=-72), dict(A1, height_m=348.0)], earth={"model": "sphere"}); bs = compute_baseline(ps, ps.baselines[0])
    pw = prob([dict(FN, height_m=-72), dict(A1, height_m=348.638)], [dict(name="MI", turns=141, buckets_per_turn=588, rf_hz=53.1034e6)]); bw = compute_baseline(pw, pw.baselines[0])
    p14 = prob([dict(FN, height_m=228, offset_enu_m=[0, 0, -120]), dict(A1, height_m=348.638, offset_enu_m=[0, 0, -19.8])]); b14 = compute_baseline(p14, p14.baselines[0])
    refs = [("2013 notebook, spherical chord (m)", bs["result"]["L_m"], 810429.1726392909, 4),
            ("2013 notebook, WGS84 chord (m)", bw["result"]["L_m"], 809606.1622206265, 4),
            ("2013 notebook, ToF (\\textmu{}s)", bw["result"]["t_us"], 2700.555469679716, 6),
            ("2013 notebook, ToF (ticks)", bw["result"]["ticks"], 172835.5500595018, 4),
            ("2013 notebook, MI shift (ticks)", bw["timing_shifts"][0]["ticks"], 99920.38174580157, 4),
            ("2013 notebook, total (ticks)", bw["total"]["ticks"], 272755.9318053034, 4),
            ("2014 note offsets, WGS84 chord (m)", b14["result"]["L_m"], None, 4)]
    rows = []
    for lab, comp, ref, d in refs:
        rel = ("\\num{%.1e}" % (abs(comp - ref) / abs(ref))) if ref else "--"
        rows.append(r"%s & %s & %s & %s \\" % (lab, n(comp, d), n(ref, d) if ref else "--", rel))
    W["reproduction"] = "\n".join(rows)
    hist = [("2013 notebook: antenna $-$300 m, no FD offset", bw["result"]["ticks"]),
            ("2014 note: antenna $-$120 m, FD antenna $-$19.8 m", b14["result"]["ticks"]),
            ("ND at the quoted 1015 m, antenna transverse", bl["ND at the quoted 1015 m -> FD (superseded ND placement)"]["result"]["ticks"]),
            ("surveyed faces (this note)", rr["ticks"])]
    rows = [r"%s & %s & %s \\" % (lab, n(v, 3), sn(v - rr["ticks"], 3)) for lab, v in hist]
    W["history"] = "\n".join(rows)

    rows = []
    for lab in ("NuMI target -> Lake Vermilion (-100 ft)", "NuMI target -> Lake Superior, Two Harbors (-100 ft)"):
        for l in bl[lab]["ledger"]:
            rows.append(r"%s & %s & %s & %s & %s & %s \\" % (esc(lab.split(" -> ")[1]), esc(l["step"]), n(l["L_m"], 3), sn(l["dL_m"], 3), sn(l["dt_ns"], 2), sn(l["dticks"], 3)))
    W["ledger_lakes"] = "\n".join(rows)
    W["meta"] = r"\newcommand{\gpstofversion}{%s}\newcommand{\reportgenerated}{%s}" % (r["gps_tof_version"], r["generated"][:10])
    # A table body read with \input must carry its own \bottomrule: LaTeX's end-of-file handling
    # after the final \\ breaks the \noalign scan if the rule follows in the including file.
    for k, v in W.items():
        if v.rstrip().endswith("\\\\"):
            v = v.rstrip() + "\n\\bottomrule"
        (out / (k + ".tex")).write_text(v + "\n", encoding="utf-8")
    print("wrote %d tables to %s" % (len(W), out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
