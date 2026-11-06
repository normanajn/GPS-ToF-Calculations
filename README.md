# GPS-ToF-Calculations

Straight-line (chord) time-of-flight calculator for surveyed sites, written for the
NOvA beam-timing problem (NuMI target / Near Detector at Fermilab to the Far Detector at
Ash River) but general: any set of GPS fixes, Fermilab site coordinates or NMEA fixes, any
clock, any set of fixed timing shifts.

For every baseline the tool reports the chord, the flight time in seconds, clock ticks and
a legacy unit, and a **ledger of each correction** (Earth model, height datum, vertical and
horizontal antenna-to-endpoint offsets), followed by timing shifts, the trigger window,
chord geometry, non-geometric effects (Sagnac, neutrino mass, cable delays), sensitivities
and an error budget.

```
$ gps-tof -c config/nova.yaml -f md -o reports/nova.md
```

| NOvA baseline (config/nova.yaml)        | L (m)        | ToF (µs)     | 64 MHz ticks | + MI 141-turn shift |
|-----------------------------------------|--------------|--------------|--------------|---------------------|
| **ND upstream face → FD upstream face (both surveyed)** | **809 514.750** | **2700.250552** | **172 816.035** | **272 736.417 (272 736)** |
| NuMI target → FD upstream face (surveyed) | 810 509.171 | 2703.567584  | 173 028.325  | 272 948.707 (272 949) |
| NuMI target → ND upstream face (surveyed) | 994.424    | 3.317043     | 212.291      |                     |
| ND at the quoted 1015 m → FD (superseded placement) | 809 494.148 | 2700.181830 | 172 811.637 | 272 732.019 (272 732) |
| ND under the mast → FD from the Ant-2 fix (superseded 2014-note geometry) | 809 616.263 | 2700.589164 | 172 837.706 | 272 758.088 (272 758) |
| 2013 notebook (FNAL −300 m, no FD offset) | 809 606.162 | 2700.555470  | 172 835.550  | 272 755.932 (272 756) |

The 2013 Mathematica notebook and the 2014 note are reproduced to 10⁻⁹ by the test suite
(`tests/test_nova_reproduction.py`).

## Definitive detector positions (Fermilab alignment survey)

The Fermilab Survey, Alignment and Geodesy group supplied the upstream-face centres of both
NOvA detectors in the NuMI beamline coordinate system: origin MCZERO, X = beam right
(eastward looking downstream), Y = stationing (positive downstream), Z = up, orthogonal to
the beam.

| point | X right (m) | Y stationing (m) | Z up (m) | note |
|---|---|---|---|---|
| NOvA ND upstream face centre | −11.565000 | 993.350283 | −3.643551 | 3×3 module 158.125″; drawing 489389 |
| NOvA FD upstream face centre | −11 037.455993 | 810 422.323775 | −4 162.644422 | 7.5″ bookend from the rail/wall line; H = 1209.1058 ft NAVD88 |

`config/nova.yaml` records them as `axis_position` entries in the frame
`{origin: mczero, through: minos-fd}`, and the package converts them:

| point | latitude | longitude | h (WGS84, m) | ECEF X, Y, Z (m) |
|---|---|---|---|---|
| ND upstream face centre | 41° 50′ 24.3467″ N (41.84009631°) | 88° 16′ 13.7981″ W (−88.27049947°) | 96.572 | 143 628.970, −4 756 768.845, 4 232 452.856 |
| FD upstream face centre | 48° 22′ 41.5413″ N (48.37820593°) | 92° 49′ 50.7737″ W (−92.83077048°) | 337.611 | −209 624.380, −4 239 417.585, 4 745 165.129 |

How the frame was realised, and what checks it:

* **MCZERO** is taken as the upstream face of horn 1 from the 1998 TDR beam sheet (row 0089),
  1.5 m downstream of the target entrance; the as-built point is not public, so the origin is
  good to about 1 m along the beam (0.2 ns on an 810 km chord, nothing transverse).
* **Y axis.** Two candidate lines were tested: the 1998 design axis (target → decay-pipe end)
  and the as-built aiming line (MCZERO → MINOS FD midpoint).  The FD's independent NAVD88
  elevation, H = 1209.1058 ft = 368.535 m, i.e. h ≈ 336.07 m with the Ash River geoid
  separation of −32.46 m, is reproduced by the aiming line to **+1.5 m** (geoid-model level)
  and missed by the design axis by 17 m.  The aiming line is therefore the surveyors' Y axis,
  and it is what the configuration uses.
