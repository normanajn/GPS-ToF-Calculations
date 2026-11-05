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
8. **Sensitivities.**  Numerical partial derivatives of L for each site: height, latitude,
   longitude (per arcsecond), endpoint moved East/North, plus method and model variants.
9. **Error budget.**  Declared uncertainties per site multiplied by the sensitivities;
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

Finding: the target → "ND" chord computed from the MINOS-mast antenna with a 120 m vertical
offset and no horizontal offset is 948 m, against the ~1015 m usually quoted for the NOvA
ND, and the off-axis angle of that endpoint is 13.3 mrad rather than 14.6.  The antenna is
therefore not above the NOvA ND; the missing horizontal antenna → ND vector (2014 note
Table 3, TBD) is of order 65 m along the beam, i.e. about 14 ticks on a target-referenced
delay and about 1 tick on the ND → FD delay (the chord direction is nearly the same at both
ends, so a horizontal shift changes L only through its component along the chord).

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
| legacy notebook files | moved to `docs/reference/` | keep provenance, keep the top level for the package |

## 6. Verification

* 2013 notebook: spherical and WGS84 chords, ToF, ticks, MI shift and total reproduced to
  10⁻⁹ relative.
* 2014 note: the +10.1 m change from its offsets, the −2.08 m MSL-datum term, the
  sensitivities (±27.98/9.62/27.24 m per arcsecond, 0.063 m/m), geometry (7.290°, 335.3°,
  3.613° dip, 544 m arc − chord) and the quantization error budget (1.8 / 4.0 ticks).
* Projection: EPSG 9809 Amersfoort example to 2 mm; FSCS A0 round trip; CFMI control point.
* Target: MINOS FD distance within 10 m of 735 338 m; azimuth 336.098 ± 0.01°; off-axis
  14.6 ± 0.1 mrad; decay-pipe station length.
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
