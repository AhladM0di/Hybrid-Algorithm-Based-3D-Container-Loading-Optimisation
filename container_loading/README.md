# Hybrid Algorithm-Based 3D Container Loading Optimisation

Stage 1 validates a proposed axis-aligned packing for a single container. It runs with Python 3.10+ using the standard library.

From this directory, run the tests and check the hand-placed example:

```sh
conda run -n cwq python -m unittest discover -s tests -v
conda run -n cwq python check_packing.py data/packages_10.json data/example_packing.json
```

Dimensions are ordered along x, y and z. Dimensions and positions use integer millimetres, and weights and payload limits use integer grams. Positions specify the lower corner of a placement. A package with rotation enabled accepts every distinct axis-aligned permutation of its dimensions. An empty or partial packing is valid if its placements satisfy all constraints.

The checker emits JSON with any violations and, for valid packings, the packed count, packed volume in cubic millimetres, total weight in grams, and utilization as a fraction of internal container volume. Exit status is 0 for a valid packing, 1 for an infeasible packing, and 2 for an input error.