* **Consistency.** The chord MCZERO → FD equals √(X² + Y² + Z²) = 810 508.171 m exactly; the
  surveyed FD face is 58 m horizontally and 8.8 m vertically from the point obtained from the
  Ant-2 antenna fix with a −19.8 m offset (the horizontal antenna → detector vector the 2014
  note left TBD); the surveyed ND confirms the antenna's 11.57 m left offset to 5 mm but sits
  3.6 m below the axis and 993.35 m from MCZERO, not 1015 m.
* **Result.** With both surveyed faces the ND lies only 2.46 m off the target → FD line: the
  opening angle at the target between the ND and FD chords is 2.474 mrad (−1.99 horizontal,
  −1.47 vertical).  Both detectors are 12.19 and 14.55 mrad off the Soudan axis, at clock
  angles −107° and −111° (left of and below the axis).

**Detector face edges.** `face: {half_width_m, half_height_m}` on a site derives its left/right
(and top/bottom) edge points in the same beamline frame; the report lists their positions, their
angles to the beam axis, the angle the face subtends at the target, and left/centre/right versions
of every opening angle involving that detector.  The ND face is 158.125 in square (survey note),
the FD half-size 304.21 in.

| ND upstream face (surveyed) | angle to beam axis (mrad) | right (m) | opening angle to the FD chord (mrad) |
|---|---|---|---|
| left edge | 14.133 | −13.573 | 1.472 |
| centre | 12.194 | −11.565 | 2.474 |
| right edge | 10.285 | −9.557 | 4.270 |
| face width at the target | 4.039 mrad subtended | | |

Superseded geometries are kept in the configuration for comparison: `nd-1015` (the quoted
1015 m placement with antenna transverse offsets), `nd-under-mast` and `fd2` (the 2014-note
antenna-derived endpoints).

## The NuMI target position

The GPS fixes in the 2013/2014 work are antenna positions; the target was never in the
calculation.  `config/nova.yaml` carries the target, derived as follows:

1. The NuMI Facility Technical Design Report (rev 1.0, Oct 1998), Appendix A beam sheet,
   gives every beam element in Fermilab site (DUSAF/FSCS) coordinates in feet.  Row 0087
   `HALTA TAR-2` (target entrance) is x = 100327.838, y = 97780.188, z = 626.743 ft; the
   decay pipe end (row 0092 `DENCU`) is x = 98230.009, y = 98887.039, z = 488.477 ft.
2. Beams-doc-1148 (*Fermilab Coordinate Systems*, Survey Alignment and Geodesy group) defines
   the site frame as a double stereographic projection of NAD83/GRS80 with origin at monument
   A0 (N 41° 50′ 14.312704″, W 88° 15′ 41.143123″, h = 186.49880 m), Y axis along azimuth
   38° 16′ 48.01429″, scale 1.000029251309483, and the height relation
   h = H_DUSAF − 0.17308 m + N with N = −32.78456 m.  `gps_tof.fermilab_site` implements it
   (EPSG method 9809, verified against the EPSG worked example and the document's own CFMI
   control point).
3. Result: target at **41° 49′ 55.092″ N, 88° 15′ 55.909″ W, h = 158.07 m** (ellipsoidal).

Cross-checks (all in the test suite):

| check | computed | published |
|---|---|---|
| target → MINOS FD supermodule midpoint | 735 344.6 m | 735 338.0 m from horn-1 upstream end (NIM A 596, 2008) |
| beam azimuth at the target | 336.094° | 336.098° (Fermilab–Soudan geodetic survey, 1999) |
| beam dip at the target | 3.339° | 3.336° design pitch, 3.343° as-built (NIM A 806, 2016) |
| decay pipe length | 675.0 m | 675 m |
| off-axis angle of the surveyed FD face | 14.55 mrad | 14.6 mrad |

**Beam axis.** `beam_axis: {from: target, to: minos-fd}` (CLI `-x target:minos-fd`) makes the
target → MINOS far detector line the reference for everything: each site gets its off-axis
angle, distance along the axis and transverse position (right/up looking downstream); each
baseline gets the opening angle between its chord and the axis with right/up components and the
off-axis position of both endpoints; each opening angle gets the angle of both chords to the axis.

| Site vs NuMI beam axis | off-axis (mrad) | along axis (m) | transverse (m) | right (m) | up (m) |
|---|---|---|---|---|---|
| FD upstream face centre (surveyed) | 14.555 | 810 423.3 | 11 796.3 | −11 037.5 | −4 162.6 |
| ND upstream face centre (surveyed) | 12.194 | 994.4 | 12.125 | −11.565 | −3.644 |
| Ash River Ant-2 fix − 19.8 m (superseded) | 14.575 | 810 478.5 | 11 813.8 | −11 051.4 | −4 175.3 |
| ND at the quoted 1015 m (superseded) | 12.466 | 1 015.0 | 12.653 | −11.570 | +5.123 |
| TDR decay-pipe end | 0.020 | 724.2 | 0.014 | | |

