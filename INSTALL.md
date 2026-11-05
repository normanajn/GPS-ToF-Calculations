# Installing, bootstrapping, building and running gps-tof

## Requirements

* Python 3.9 or newer (tested with 3.12; the code avoids post-3.9 syntax).
* PyYAML (installed by the bootstrap).  pytest for the test suite.
* Optional: CMake ≥ 3.16 for the `ctest` and man-page install targets; `man` to read the pages.

## Linux / macOS

```
git clone git@github.com:normanajn/GPS-ToF-Calculations.git
cd GPS-ToF-Calculations
./bootstrap.sh                 # creates venv/, installs the package in editable mode, runs pytest
source venv/bin/activate
gps-tof -c config/nova.yaml    # text report on stdout
gps-tof -c config/nova.yaml -f all -o reports/nova   # reports/nova.md, .txt, .json
```

`./start-gps-tof.sh [args]` runs `gps-tof` from the venv, creating and updating it first if
needed, e.g. `./start-gps-tof.sh -c config/nova.yaml -f md -o reports/nova.md`.

Man pages: `man -l man/gps-tof.1` (or install them with CMake, below).

## Windows 11 (PowerShell)

```
git clone git@github.com:normanajn/GPS-ToF-Calculations.git
cd GPS-ToF-Calculations
.\bootstrap.ps1
.\venv\Scripts\Activate.ps1
gps-tof -c config\nova.yaml
```

## CMake targets (all platforms)

```
cmake -S . -B build
cmake --build build          # nothing to compile; creates the venv through the bootstrap target
ctest --test-dir build       # runs pytest inside the venv
cmake --install build        # installs man pages under <prefix>/share/man
```

## Configuration

* YAML file (`config/nova.yaml` is the worked example; `config/gps-tof.yaml` is picked up by default if present).
* `.env` in the working directory or `config/.env`: `GPS_TOF_CLOCK_HZ=64.0e6`, `GPS_TOF_FORMAT=md`, ...
* Environment variables with the same names override `.env`; command-line options override everything.
* `gps-tof --dump-config` prints the merged configuration actually used.

## Running the tests

```
source venv/bin/activate
pytest -q
```
