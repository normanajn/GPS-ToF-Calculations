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
| ND (1015 m from target) → FD front face (Ant-2) | 809 549.587 | 2700.366754 | 172 823.472 | 272 743.854 (272 744) |
| NuMI target → FD front face (Ant-2)     | 810 564.610  | 2703.752507  | 173 040.160  | 272 960.542 (272 961) |
| NuMI target → ND (1015 m)               | 1 015.079    | 3.385939     | 216.700      |                     |
| ND placed under the mast → FD (superseded 2014-note geometry) | 809 616.263 | 2700.589164 | 172 837.706 | 272 758.088 (272 758) |
| 2013 notebook (FNAL −300 m, no FD offset) | 809 606.162 | 2700.555470  | 172 835.550  | 272 755.932 (272 756) |

**Beam axis.** `beam_axis: {from: target, to: minos-fd}` (CLI `-x target:minos-fd`) makes the
target → MINOS far detector line the reference for everything: each site gets its off-axis
angle, distance along the axis and transverse position (right/up looking downstream); each
baseline gets the opening angle between its chord and the axis with right/up components and the
off-axis position of both endpoints; each opening angle gets the angle of both chords to the axis.

| Site vs NuMI beam axis | off-axis (mrad) | along axis (m) | transverse (m) | right (m) | up (m) |
|---|---|---|---|---|---|
| Ash River Ant-2 front face | 14.575 | 810 478.5 | 11 813.8 | −11 051.4 | −4 175.3 |
| NOvA ND (1015 m from the target) | 12.466 | 1 015.0 | 12.653 | −11.570 | +5.123 |
| ND if under the mast (superseded) | 13.343 | 948.3 | 12.654 | −11.570 | +5.123 |
| TDR decay-pipe end | 0.020 | 724.2 | 0.014 | | |

The chord ND → FD makes 14.58 mrad with the axis.  The TDR design axis (target → decay-pipe end)
agrees with target → MINOS FD to 0.02 mrad.

Opening angle at the target between the ND and FD chords (config `opening_angles`, CLI `-a target:nd:fd2`):
10.440 mrad (0.5982°), of which −10.20 mrad is vertical and −2.24 mrad horizontal; the ND
endpoint lies 10.6 m above the target → FD line.  Both chords are reported with their
off-axis angles (12.47 and 14.58 mrad) relative to the beam axis.

The 2013 Mathematica notebook and the 2014 note are reproduced to 10⁻⁹ by the test suite
(`tests/test_nova_reproduction.py`).

## The NuMI target position

The GPS fixes in the 2013/2014 work are antenna positions; the target was never in the
calculation.  `config/nova.yaml` now carries the target, derived as follows:

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
| off-axis angle of the Ash River FD | 14.58 mrad | 14.6 mrad |

The design target is a metre-level position (as-built LE/ME target positions differ by up
to ~1 m longitudinally, and the as-built decay-pipe/MINOS FD distances differ from the
design by ~6 m).

**Near Detector placement.** The ND is not under the MINOS mast antenna: it is 1015 m from
the target along the beam.  `config/nova.yaml` therefore gives the ND in the beam-axis frame,
`axis_position: {along_m: 1015, right_m: -11.57, up_m: 5.12}`, i.e. 1015 m along the axis with
the transverse position taken from the mast antenna fix (the only survey information for the
transverse direction; it still carries the 1″ ≈ 30 m resolution of that coordinate).  The
antenna-under-mast geometry of the 2014 note put the ND 948 m from the target, 65 m short;
moving it shortens the ND → FD chord by 66.7 m, i.e. **−14.2 ticks** (172 837.7 → 172 823.5).
That superseded geometry is kept in the configuration as `nd-under-mast` for comparison.

## Layout

```
config/nova.yaml        NOvA example configuration (sites, baselines, timing shifts)
src/gps_tof/            package: angles, geodesy, projection, fermilab_site, nmea, model, calc, report, config, cli
tests/                  pytest suite (reproduction of the notebook, projection, config precedence, CLI)
man/                    gps-tof(1), gps-tof(5), gps-tof-nmea(1), gps-tof-fscs(1), gps_tof(3)
docs/DESIGN.md          design, methodology, decisions, references
docs/reference/         original Mathematica notebooks, 2014-note transcription, generator script
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


Version 0.4.0.  Python ≥ 3.9, PyYAML only.  55 tests.  No C/C++ library yet (the
geodesy core is small enough to port; see docs/DESIGN.md "Future work").
