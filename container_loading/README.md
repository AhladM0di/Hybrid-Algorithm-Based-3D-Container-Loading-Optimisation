# Hybrid Algorithm-Based 3D Container Loading Optimisation

Stage 1 validates a proposed axis-aligned packing for a single container. It runs with Python 3.10+ using the standard library.

## Reproduce from a clean environment

Use Python 3.13 for the recorded dependency versions. Start in the
`container_loading` directory:

```sh
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python benchmark.py --output reproduced
```

The CSV metrics and placements are deterministic with the recorded seeds.
Runtime measurements vary by machine. Use `requirements-hardware.txt` for
the ideal QAOA and physical IBM Quantum commands. The commands below use the
existing `cwq` Conda environment. Inside an activated virtual environment,
run the same Python commands without the `conda run -n cwq` prefix.

## Recorded results and deliverables

- [Local benchmark summary](results/benchmark.csv) and [per-seed results](results/benchmark.json)
- 3D comparisons for [10 packages](results/packing_10.png),
  [15 packages](results/packing_15.png), and [20 packages](results/packing_20.png)
- [Physical QPU results and job IDs](results/hardware.json)
- [Technical report](docs/technical_report.pdf) and [student lab report](docs/container_loading_lab_report.docx)
- [Timed live demo](docs/demo.md) and [PowerPoint slides](docs/demo_slides.pptx)

All three test cases tied on packed volume across the two solvers.
The hybrid solver took longer in each case. This prototype models
geometry and payload only. It does not model support, weight distribution,
load-bearing limits, or securing cargo. The candidate cap bounds the hybrid
search and its results do not certify full-instance optimality.

## Stage 1 feasibility checker

From this directory, run the tests and check the hand-placed example:

```sh
conda run -n cwq python -m unittest discover -s tests -v
conda run -n cwq python check_packing.py data/packages_10.json data/example_packing.json
```

Dimensions are ordered along x, y and z. Dimensions and positions use integer millimetres, and weights and payload limits use integer grams. Positions specify the lower corner of a placement. A package with rotation enabled accepts every distinct axis-aligned permutation of its dimensions. An empty or partial packing is valid if its placements satisfy all constraints.

The checker emits JSON with any violations and, for valid packings, the packed count, packed volume in cubic millimetres, total weight in grams, and utilization as a fraction of internal container volume. Exit status is 0 for a valid packing, 1 for an infeasible packing, and 2 for an input error.

## Stage 2 classical baseline

Run First-Fit Decreasing on the same dataset:

```sh
conda run -n cwq python baseline.py data/packages_10.json
```

The baseline sorts packages by decreasing volume, breaking ties by package ID.
Candidate coordinates come from the origin and the upper faces of placed boxes
on each axis. It tries positions in ascending z, y, x order, with the original
orientation first at each position. It skips any package it cannot place and
continues with the remaining packages.

The command reports placements, shared validator results and metrics, and wall
time in seconds for packing and validation. Run the test command above to check
the known-answer cases and repeatability.

## Stage 3 hybrid solver

```sh
conda run -n cwq python hybrid.py data/packages_10.json --cap 100 --seed 2 --sweeps 200 --reads 16
```

The deterministic candidate pool starts with the baseline placements, then
adds individually feasible alternatives in package ID order, one per package
per round. A candidate can start at the origin, at an upper face of a baseline
box, or flush with the far wall on each axis. The cap must accommodate the
entire baseline.

Each candidate contributes its negative volume to the QUBO when selected.
Each overlapping pair or pair for the same package incurs one conflict
penalty when both are selected. The default penalty is one greater than the
largest volume reward, so removing a candidate from a conflicting pair
strictly improves the energy. The seeded annealer tracks the lowest-energy
state visited across its reads. Payload is enforced during repair, which
tries the selected placements by decreasing volume and keeps each one only
if it passes the shared validator with the placements already kept. The
report includes raw and repaired placements, violations, and separate
annealing time.

### Hardware fixture preparation

`data/hardware_reference.json` records the fixed H0 measurement pattern and
the H1–H3 candidate order, QUBO coefficients, exact optima, and ideal
depth-1 QAOA angles. The circuit scales its Ising coefficients by the
conflict penalty during evolution. The reported exact energies use the
original QUBO units.

Recompute the reference locally with Qiskit from the `cwq` environment:

```sh
conda run -n cwq python hardware_fixtures.py
```

The hardware benchmark uses these recorded angles for backend-specific
transpilation and physical submissions in Stage 4.

## Stage 4 benchmark and 3D comparison

Run from this directory. The benchmark uses Matplotlib from `cwq`.

```sh
conda run -n cwq python benchmark.py
```

The benchmark runs both solvers on the same dataset for each size. The
10-package case is an easy fill, the 15-package case adds varied shapes and
rotation requirements, and the 20-package case uses a 4,000 kg payload limit.
It runs five hybrid seeds (0–4) per case with a candidate cap of 100. It
validates every result and replays each best run. It writes detailed JSON,
a CSV summary, and three labeled 3D comparisons under `results/`. Runtime
measurements cover the entire solver and final validation.

Run the hardware benchmark with the saved IBM Quantum account in `cwq`:

```sh
conda run --no-capture-output -n cwq python qpu_benchmark.py --output reproduced/hardware.json
```

The command uses your saved IBM account and consumes hardware allocation.
It submits H0 first, waits for the physical mapping check, then
runs H1 and H2 before submitting H3. By default it uses 1,024 shots per
circuit and five independent submissions per packing fixture. It saves job
IDs before retrieving results. Rerun against the same output file and shot
count to resume. Use a new output file for a fresh experiment. The report
compares raw samples with the exact references and applies the shared repair
to every method. Ideal rates are probability-weighted and the simulated
annealing rates use one best-visited state per read.
