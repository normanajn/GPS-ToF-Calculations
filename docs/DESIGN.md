# Design, methodology and decisions

## 1. Problem

A beam timing system needs the expected delay between a timestamp taken at the source and
the arrival of relativistic particles at a remote detector, in integer ticks of the
detector clock.  The inputs are survey positions of GPS antennas (or of beam elements in a
site coordinate system), the displacement from each antenna to the physics endpoint, and
fixed timing-reference offsets.  The 2013 Mathematica notebook and the 2014 note did this
once, by hand, for one pair of points.  This package does it for any set of points and
writes down every correction so that each number in the result can be traced to an input.

## 2. Method

1. **Angles to geodetic coordinates.**  Latitude and longitude are accepted in all the forms
   that appear in survey records (DMS, degrees and decimal minutes, NMEA ddmm.mmmm).
   Longitudes are east-positive internally.  The 2013 notebook used positive (east)
   longitudes for both sites; distances are invariant under that reflection but the Sagnac
   term is not, so the sign is handled explicitly and tested.
2. **Heights to ellipsoidal heights.**  The ECEF transform needs the height above the
   ellipsoid.  A GPS receiver's `$GPGGA` altitude is orthometric (MSL); the geoid separation
   in the same sentence converts it.  Each site declares its datum; the conversion is a
   ledger row, not a silent fix.
3. **Geodetic to ECEF.**  Standard WGS84 (or GRS80, or a sphere) transformation
   `X = (N+h) cos φ cos λ`, `Y = (N+h) cos φ sin λ`, `Z = (N(1−e²)+h) sin φ`.
4. **Antenna to endpoint.**  The offset vector is given in the local East/North/Up frame at
   the antenna and rotated into ECEF.  "Up" is the ellipsoid normal (`geodetic`) or the
   geocentric direction (`radial`, the sphere-tangent plane described in the 2014 note);
   the difference is reported as a sensitivity.  Vertical and horizontal parts are separate
   ledger rows so the dominant vertical term is visible on its own.
5. **Chord and time.**  `L = |p_B − p_A|`, `t = L/c`.  Particles travel the chord through the
   Earth, not the surface arc; the arc − chord difference (544 m, 116 ticks for NOvA) is
   printed as a reminder.
6. **Ticks.**  `n = t · f_clock`, with the integer convention (round/floor/ceil) selectable
   and the residual reported in ns.
7. **Timing shifts.**  Fixed offsets (e.g. 141 Main Injector turns of 588 buckets at the
   flat-top RF) are added to the flight time to form the total offset.
8. **Opening angles.**  For two chords sharing a vertex site (target → ND and target → FD)
   the angle is computed from the fully corrected ECEF endpoints, decomposed into azimuth
   and elevation differences at the vertex, and expressed as the transverse distance of each
   endpoint from the other chord (L sin θ) and as the difference of the two flight times.
   With a reference axis the off-axis angle of each chord and whether the endpoints lie on
   the same side of the axis are added.
9. **Beam axis.**  A global reference line from an origin site through a second site (NuMI:
   target → MINOS far detector, which is where the beam was aimed).  A right-handed frame
   (u along the axis, h to the right looking downstream, v up) is built at the origin; every
   site endpoint is expressed as off-axis angle at the origin, distance along the axis and
   transverse (right, up) position; every chord gets its opening angle to the axis with
   right/up components; opening angles report both chords against the axis.
10. **Sensitivities.**  Numerical partial derivatives of L for each site: height, latitude,
   longitude (per arcsecond), endpoint moved East/North, plus method and model variants.
11. **Error budget.**  Declared uncertainties per site multiplied by the sensitivities;
   coordinate quantization gives both an RMS (uniform rounding, /√12) and a worst-case
   entry; the RF-frequency uncertainty of a turn-based shift; rounding and neglected terms
   are listed but not combined.

## 3. The correction ledger

The ledger is built progressively from site clones that carry only the corrections applied
so far: reference model → chosen model → datum conversion per site → vertical offset per
site → horizontal offset per site.  The chain must close on the directly computed final
chord to 1 µm or the engine raises.  The reference row is the model *not* chosen (sphere for
an ellipsoid run), which keeps the historical "sanity check" visible without making it a
setting.

