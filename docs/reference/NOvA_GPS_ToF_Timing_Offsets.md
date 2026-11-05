# NOvA Beam Timing Offsets from GPS Positions: Time-of-Flight Calculation

Source: `FNAL_to_AshRiver_Distance.nb` (Mathematica 9, last saved by Mathematica 11.1).
Cell timestamps show the work was done in stages: Parts 1-2 in March-April 2013, the
64 MHz conversion and Main Injector shift in September 2013, and the unfinished
detector-angle section in May 2016. The last evaluation was 2017-03-22.

This document writes out the calculations in the notebook, checks each result with an
independent Python implementation (Appendix A), and lists the assumptions, approximations
and open issues that affect how far the offsets can be trusted.

---

## 1. Purpose

The NOvA Far Detector (FD) at Ash River, MN, and the NuMI beamline at Fermilab each keep
time with their own GPS-disciplined clocks. Beam spills are timestamped at Fermilab from
the Main Injector Beam Sync (MIBS) `$74` event. To open the FD readout window around
neutrino arrival, the DAQ needs the expected delay between the FNAL timestamp and
arrival at the FD, in NOvA 64 MHz clock ticks. The notebook computes two parts of that
delay:

1. **Neutrino time of flight (ToF)** along the straight chord between the NOvA Near
   Detector (ND) and the Ash River GPS antenna. The ND position is the MINOS-surface-
   building GPS antenna position moved down by 300 m.
2. **A fixed shift in the Main Injector timing** (141 MI revolutions) introduced during
   the 2012 accelerator shutdown.

The sum is the beam offset that the NOvA timing system has to apply.

---

## 2. Inputs

| Quantity | Value in notebook | Decimal degrees | Height h used (m) | Notes |
|---|---|---|---|---|
| FNAL latitude | 41° 50′ 23″ N | 41.839722° | | GPS antenna on mast above the MINOS Surface Building ("MINOS based TDUs") |
| FNAL longitude | 88° 16′ 13″ W | 88.270278° | | entered as **positive** |
| FNAL height | `228 - 300` | | **−72** | 228 m antenna altitude (sea level) minus the 300 m antenna → NOvA ND offset (see §11.2) |
| Ash River antenna 1 lat | 48° 22.715780′ N | 48.37859633° | | degrees + decimal minutes |
| Ash River antenna 1 lon | 92° 49.876930′ W | 92.83128217° | | entered as positive |
| Ash River antenna 1 height | | | 348.638 (348 in Part 1) | used for final result |
| Ash River antenna 2 lat | 48° 22.716416′ N | 48.37860693° | | |
| Ash River antenna 2 lon | 92° 49.877639′ W | 92.83129398° | | |
| Ash River antenna 2 height | | | 350.346 | only used for antenna-separation check |

Physical constants and time bases:

| Symbol | Value | Use |
|---|---|---|
| c | 299 792 458 m/s (exact, Mathematica `Quantity["SpeedOfLight"]`) | ToF |
| a (WGS84) | 6 378 137 m | ellipsoid semi-major axis; also sphere radius in Part 1 |
| b (WGS84) | 6 356 752.31424518 m | semi-minor axis (matches a(1−f) to 10⁻⁹ m) |
| f (WGS84) | 1/298.257223563 | flattening (defined but only b is used) |
| NOvA clock | 64 MHz → 15.625 ns/tick (4.684 m of light path per tick) | final units |
| Legacy Global Trigger unit | 500 ns | historical units |
| MI RF | 53.1034 MHz, h = 588 buckets per revolution | MI shift |

---

## 3. Angle conversion

Sexagesimal to radians:

$$
\mathrm{LC}(d,m,s) = \frac{\pi}{180}\left(d + \frac{m + s/60}{60}\right)
$$

The Ash River coordinates come in degrees plus decimal minutes (`LC[48, 22.715780, 0]`).
Six decimal places of arc-minute resolve 1.85 mm north-south, so the Ash River
positions are far more precise than the FNAL position, which is given to the nearest
whole arc-second (about 31 m N-S and 23 m E-W).

---

## 4. Model 1: spherical Earth (sanity check)

Earth is taken as a sphere of radius R = a = 6 378 137 m. A point at (φ, λ, h) maps to

$$
\vec r_{\rm sph} = (R+h)\,\big(\cos\varphi\sin\lambda,\;\; \sin\varphi,\;\; \cos\varphi\cos\lambda\big)
$$

