# Attempt and Budget Checks

This follow-up reuses the 30 held-out instances and the first recorded
trial seed per case. The stronger First-Fit baseline starts with volume,
longest edge, volume per gram, and a weight-only knapsack subset before
shuffling. It keeps its best validated packing. The hybrid keeps the
held-out settings of cap 160, 45 sweeps, and four reads per attempt.
Each method can stop early when it reaches its volume upper bound.

| Limit | Cases | First-Fit utilization | Hybrid utilization | Mean attempts First-Fit / hybrid |
|---|---:|---:|---:|---:|
| Four attempts | 30 | 67.17% | 69.26% | 3.5 / 3.7 |
| 150 ms | 30 | 69.11% | 68.94% | 258.9 / 3.1 |
| 500 ms | 30 | 69.78% | 70.25% | 863.1 / 11.0 |
| 1.5 s | 30 | 70.32% | 70.69% | 2,603.6 / 32.5 |
| 5 s | 9 | 71.82% | 72.14% | 7,833.9 / 100.2 |

The 5-second check uses the first 10-, 15-, and 20-box case in each family.
Its means describe that subset. A First-Fit attempt constructs one
layout. A hybrid attempt builds a pool and runs four annealing reads.
At 150 ms First-Fit completed roughly 84 times as many attempts. With
the four-attempt cap, First-Fit averaged 7.4 ms and the hybrid averaged
144.9 ms. The cap makes scores repeatable and is a different comparison
from equal latency. The sweep uses one seed on the same instances,
so it does not establish an advantage on a new test set.

## Payload and mixed cases

The weight-only knapsack followed by First-Fit reached 28.02% mean
utilization, at the upper bound on every payload case, in 0.88 ms on
average. The original hybrid’s small gain over randomized First-Fit
on this family can be reproduced by the weight-aware control.

On mixed cases the same control reached 70.26%. HiGHS proved all 30
payload-feasible recorded mixed-pool optima with a four-second limit
per pool. The recorded hybrid averaged 83.41% and the pool optima
averaged 85.62%, a 2.21-point search gap. The 98.59% weight-and-volume
bound ignores geometric feasibility, so the 12.97-point gap from that
bound to the pool optima cannot be attributed entirely to coverage.

## Explicit QUBO and compound search

The production sampler visits only conflict-free states and minimizes
binary slack analytically. Conflict terms are zero along its trajectory.
It therefore searches the reduced objective with an overweight penalty.
The explicit-QUBO test expands the placement and slack terms and checks
the minimum over all slack assignments against the reduced expression.

An independent `neal` run sampled the expanded binary model on the first
trial pool of three payload and three mixed cases. At 500 sweeps and 32
reads per pool it produced zero valid raw layouts in 192 reads. After
repair its best result fell below the recorded compound result on every
tested pool. This is a small sampler check with a different search
budget, rather than a matched benchmark.

## Corner priority and support

For three geometry probes, varying the corner priority raised the
20-box pool optimum from 91.25% to 100%. The other two pools already
reached 100%. Doubling the cap after varying the corner priority
gave no further gain on those probes. This was a diagnostic on the
existing cases.

| Full support during search | First-Fit | Hybrid | Mean attempts First-Fit / hybrid |
|---|---:|---:|---:|
| Geometry | 98.14% | 91.33% | 35.4 / 2.3 |
| Payload | 27.71% | 27.99% | 648.1 / 2.7 |
| Mixed | 78.03% | 79.58% | 91.5 / 2.5 |

Post-repair support cleanup removes unsupported boxes and leaves
freed capacity unused. The support-aware search comparison applies the
same full-contact rule to both methods.

## Reproduce

Run these from the project directory using the [environment setup](../README.md).

```sh
python effort_benchmark.py --fixed-only --output reproduced/fixed_work
python effort_benchmark.py --output reproduced/effort
python geometry_pool_check.py --family mixed --seconds 4 --output reproduced/mixed_pool_check.csv
python coverage_sensitivity.py --output reproduced/coverage.csv
python -m pip install -r requirements-qubo.txt
python explicit_qubo.py --output reproduced/explicit_qubo.csv
```

[Attempt and timing summary](../results/effort/summary.csv) ·
[Per-run scores](../results/effort/runs.csv) ·
[Weight-only control](../results/effort/weight_only_control.csv) ·
[Mixed pool diagnostics](../results/heldout/mixed_pool_check.csv) ·
[Coverage probes](../results/effort/coverage.csv) ·
[Explicit sampler results](../results/effort/explicit_qubo.csv)