## 4. The NuMI target

Decision: derive the target from the 1998 TDR beam sheet and the Fermilab site projection
rather than from a secondary quoted latitude/longitude, because

* the beam sheet is the primary design document and gives the whole beamline in one frame
  (target, horns, decay pipe, absorber), so the beam axis and off-axis angles come for free;
* Beams-doc-1148 defines the frame exactly (projection, origin, azimuth, scale, datum
  offsets), and the conversion verifies against the document's own CFMI control point to
  0.1 mm and against the EPSG worked example for the projection;
* the result is checked by three independent published numbers: the target → MINOS far
  detector distance (NIM A 596), the Fermilab–Soudan geodetic azimuth (1999 survey) and the
  NOvA off-axis angle (14.6 mrad).

Approximations: the geoid separation is taken constant across the site (N at A0; the
A0 → CFMI difference is 1.3 cm); the beam sheet is the design, not the as-built survey
(target longitudinal positions changed with the LE/ME configurations by up to ~1 m, and the
as-built target → MINOS FD distance differs from this design value by ~6 m).  Both are far
below the 1″ (≈ 30 m) resolution of the published MINOS-mast antenna coordinates that
dominate the error budget of the ND end.

Near Detector placement (v0.4.0): the ND is not under the MINOS mast antenna.  The
2014-note geometry (antenna minus 120 m) puts the endpoint 948 m from the target, 65 m short
of the 1015 m at which the ND actually sits along the beam.  The ND is therefore given in the
beam-axis frame, `axis_position: {along_m: 1015, right_m: -11.57, up_m: 5.12}`: the along-axis
distance from the quoted placement, the transverse position from the antenna fix (the only
transverse survey information available, still at 1″ ≈ 30 m resolution).  Moving the ND
66.7 m further along a chord that is itself nearly along the beam shortens ND → FD by 66.7 m,
i.e. −14.2 ticks (172 837.7 → 172 823.5), and lengthens target → ND by 66.7 m (+14.2 ticks),
so the target-referenced total is unchanged to 0.01 tick.  (An earlier version of this
document estimated the ND → FD effect at ~1 tick; that was wrong: the ND moves along the
chord, not transverse to it.)  The superseded geometry is kept as site `nd-under-mast`.

## 4a. The surveyed detector faces (v0.5.0)

The Fermilab alignment group's survey gives both NOvA upstream-face centres in the NuMI
beamline system (origin MCZERO; X right, Y stationing, Z up orthogonal to the beam).  These
are the definitive endpoints; the antenna-derived positions and the quoted 1015 m placement
are kept only as superseded comparisons.  The frame is realised with `frame_from_sites`
(u along the line, h = u × n̂ to the right, v = h × u up, n̂ the ellipsoid normal at the
origin), which is the same construction as the global beam-axis frame:

* MCZERO = TDR 1998 horn-1 upstream face (row 0089), 1.5 m downstream of the target entrance;
  the as-built point is not public (±1 m along the beam).
* The Y axis is the as-built aiming line MCZERO → MINOS FD midpoint.  This choice is tested,
  not assumed: the surveyed FD elevation H = 1209.1058 ft NAVD88 (h ≈ 336.07 m with
  N = −32.46 m) is reproduced to +1.5 m by the aiming line and missed by 17 m by the 1998
  design axis (target → decay-pipe end).  The 1.5 m residual is at the level of the geoid
  model and datum differences (NAVD88 vs the receiver's MSL) and the deflection of the
  vertical at the origin (a 2″ deflection is 8 m at 810 km), and is quoted as the systematic
  on the FD height.
* Checks: |(X, Y, Z)| equals the MCZERO → FD chord to 10 µm; the surveyed FD is 58 m
  horizontally and 8.8 m vertically from the Ant-2-derived face (the TBD horizontal vector of
  the 2014 note); the surveyed ND reproduces the antenna's 11.57 m left offset to 5 mm but is
  3.6 m below the axis and 993.35 m from MCZERO (994.9 m from the target), not 1015 m.
* Result: ND → FD = 809 514.750 m, 2700.250552 µs, 172 816.035 ticks; with the MI shift
  272 736.417 → 272 736 ticks.  The ND lies 2.46 m off the target → FD line (opening angle
  2.474 mrad), so for timing purposes the ND is on the line of sight to the FD.

## 4b. Detector face edges (v0.6.0)

A site may carry `face: {half_width_m, half_height_m}`.  `Problem.from_dict` then derives
edge sites (`<id>-left`, `-right`, `-top`, `-bottom`) by offsetting the centre in the
transverse directions of the site's own beamline frame (or of the global beam axis for a
geodetic site), before the axis-frame resolution runs, so the edges are ordinary sites
afterwards: they appear in the site tables, can be named in baselines and opening angles,
and `compute_face` reports their positions, their angles to the axis, the subtended angle at
the axis origin, and the left/centre/right variants of every configured opening angle that
involves the parent.  The face is taken perpendicular to the beamline frame rather than to
the detector's own axis; for the ND (12 mrad off axis, 2 m half-width) the difference is
3 cm, far below the survey uncertainty.