This axis convention is non-standard: ŷ is the polar axis and ẑ points at (0°, 0°).
It is still an orthonormal frame, so distances are not affected.

Results:

| Quantity | Notebook | Python check |
|---|---|---|
| FNAL (m) | (4 749 580.763, 4 254 482.749, 143 430.323) | identical |
| Ash River (h = 348 m) | (4 231 453.354, 4 768 236.584, −209 268.459) | identical |
| Chord length L_sph | **810 429.1726 m** | 810 429.1726 m |
| ToF L_sph / c | **2703.3007 µs** | 2703.3007 µs |
| Separation of the two Ash River antennas | 2.2524 m | 2.2524 m |

A sphere of equatorial radius puts both sites about 10 km farther from Earth's centre
than they really are (geocentric radii at 42° N and 48° N are 6 368.6 km and 6 366.6 km).
Because chord length scales roughly linearly with radius, Model 1 overestimates the
baseline by 823 m (2.745 µs, ≈176 ticks). That is why the notebook calls it only a
sanity check.

---

## 5. Model 2: WGS84 ellipsoid (the result actually used)

### 5.1 Geodetic → ECEF transformation

First eccentricity squared and second eccentricity:

$$
e^2 = \frac{a^2-b^2}{a^2} = 6.694380\times10^{-3},\qquad
e'^2 = \frac{a^2-b^2}{b^2}\;(\text{defined, unused})
$$

Prime-vertical radius of curvature (`RCurv`):

$$
N(\varphi) = \frac{a}{\sqrt{1-e^2\sin^2\varphi}}
$$

ECEF coordinates (`Xpos`, `Ypos`, `Zpos`), which is the standard GPS/WGS84 transformation:

$$
\begin{aligned}
X &= (N+h)\cos\varphi\cos\lambda\\
Y &= (N+h)\cos\varphi\sin\lambda\\
Z &= \left(\tfrac{b^2}{a^2}N + h\right)\sin\varphi \;=\; \big(N(1-e^2)+h\big)\sin\varphi
\end{aligned}
$$

Here h is the **ellipsoidal** height (height above the WGS84 ellipsoid, which is what a
GPS receiver reports natively). The notebook describes this step as going from the
"Local Tangential Plane" to ECEF. Strictly, the input is geodetic (φ, λ, h), not an ENU
local tangent plane.

### 5.2 Positions and baseline

| Quantity | Notebook | Python check |
|---|---|---|
| Ash River ant. 1, ECEF (m) | (−209 660.9996, 4 239 390.6130, 4 745 202.2088) | identical |
| FNAL, ECEF (m) | (143 644.4212, 4 756 670.4609, 4 232 309.4554) | identical |
| **Chord L** | **809 606.1622 m** | 809 606.1622 m |
| **ToF t = L/c** | **2700.555470 µs** | 2700.555470 µs |
| Antenna 1-2 separation | (not recomputed) | 2.2523 m |

Both longitudes were entered as positive numbers. The sites are therefore placed at 88° E
and 92° E, the mirror image of their real positions in the plane of the prime meridian.
A reflection is an isometry, so L is unchanged (verified: recomputing with physical
west-negative longitudes gives exactly 809 606.1622 m). The ECEF coordinates in the
notebook should **not** be reused as real ECEF positions, and any quantity that depends on
handedness, such as the Sagnac term in §8, has to be computed with the correct signs.

---

## 6. Geometry of the chord

Neutrinos travel in a straight line through the Earth, so the relevant path length is
the Euclidean chord |r_FNAL − r_Ash|, not a distance along the surface. Derived
geometry (Python, WGS84 positions):

| Quantity | Value |
|---|---|
| Geocentric central angle | 7.290° |
| Surface arc at mean radius | 810 150 m |
| Arc − chord | 544 m (1.814 µs, 116 ticks) |
| Maximum depth of chord below surface (sagitta) | ≈12.9 km |
| Beam dip below local horizontal at FNAL | 3.613° (≈63.1 mrad) |
| Beam rise above local horizontal at Ash River | 3.671° |
| Baseline azimuth at FNAL | 335.3° (N 24.7° W) |

A great-circle or geodesic distance, such as the output of a map tool, would be wrong by
more than 100 ticks.

---

## 7. Conversion to timing units

