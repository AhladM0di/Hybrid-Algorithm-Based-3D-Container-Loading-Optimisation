# Hybrid Algorithm-Based 3D Container Loading Optimisation

Compare a deterministic First-Fit Decreasing baseline with a hybrid solver
that searches a pool of possible box placements. The revised experiment
separates candidate coverage, search quality and payload repair.

## Reproduce the revised experiment

Use Python 3.13 in the project environment. Run from this directory.

```sh
conda activate cwq
python -m pip install -r requirements.txt
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
Each selected candidate earns its volume. Each overlapping or duplicate
pair costs a penalty greater than the largest single reward. A seeded
annealer returns its best raw state. Repair checks the shared constraints,
including total payload, and the output records pre-repair violations and
removals. The QUBO itself covers geometry and package uniqueness. Payload
enters the independent integer-programming reference as a separate
constraint, so the benchmark can measure how much a weight-aware search
could improve within the same pool.

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

The [original technical report](docs/technical_report.pdf),
[student lab report](docs/container_loading_lab_report.docx),
[demo guide](docs/demo.md) and [slides](docs/demo_slides.pptx) document the
earlier baseline-seeded experiment. Use the revised findings for conclusions
about candidate coverage and search quality.

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
