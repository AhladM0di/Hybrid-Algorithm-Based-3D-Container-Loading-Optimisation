# Hybrid Algorithm-Based 3D Container Loading Optimisation

Python prototype for packing rectangular boxes into one container using a
classical First-Fit baseline and a hybrid candidate-placement search.
The validator enforces permitted rotations, container boundaries,
non-overlap, unique package assignments and payload capacity.

## Project

- [Setup and reproduction commands](container_loading/README.md)
- [Model, QUBO formulation and input generators](container_loading/docs/model.md)
- [Datasets and experiment protocols](container_loading/data/)
- [Source code and tests](container_loading/)
- [Main comparison](container_loading/results/main_v4/summary.csv),
  [paired intervals](container_loading/results/main_v4/intervals.csv) and
  [deterministic reference](container_loading/results/main_v4/deterministic_reference.csv)
- [3D packing example](container_loading/results/revised/packing_packages_20.png)

The main comparison uses five trials per case against weight-aware
multi-start First-Fit. The hybrid difference is +0.48 percentage points
(paired 95% interval -0.32 to +1.26). These are reused development cases,
so this exploratory result does not establish an overall improvement.
The 150 ms cutoff controls scoring; actual elapsed time includes late attempts.