### 7.1 Legacy 500 ns Global Trigger units

$$
n_{500} = \frac{t}{500\ \text{ns}} = 5401.1109
$$

The notebook displays this as `5401.11 ns`. The unit label is a display artifact: it
divides a `Quantity` in ns by the bare number 500, so the ns label stays on. The
physically correct value is 5401.11 **ticks**, i.e. 2.700555 ms.

### 7.2 NOvA 64 MHz ticks

$$
n_{\rm ToF} = t \times 64\times10^{6}\ \text{s}^{-1} = \mathbf{172\,835.550}\ \text{ticks}
$$

(`NovaFlightTime`). Rounded to an integer, this is 172 836 ticks, which is 7.0 ns later
than the exact value. Truncating gives 172 835, which is 8.6 ns earlier. The notebook
does not say which convention the DAQ uses.

---

## 8. Main Injector timing shift (2012 shutdown)

After the 2012 shutdown, beam relative to MIBS `$74` moved by 141 MI revolutions:

$$
T_{\rm rev} = \frac{h}{f_{\rm RF}} = \frac{588}{53.1034\ \text{MHz}} = 11.072737\ \mu\text{s}
$$

$$
\Delta t_{\rm MI} = 141\,T_{\rm rev} = 1561.255965\ \mu\text{s}
\;\Rightarrow\; n_{\rm MI} = 99\,920.382\ \text{ticks}
$$

(`TimingShift`, `MiShiftNovaTime`). One MI revolution is 708.655 NOvA ticks, which is not
an integer: the 53.1034 MHz RF and the 64 MHz NOvA clock are not commensurate. The MI RF
frequency also sweeps during acceleration, and 53.1034 MHz is the flat-top value. If the
141-turn shift is referenced to an RF-synchronous event, the fractional-tick error
accumulated over 141 turns is set by the precision of f_RF: a 1 kHz error in f_RF shifts
Δt_MI by 29 ns (≈1.9 ticks).

---

## 9. Combined beam offset

$$
n_{\rm total} = n_{\rm ToF} + n_{\rm MI} = 172\,835.550 + 99\,920.382 = \mathbf{272\,755.932\ ticks}
$$

$$
t_{\rm total} = 4261.8114\ \mu\text{s}
$$

Rounded to an integer, this is **272 756 ticks**, which is 1.1 ns from the exact value.

### Summary of results

| Item | Length (m) | Time (µs) | 64 MHz ticks |
|---|---|---|---|
| Spherical chord (check only) | 810 429.173 | 2703.3007 | 173 011.25 |
| **WGS84 chord (ToF)** | **809 606.162** | **2700.5555** | **172 835.550** |
| **MI 141-turn shift** | | **1561.2560** | **99 920.382** |
| **Total offset** | | **4261.8114** | **272 755.932** |

---

## 10. Incomplete sections of the notebook

* **Part 3, "Including Target and Offaxis detector positions (Work in progress)."** It
  introduces a target position T = (T_x, T_y, T_z) in ECEF and detector positions P, P′.
  The text stops mid-sentence ("then the angle between the ..."), and the notebook
  contains no computation for it. The intent was to replace the GPS-reference endpoints
  with target → detector paths and to compute the off-axis angles.