ND front face (158.125 in square): left / centre / right edges 14.133 / 12.194 / 10.285 mrad
from the beam axis; the face subtends 4.039 mrad at the target; opening angles to the FD
chord 1.472 / 2.474 / 4.270 mrad (the left edge is nearest the target → FD line).

## 5. Decisions

| decision | choice | why |
|---|---|---|
| language | Python 3.9+, stdlib + PyYAML | user preference; the maths is a few hundred lines; no NumPy so it runs anywhere |
| results as plain dicts | yes | one structure feeds text, Markdown and JSON; tests read keys directly |
| offsets as ENU vectors | surveyed point → endpoint, down negative | one convention for vertical and horizontal, no sign flips per site |
| datum explicit per site | `datum: ellipsoid|msl` + `geoid_separation_m` | the 2014 note spent a section on this ambiguity; make it an input |
| site frame | FSCS double stereographic (EPSG 9809) | exact definition available; needed for the target and any other beam element |
| projection code | own implementation, EPSG formulas | avoids a pyproj dependency; verified against the EPSG example |
| config precedence | CLI > env > .env > YAML > defaults | global project convention |
| sensitivities numeric | finite differences on cloned sites | no analytic derivatives to maintain; steps configurable |
| timing shifts generic | `seconds` or `turns×buckets/f_RF` | covers the MI shift and any fixed latency |
| reference axis | optional `axis_to` per baseline | off-axis angle is the natural check of a beam-element position |
| beam axis | global `beam_axis: {from, to}`, defaulting the reference for every site, baseline and opening angle | the physics question is always "relative to the beam"; one definition, used everywhere, replaces per-item `axis_to` (kept as an override) |
| surveyed faces | `nd` and `fd` are the alignment-group points in the MCZERO frame; antenna-derived and quoted placements kept as `fd2`, `nd-under-mast`, `nd-1015` | a survey beats a GPS antenna fix plus an unknown offset; the history stays visible in the report |
| face edges | `face: {half_width_m, half_height_m}` derives edge sites in the beamline frame | left/centre/right angles are a geometry question about one physical face; deriving ordinary sites keeps every report section consistent |
| sites in the axis frame | `axis_position: {along_m, right_m, up_m}` or `{along_m, off_axis_mrad, clock_deg}` resolved to geodetic at load time | beam-element and detector placements are quoted along the beam, not as lat/lon; the configuration should say what is actually known |
| opening angles | explicit `opening_angles` list (vertex, a, b), CLI `-a` | the user's question is a specific pair of chords; computing every shared-vertex pair would bury it in near-zero antenna-to-antenna angles |
| legacy notebook files | moved to `docs/reference/` | keep provenance, keep the top level for the package |

Opening angle at the target, ND vs FD (Ant-2): 10.440 mrad, −10.20 mrad vertical and
−2.24 mrad horizontal, so the ND endpoint is 10.6 m above the target → FD line (within the
~30 m resolution of the antenna coordinate).  Against the MINOS FD the angle is 12.47 mrad,
mostly horizontal, as expected for an on-axis far detector.

