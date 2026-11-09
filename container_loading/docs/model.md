# Model and experiment specification

A candidate i fixes a package ID, lower-corner position and permitted orientation.
Its binary variable x_i selects that placement and v_i is its volume in mm^3.
The conflict set C contains unordered candidate pairs that overlap or use the
same package. A pair satisfying both conditions is counted once. Omitting a
package is allowed, so assignment means at most one placement per package.

The expanded binary objective is

    E(x,y) = -sum_i v_i x_i + lambda sum_(i,j in C) x_i x_j
             + mu (sum_i a_i x_i + sum_k 2^k y_k - B)^2.

Let g be the GCD of the payload capacity and all package weights in grams
(or 1 when all are zero). Then a_i = weight_i/g and B = capacity/g are exact
integers. Slack uses B.bit_length() binary variables y_k. With no weight
price, the main run sets lambda = mu = max_i(v_i) + 1 (1 for an empty pool).
For the geometry-only QUBO, removing a member of a conflicting pair improves
energy because lambda exceeds every individual reward. In conflict-free
states, removing an overweight selected box reduces the integer residual
penalty by more than its reward. These arguments do not assert that any
conflict removal improves the combined objective while holding slack fixed.

The production compound annealer stays conflict-free and minimizes slack
analytically. Its reduced objective is

    E_reduced(x) = -sum_i v_i x_i
                   + mu max(0, sum_i a_i x_i - B)^2.

It therefore does not sample every bit of the expanded QUBO. The independent
`explicit_qubo.py` experiment uses neal on that expanded model. Each main
attempt combines layouts with varied coordinate priorities (cap 160), then
uses four reads of 45 sweeps, compound insertion/removal swaps and final
strict descent. Repair resolves geometry conflicts then solves a weight
knapsack over the retained placements. The shared validator is authoritative.
Optional support filtering is outside the main experiment.

## Test inputs

The main comparison has 30 generated cases in a 1200 x 1000 x 800 mm
container (960 L). Each family has the package counts
10, 15, 20, 10, 15, 20, 10, 15, 20, 10. Dimensions and coordinates use integer
millimetres; weights and capacity use integer grams.

- Geometry (seeds 4100-4109): recursive splits of a 12 x 10 x 8 grid,
  scaled by 100 mm, give a verified full tiling. Each box weighs 1000 g,
  payload equals total weight, and rotation permission has probability 0.75.
- Payload (4200-4209): each dimension is 200-400 mm in 100 mm steps,
  weights are 1000-21000 g in 1000 g steps, all rotations are allowed,
  and payload is 45% of offered weight, rounded down to integer grams.
- Mixed (4300-4309): each dimension is 300-600 mm in 100 mm steps,
  weights are 3000-16000 g in 1000 g steps, rotation probability is 0.55,
  and offered volume is screened to 1.05-1.65 times container volume.
  Payload is 72% of offered weight, rounded down to integer grams.

The earlier 5.90 x 2.35 x 2.39 m datasets remain runnable. The brief suggests
that size but does not require it. The smaller main container exposes tight
geometry and payload tradeoffs with 10-20 packages.

## Comparators and inference

Deterministic First-Fit Decreasing sorts by volume, breaking ties by ID.
The enhanced weight-aware multi-start comparator tries volume, longest edge,
volume per gram and knapsack-guided orders, then seeded shuffled restarts.
The main trial seeds are 301-305 for both enhanced First-Fit and hybrid.
Only validated results completed by 0.15 s count. Actual elapsed time includes
late attempts. The paired bootstrap resamples 30 case means (5000 draws,
seed 9503). Best utilization averages the best of five trials per case.

These cases were reused while developing the algorithms. The intervals
summarize this exploratory benchmark and do not account for adaptive method
selection. New independent cases and settings fixed in advance are required
for confirmatory claims. The overall interval includes zero.