* **"Detector Angle and Transformation to ECF coordinates" (2016).** It contains one
  unfinished sentence ("Take the zero angle of the detector as being the line between
  the ...").

Neither section contributes to the numbers above.

---

## 11. Assumptions, caveats and review findings

These are ordered by likely impact on the timing offset.

### 11.1 Endpoints are ND and FD antenna, not beam source and FD

At the FNAL end, the chord starts at the NOvA Near Detector. The notebook gets that
point by taking the GPS antenna on the mast above the MINOS Surface Building and
moving it 300 m straight down along the local vertical. At the Ash River end, it stops
at GPS antenna 1. The two ends are treated differently:

* At FNAL, the height is corrected to the ND, but the horizontal offset between the
  mast antenna and the ND is ignored.
* At Ash River, the endpoint is the antenna, not the FD.

For an ND → FD arrival-time difference, the ND endpoint is the right choice. For
predicting FD arrival from the MIBS `$74` timestamp, the path that matters starts at
the target.
Neither end is the NuMI target or decay region. The real physics ToF differs by the
along-baseline projection of three displacements: the offset of the FNAL endpoint from
the target, the offset of the antenna from the FD front face, and the length of the
decay region (neutrinos come from π/K decays distributed over the
~675 m decay pipe, and parents travel at β ≈ 1). Part 3 was meant to handle this. For a
DAQ trigger window, a constant offset of a few hundred ns is normally absorbed into
the window width and delay calibration.

### 11.2 Antenna → NOvA Near Detector offset (−300 m)

h_FNAL = 228 − 300 = −72 m.

* **228 m** is the sea-level altitude of the GPS antenna, which is mounted on a mast
  above the MINOS Surface Building.
* **300 m** is the vertical offset from that antenna down to the NOvA Near Detector.
  It moves the FNAL endpoint from the antenna to the ND.

The beam dips 3.61° at FNAL, so ∂L/∂h_FNAL = sin(3.61°) = 0.0630. The 300 m correction
therefore shortens L by 18.96 m, which is **−63 ns ≈ −4.0 ticks** compared with using
the antenna position. The notebook does not say what this term is, so it should get a
comment there, because it is the largest single geometric correction after the choice
of Earth model.

Sensitivity is 0.063 m of L per metre of offset (0.21 ns/m). A ±10 m uncertainty in the
offset is ±0.63 m in L, i.e. ±2.1 ns (0.13 tick).

**Cross-check against the published ND depth.** The NOvA ND sits in the MINOS
underground hall, which is usually quoted as about 100 m below the surface. Adding a
mast height of order 10-20 m gives an antenna → ND offset of about 110-125 m. The
notebook uses 300 m. If the offset is in fact about 110-125 m, the notebook's chord is
11-12 m too short, which is **37-40 ns (2.4-2.6 ticks)**. The surveyed antenna and ND
elevations will settle this. Note that 228 − 300 = −72 m puts the ND 72 m below sea
level, while the Fermilab surface is at about 225 m above sea level.

### 11.3 Height datum (sea level vs ellipsoid)

The WGS84 transformation needs ellipsoidal height (h). The FNAL antenna altitude is a
sea-level (orthometric, H) value. Receivers usually report MSL altitude, e.g. in NMEA
GGA, and give the geoid separation N_g separately, with h = H + N_g. The geoid
undulation is about −33 m at Fermilab and about −28 m at Ash River.

The chord dips below the local horizontal at both ends, so ∂L/∂h is positive at both
(0.063 and 0.064). Lowering either endpoint shortens L, and the two datum errors
therefore **add rather than cancel** (correcting the earlier version of this document):

| Correction applied | ΔL | Δt | ticks |
|---|---|---|---|
| FNAL only, N_g = −33 m | −2.08 m | −6.9 ns | −0.44 |
| Ash River only, N_g = −28 m | −1.79 m | −6.0 ns | −0.38 |
| Both | −3.87 m | −12.9 ns | **−0.83** |

The Ash River heights (348.638 m and 350.346 m) are also receiver outputs. Whether they
are MSL or ellipsoidal is not recorded. The worst case is both ends MSL, a 0.83 tick
error. If the Ash River heights are already ellipsoidal, the error is 0.44 tick from
the FNAL end alone.

### 11.4 FNAL coordinate precision

FNAL lat/lon are quoted to 1″. Sensitivities of L:

| Parameter | ∂L per 1″ |
|---|---|
| FNAL latitude | −27.98 m |
| FNAL longitude | −9.62 m |
| Ash River latitude | +27.24 m |
| Ash River longitude | +9.62 m |

Rounding to ±0.5″ gives up to ±14.0 m (lat) and ±4.8 m (lon) in L. Added linearly
that is **±18.8 m = ±63 ns (≈ ±4.0 ticks)** worst case. For uniform rounding errors
added in quadrature it is 8.5 m, i.e. **28 ns (1.8 ticks) RMS**. This is the dominant *precision* limit of the calculation.

### 11.5 Antenna choice at Ash River

Antenna 1 was used. Using antenna 2 lengthens L by 1.558 m (**+5.2 ns**). The 2.25 m
antenna separation is computed only as a consistency check of the two survey points.
Part 1 uses h = 348 m where Part 2 uses 348.638 m, which changes L by only 4 cm.

### 11.6 Neglected physical effects

| Effect | Size | Comment |
|---|---|---|
| Sagnac (Earth rotation during flight, ECEF frame) | **−1.30 ns** | ω(x_s y_r − y_s x_r)/c², computed with physical (west-negative) longitudes. The beam travels westward and the FD moves toward it, so the flight is shorter. |
| Neutrino velocity (m_ν ~ 0.1 eV, E ~ 2 GeV) | ~10⁻²⁴ s | δt/t ≈ m²/2E². Negligible. |
| Gravitational/Shapiro delay along chord | ≪ 1 ns | Handled at the ns level by GPS time itself. |
| GPS time-transfer accuracy between sites | ~10-50 ns | Depends on receivers and common-view setup. Outside the notebook. |
| Antenna cable delays, receiver and TDU latencies | 100s of ns typical | Calibrated separately. Not part of a geometric ToF. |

### 11.7 Longitude sign convention

As noted in §5.2, both longitudes are positive (east). This has no effect on L. It does
make the printed ECEF vectors mirror-image, and it would give the wrong sign for any
rotation-dependent correction.

### 11.8 Unit-label artifact

The 500 ns tick count prints as "5401.11 ns" (§7.1). It is a dimensionless tick count.

### Error budget (64 MHz ticks)

| Source | Size | Type |
|---|---|---|
| FNAL lat/lon quantization (1″) | ±1.8 (RMS), ±4.0 (max) | precision |
| Antenna → ND offset: 300 m vs ~110-125 m from published ND depth | 2.4-2.6 | to be confirmed |
| Antenna → ND offset, per 10 m of uncertainty | 0.13 | systematic |
| Sea-level vs ellipsoidal heights (both ends) | 0.44-0.83 | systematic |
| Antenna 1 vs 2 | 0.33 | choice |
| Integer rounding of the final value | ≤ 0.5 | convention |
| Sagnac | 0.08 | neglected |
| MI f_RF precision (per kHz) | 1.9 | systematic |

---

## 12. Recommended follow-ups

1. Add a comment in the notebook that the −300 m is the mast-antenna → NOvA ND offset.
   Confirm the value against the surveyed antenna and ND elevations (§11.2 compares it
   with the ~100 m published ND depth). Also add the horizontal antenna → ND offset.
2. Convert both antenna altitudes from sea level to WGS84 ellipsoidal height using each
   receiver's reported geoid separation (§11.3).
3. Replace the 1″ FNAL coordinate with a surveyed position (mm to cm precision), as was
   done for Ash River.
4. Complete Part 3: compute target → FD (and target → Near Detector) chords and the
   off-axis angles, and state the decay-point convention.
5. Use west-negative longitudes so the intermediate ECEF vectors are real positions.
6. State the rounding convention used when loading the offset into the timing system.

---

## Appendix A. Independent reproduction (Python, stdlib only)

The script below reproduces every numeric output of the notebook. It agrees to the last
printed digit (differences ≤ 10⁻⁹ relative, from floating-point order of operations).

```python
import math
C = 299792458.0
def LC(d, m, s): return math.pi/180*(d + (m + s/60)/60)

FNAL = (LC(41,50,23), LC(88,16,13), 228-300)
ASH1 = (LC(48,22.715780,0), LC(92,49.876930,0), 348.638)

a = 6378137.0; b = 6356752.31424518
e2 = (a*a - b*b)/(a*a)
def N(lat): return a/math.sqrt(1 - e2*math.sin(lat)**2)
def ecef(lat, lon, h):
    n = N(lat)
    return ((n+h)*math.cos(lat)*math.cos(lon),
            (n+h)*math.cos(lat)*math.sin(lon),
            (b*b/(a*a)*n + h)*math.sin(lat))

L   = math.dist(ecef(*FNAL), ecef(*ASH1))
t   = L/C
tMI = 141*588/53.1034e6
print(f"L = {L:.4f} m  ToF = {t*1e6:.6f} us  = {t*64e6:.3f} ticks")
print(f"MI = {tMI*1e6:.6f} us = {tMI*64e6:.3f} ticks")
print(f"Total = {(t+tMI)*1e6:.4f} us = {(t+tMI)*64e6:.3f} ticks")
```

Run:

```
$ python3 nova_tof_check.py
L = 809606.1622 m  ToF = 2700.555470 us  = 172835.550 ticks
MI = 1561.255965 us = 99920.382 ticks
Total = 4261.8114 us = 272755.932 ticks
```

(`math.dist` needs Python ≥ 3.8.)
