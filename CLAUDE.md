# GPS-ToF-Calculations

## Project Overview
Python package and CLI (`gps-tof`) that computes straight-line times of flight between
surveyed sites and reports every correction applied (Earth model, height datum, antenna
to endpoint offsets), timing shifts, trigger window, geometry, Sagnac/cable/neutrino-mass
effects, sensitivities and an error budget.  Built to replace and generalise the NOvA
FNAL to Ash River Mathematica notebooks (docs/reference), and now includes the NuMI target
derived from the 1998 TDR beam sheet through the Fermilab site-coordinate projection.

## Setup and Running
```
./bootstrap.sh                                  # venv + editable install + pytest
source venv/bin/activate
gps-tof -c config/nova.yaml -f md -o reports/nova.md
gps-tof -c config/nova.yaml -f all -o reports/nova    # md + txt + json
gps-tof-fscs to-geodetic 100327.838 97780.188 626.743
gps-tof-nmea screenlog.0 --yaml
```

## Architecture
- `src/gps_tof/angles.py` angle parsing (DMS, decimal minutes, NMEA), `geodesy.py` ellipsoids,
  ECEF, ENU, azimuth/elevation; `projection.py` EPSG 9809 oblique stereographic;
  `fermilab_site.py` FSCS/DUSAF feet <-> geodetic (Beams-doc-1148); `nmea.py` checksums and GGA.
- `model.py` dataclasses `Site`, `Baseline`, `OpeningAngle`, `BeamAxis`, `TimingShift`, `Settings`, `Problem` (+ `from_dict`;
  sites may be given as `axis_position: {along_m, right_m, up_m}` in the beam-axis frame and are resolved there).
- `calc.py` engine: `site_point` (endpoint for a `Stage` of corrections), `build_ledger`
  (progressive chain, asserts closure with the direct final chord), `geometry`, `effects`,
  `sensitivities`, `error_budget`, `compute_baseline`, `compute_opening_angle` (angle at a vertex
  between two chords, with components and off-axis angles), `axis_frame` / `point_vs_axis` /
  `direction_vs_axis` (global beam axis: every site, baseline and opening angle is reported
  against it), `compute_all` (plain dicts).
- `report.py` renders dicts to text/Markdown/JSON.  `config.py` merges YAML < .env < env < CLI.
  `cli.py` has `main`, `main_nmea`, `main_fscs`.
- Single-threaded, stdlib + PyYAML.  All distances in metres, angles in radians internally,
  degrees at the model boundary; longitudes east-positive; `offset_enu_m` is surveyed point
  to endpoint (down is negative U).

## Configuration Schema
See `man/gps-tof.5` and `config/nova.yaml`.  Minimal:
```yaml
clock_hz: 64.0e+6            # exponent needs a sign in YAML 1.1
earth: {model: wgs84}
sites:
  - {name: ND, id: nd, axis_position: {along_m: 1015, right_m: -11.57, up_m: 5.12}}   # in the beam-axis frame
  - {name: Target, id: target, fscs_xyz_ft: [100327.838, 97780.188, 626.743]}
beam_axis: {from: target, to: minos-fd}      # target -> MINOS FD is the NuMI beam axis
baselines: [{from: target, to: nd}]
opening_angles: [{vertex: target, a: nd, b: fd2, axis_to: decay-end}]
timing_shifts: [{name: MI shift, turns: 141, buckets_per_turn: 588, rf_hz: 53.1034e+6}]
```

## Testing
`pytest -q` (55 tests): notebook/2014-note reproduction to 1e-9, EPSG 9809 worked example,
Beams-doc-1148 control points, NuMI target cross-checks (MINOS FD distance, beam azimuth,
off-axis angle), config precedence, CLI smoke tests.  `ctest --test-dir build` after `cmake -S . -B build`.
