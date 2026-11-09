# Hybrid Algorithm-Based 3D Container Loading Optimisation

Compare a deterministic First-Fit Decreasing baseline with a hybrid solver
that searches a pool of possible box placements. The revised experiment
separates candidate coverage, search quality and payload repair.

## Environment

From this directory, use Python 3.13 to create the project environment.

```sh
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

An existing environment with these dependencies also works.

## Fixed-work and budget follow-up

```sh
python effort_benchmark.py --fixed-only --output reproduced/fixed_work
python effort_benchmark.py --output reproduced/effort
```

See the [effort findings](docs/effort.md) for the attempt-count tables,
weight-aware baseline, mixed pool check and explicit-QUBO reference.

## Held-out comparison

```sh
python heldout_benchmark.py --output reproduced/heldout
python heldout_benchmark.py --support-search --output reproduced/support_search
python payload_experiment.py --exact-slack-only --output reproduced/exact_slack
```

The held-out protocol fixes the generators, solver settings, and a 150 ms
budget for each method. The comparison uses 30 instances, averages three
trials within each instance, and reports paired results. Full-base support
is a separate benchmark mode. See the [held-out findings](docs/heldout.md).

For an individual run, use `baseline.py DATASET --seconds 0.15 --seed 301`
for multi-start First-Fit or `hybrid.py DATASET --exact-slack` for exact
weight units. Both accept `--require-support`, as does `check_packing.py`. Add
`--support-during-search` to the hybrid to reject moves that would leave
a box unsupported. This option requires `--require-support`.

## Reproduce the revised experiment

Run from this directory with the environment above activated.

```sh
python -m unittest discover -s tests -v
python benchmark.py --output reproduced
```

The benchmark runs the original 10-, 15- and 20-box cases plus two tight
geometry cases. It reports 20 baseline timings and five hybrid seeds per
case. The geometry cases have checked full-container tilings as witnesses,
so the exact full-instance optimum is 100%. The witness coordinates are
used for verification only.

The 3D plots include a horizontal slice through the container. Pale blue
shows free space in that slice. The JSON records each box's support fraction,
measured by the share of its base touching the floor or the tops of boxes
below it. Support is a diagnostic. The feasibility rules cover geometry
and payload, with load-bearing, weight distribution and cargo securing
outside the model.

## Payload and search ablation

```sh
python payload_experiment.py --output reproduced/payload_ablation
```

This experiment crosses five candidate-pool seeds with three search seeds
on the 20-box case and the two tight geometry cases. It compares greedy
repair with exact payload repair, single flips with compound swaps, global
with per-pair penalties for single flips, and two ways to include weight
in the search. See the [ablation findings](docs/payload_ablation.md).

The hybrid CLI now uses compound swaps and exact payload repair by default.
Use `--pool-seed` and `--anneal-seed` for separate seeds. Add
`--weight-multiplier 0.5` for a volume-per-gram price or
`--exact-slack` for the squared payload penalty with exact weights.
The exact unit is the greatest common divisor of package weights and
payload capacity in grams. The slack variant minimizes over the slack
bits for each classical move. The earlier ablation keeps its historical
10 kg configuration for comparison.

## Run either solver

```sh
python check_packing.py data/packages_10.json data/example_packing.json
python baseline.py data/geometry_10.json
python hybrid.py data/geometry_10.json --cap 240 --seed 0 --sweeps 200 --reads 16
```

Dataset dimensions and positions are integer millimetres. Package weights
and payload limits are integer grams. The baseline tries packages in
descending volume order with ties broken by package ID.

The hybrid builds separate layouts using longest-edge, smallest-volume
and seeded shuffled orders. Each layout gets its own set of candidate
corners. The pool combines placements from these layouts up to the cap.
Each selected candidate earns its volume before any optional weight
price. Each overlapping or duplicate pair carries a conflict penalty.
Compound swaps replace a candidate's selected blockers in one move.
The cooling range comes from sampled energy changes. Exact repair first
resolves any geometric conflicts, then maximizes volume within payload
over the remaining selected placements. The output includes pre-repair
violations and removals. The original five-case benchmark keeps the
single-flip and greedy configuration for comparison.

`reference_solver.py` uses SciPy/HiGHS to cross-check the QUBO optimum
and find the best payload-feasible packing on the same seed-0 pool. The
JSON distinguishes proven optima from time-limited bounds. The hybrid
solver accepts a replacement sampler through its `sampler` argument.

## Results and reports

- [Revised findings](docs/revised_experiment.md)
- [Revised benchmark CSV](results/revised/benchmark.csv),
  [per-run JSON](results/revised/benchmark.json) and [parameter sweep](results/revised/tuning.csv)
- [Revised 20-box comparison](results/revised/packing_packages_20.png) and
  [geometry comparison](results/revised/packing_geometry_10.png)
- [Recorded IBM Quantum results](results/hardware.json)

The final submission includes the [technical report](docs/technical_report.pdf),
[student lab report](docs/container_loading_lab_report.docx),
[seven-minute demo guide](docs/demo.md), and [PowerPoint slides](docs/demo_slides.pptx).
The [v1 archive](docs/archive/v1/) holds the materials from the initial experiment.

## Optional IBM hardware experiment

The hardware fixture manifest fixes the candidate order, coefficients and
ideal QAOA angles used in the recorded jobs. These are small tests of the
circuit and measurement decoding workflow.

```sh
python -m pip install -r requirements-hardware.txt
python hardware_fixtures.py
python qpu_benchmark.py --output reproduced/hardware.json
```

The last command uses the saved IBM Quantum account and consumes hardware
allocation. It checks H0 first, then runs H1 and H2 before H3. Rerun with
the same output file and shot count to resume saved jobs.
