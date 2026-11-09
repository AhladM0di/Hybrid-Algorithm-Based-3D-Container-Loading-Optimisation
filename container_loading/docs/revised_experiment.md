# Revised Container Loading Experiment

The original benchmark started the hybrid pool with the baseline packing
and used its box faces to generate the remaining positions. That design
made it hard to tell whether the tie came from the pool or from the search.
The revised pool uses separate layouts from longest-edge, smallest-volume
and seeded shuffled orders. Each layout starts at the origin and creates
its own candidate corners. The main comparison uses a cap of 240.

## Packing results

| Case | Baseline utilization | Hybrid mean ± SD | Hybrid range | Full-instance reference |
|---|---:|---:|---:|---:|
| Original 10 boxes | 13.62% | 13.62% ± 0.00 pp | 13.62–13.62% | 13.62%, all boxes fit |
| Original 15 boxes | 57.15% | 54.68% ± 3.40 pp | 50.53–57.15% | 57.15%, all boxes fit |
| Original 20 boxes | 57.80% | 48.33% ± 4.19 pp | 42.47–52.48% | 61.86% weight-only upper bound |
| Tight geometry, 10 boxes | 90.00% | 96.33% ± 2.74 pp | 93.33–98.33% | 100%, verified tiling |
| Tight geometry, 15 boxes | 90.00% | 92.00% ± 4.47 pp | 90.00–100.00% | 100%, verified tiling |

The two tight cases come from splitting a container into boxes. The
original split gives a valid 100% packing, which reaches the container
volume upper bound. These cases were selected because the baseline left
at least 10% empty. The hybrid results were not used to select them.
The cases test whether the search can improve on this baseline under
tight geometry. They do not estimate how often it will win on unseen data.

The CSV records 20 baseline timings and five hybrid runs per case,
with means, standard deviations and ranges. The baseline took about
0.9–15.4 ms on average across the five cases. The hybrid took about
1.18–1.84 seconds. All 25 hybrid results passed the shared validator
after repair.

## Candidate coverage and search quality

An independent SciPy/HiGHS integer solver used the same seed-0 pool as
the annealer. The conflict penalty exceeds each single volume reward, so
an optimum of the QUBO cannot include a conflicting pair. The reference
can therefore optimize the same objective using conflict constraints.
It can also add a payload constraint to show the best legal volume in
the same pool.

- In both tight geometry cases, the reference proved the seed-0 pool
  could reach 100%. The seed-0 annealer reached 93.33% and 90.00%.
  The gap on that seed came from the search. A different annealing seed
  and pool reached 100% on the 15-box case.
- In the 20-box case, the weight-only knapsack bound is 61.86% when
  geometry is ignored. HiGHS proved a 61.12% payload-feasible packing in
  the seed-0 pool, above the baseline's 57.80%. The geometry-only
  reference stopped at its time limit with a 67.60% incumbent and a
  69.57% upper bound. The raw seed-0 annealer packed 63.63% by volume
  and exceeded the payload limit. Greedy repair cut it to 45.55%.
- Across all five 20-box seeds, there were five raw payload violations
  and 47 removals during repair. Payload is still outside the annealing
  objective. The results show the cost of deferring that constraint.

## Parameter sweep and support

The seed-0 sweep varied one setting at a time on the 20-box and tight
10-box cases. It tested caps of 120, 240 and 320, penalty factors of
1, 1.5 and 2, and doubled sweeps or reads. On the tight 10-box case,
increasing the cap from 120 to 320 moved utilization from 90.00% to
96.67%. Doubling sweeps on the 20-box case improved the repaired
result from 45.55% to 54.64%. It still fell short of the baseline.
The sweep is a sensitivity check on two cases and one seed.

The JSON records the fraction of each box base in contact with the floor
or a box directly below it. The minimum reached zero in some hybrid
runs. The plots show the free area in a mid-height slice in pale blue.
The support measurements describe the geometry and do not certify
load-bearing or physical stability.

## Reproduction and scope

See the [README](../README.md) for commands and the
[benchmark CSV](../results/revised/benchmark.csv),
[per-run JSON](../results/revised/benchmark.json), and
[tuning CSV](../results/revised/tuning.csv) for the measurements.
The [recorded IBM runs](../results/hardware.json) still refer to their
frozen small fixtures and are separate from this solver comparison.