The chord ND → FD makes 14.56 mrad with the axis.  The TDR design axis (target → decay-pipe end)
agrees with target → MINOS FD to 0.02 mrad in direction.

## Technical note

`docs/note/nova-tof-note.tex` is a NOvA-style technical note ("Determination of the Neutrino
Time of Flight from the NuMI Target to the NOvA Detectors: Coordinate Systems, Distances and
Timing Offsets") with the full derivations of all five coordinate systems, the distances,
flight times, timing shifts, angles, validation, error budget and an appendix reproducing the
2013/2014 work.  Its tables are generated from `reports/nova.json` by
`scripts/make_note_tables.py`, its figures are the PDF versions of `docs/figures/`, and the
built PDF is `docs/note/nova-tof-note.pdf`.  Build with `make -C docs/note` (TeX Live with
latexmk, natbib, siunitx, booktabs).  Local copies of every cited document are in
`docs/external/` (published papers, the TDR, Beams-doc-1148, the survey notes) and
`docs/reference/` (the 2013 notebook, NOvA-doc-11860 and its LaTeX source), each directory with
a provenance index and SHA-256 checksums.

## Layout

```
config/nova.yaml        NOvA example configuration (sites, baselines, timing shifts)
src/gps_tof/            package: angles, geodesy, projection, fermilab_site, nmea, model, calc, report, config, cli
tests/                  pytest suite (reproduction of the notebook, projection, config precedence, CLI)
man/                    gps-tof(1), gps-tof(5), gps-tof-nmea(1), gps-tof-fscs(1), gps_tof(3)
docs/DESIGN.md          design, methodology, decisions, references
docs/figures/           schematic figures as standalone SVG and PNG (scripts/export_figures.py)
docs/note/              technical note (LaTeX, generated tables, PDF figures, built PDF)
docs/external/          local copies of all cited external documents, with index and checksums
docs/reference/         2013 notebook, NOvA-doc-11860 (PDFs and LaTeX source), transcription, generator script
reports/                generated reports for config/nova.yaml (md, txt, json)
bootstrap.sh/.ps1       create venv, install, run tests;  start-gps-tof.sh  runs the tool from the venv
CMakeLists.txt          ctest + man-page install targets
```

## Install and run

See [INSTALL.md](INSTALL.md).  Short form (Linux, macOS, Windows PowerShell):

```
./bootstrap.sh            # or:  .\bootstrap.ps1
source venv/bin/activate  # or:  .\venv\Scripts\Activate.ps1
gps-tof -c config/nova.yaml
```

Opening angle at a vertex (`-a VERTEX:A:B[:LABEL[:AXIS]]`), e.g. `gps-tof -c config/nova.yaml -a target:nd:fd2::decay-end`.

Ad-hoc sites without a configuration file:

```
gps-tof -c /dev/null --clock-hz 100e6 \
   -s 'name=A id=a lat=41:50:23N lon=88:16:13W h=228 offset=0,0,-120' \
   -s 'name=B id=b lat="48 22.715780 N" lon="92 49.876930 W" h=348.638 offset=0,0,-19.8' -p a:b
```

Helpers: `gps-tof-nmea` (checksums, $GPGGA → site YAML), `gps-tof-fscs` (Fermilab site
coordinates ↔ geodetic).  Configuration precedence is command line > environment
(`GPS_TOF_*`) > `.env` > YAML file > defaults.

## Status

Project status page (phases, results, test and compatibility matrices, design decisions):
https://claude.ai/artifact/S4eqJocVhnzvuuP8ziAMf4

Not-to-scale schematic of the target, ND, FD and MINOS FD layout with the computed angles
(`docs/nova-schematic.html`): https://claude.ai/artifact/MHZuX5iAPTuxbCbFRRoqBY

The four figures are also exported as standalone files in `docs/figures/` (SVG and 2× PNG):
`01-plan-view`, `02-elevation-view`, `03-transverse-view`, `04-near-detector-front-face`.
Regenerate with `python3 scripts/export_figures.py` (man page `gps-tof-export-figures(1)`).


Version 0.7.0.  Python ≥ 3.9, PyYAML only.  61 tests.  No C/C++ library yet (the
geodesy core is small enough to port; see docs/DESIGN.md "Future work").