Relative to the beam axis (target → MINOS FD): the Ash River front face is 14.575 mrad off
axis, 11.05 km to the left and 4.18 km below the axis at 810.5 km along it (the "12 km west of
the beam" of the NOvA papers); the ND endpoint is 12.47 mrad off axis, 11.6 m left and
5.1 m up at 1015 m; the TDR design axis (target → decay-pipe end) agrees with the target → MINOS
FD line to 0.02 mrad.  The ND at 1015 m is 12.47 mrad off axis.

Surveyed faces: ND 12.19 mrad and FD 14.55 mrad off the Soudan axis, both left of and below it
(clock −107° and −111°); ND → FD chord 14.56 mrad to the axis.

## 6. Verification

* 2013 notebook: spherical and WGS84 chords, ToF, ticks, MI shift and total reproduced to
  10⁻⁹ relative.
* 2014 note: the +10.1 m change from its offsets, the −2.08 m MSL-datum term, the
  sensitivities (±27.98/9.62/27.24 m per arcsecond, 0.063 m/m), geometry (7.290°, 335.3°,
  3.613° dip, 544 m arc − chord) and the quantization error budget (1.8 / 4.0 ticks).
* Projection: EPSG 9809 Amersfoort example to 2 mm; FSCS A0 round trip; CFMI control point.
* Target: MINOS FD distance within 10 m of 735 338 m; azimuth 336.098 ± 0.01°; off-axis
  14.6 ± 0.1 mrad; decay-pipe station length.
* Survey points: the beamline (X, Y, Z) of both faces are reproduced in the MCZERO frame to
  10 µm, the FD lands within 2 m of its NAVD88 elevation, the MCZERO → FD chord equals
  |(X, Y, Z)|, and the headline ND → FD numbers are pinned.
* Configuration: override order, .env parsing, YAML exponent strings, ad-hoc CLI sites,
  NMEA and FSCS helpers.

## 7. Future work

* C/C++ port of `geodesy`, `projection`, `fermilab_site` and the chord/ledger core with
  Python bindings, per the project convention of shipping both.
* Horizontal antenna → detector vectors once surveyed (Table 3 of the 2014 note).
* As-built target positions per NuMI configuration (LE010, ME) from the Fermilab alignment
  database, replacing the TDR design row.
* Geoid model lookup (GEOID12/18) instead of the constant N across the site.

## 8. References

* A. Norman, *Determination of the Neutrino Time of Flight, Fermilab to Ash River*, NOvA draft note, Aug 2014 (transcribed in `docs/reference/NOvA_GPS_ToF_Timing_Offsets.md` and `.nb`).
* `FNAL_to_AshRiver_Distance.nb`, Mathematica, 2013–2017 (`docs/reference/`).
* NuMI Facility Technical Design Report, rev 1.0, Oct 1998, Appendix A beam sheet "horn2 ces" (FERMILAB-DESIGN-1998-01).
* B. Oshinowo, *Fermilab Coordinate Systems*, Beams-doc-1148 / MI-0209 v4.0, 1997 (SSO-protected; parameters reproduced in `gps_tof/fermilab_site.py`).
* V. Bocean, *Geodetic determinations for the NuMI project at Fermilab*, FERMILAB-CONF-99-480-PPD (Tables 3–4: 66589 → SHAFT azimuth 336° 05′ 52.36″, vertical angle −3° 17′ 17.88″, 735 273.058 m).
* D.G. Michael et al. (MINOS), *The magnetized steel and scintillator calorimeters of the MINOS experiment*, NIM A 596 (2008) 190, sec. 6.5 (FD midpoint 47.820267 N, 92.241412 W, h = −248.4 m NAD83; 735.3380 km from horn 1).
* P. Adamson et al., *The NuMI Neutrino Beam*, NIM A 806 (2016) 279 (3.34349° beam angle in the Target Hall, 675 m decay pipe, ND 1.04 km).
* P. Adamson et al. (MINOS), *Precision measurement of the speed of propagation of neutrinos using the MINOS detectors*, PRD 92 (2015) 052005 (survey method, 70 cm baseline precision, Sagnac).
* EPSG Guidance Note 7-2, Oblique Stereographic (method 9809).
