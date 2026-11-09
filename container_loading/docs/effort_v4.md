# Three-Seed Effort Follow-up

The same 30 cases were rerun with all three frozen trial seeds. This
follow-up enables varied corner priorities in the hybrid, keeps the
160-candidate cap, 45 sweeps and four reads, and uses weight-aware
First-Fit. It reuses the earlier held-out cases, so it is evidence on
these cases rather than a fresh test set.

## Paired utilization differences

Values are hybrid minus First-Fit in percentage points. We averaged
the three trial scores within each instance, then used a paired
bootstrap over instances to obtain the 95% intervals. The five-second
row covers the first three cases in each family.

| Limit | All | Geometry | Payload | Mixed |
| --- | --- | --- | --- | --- |
| 4 attempts | +2.66 [+0.95 to +4.51] | -0.62 [-2.26 to +1.09] | +0.00 [+0.00 to +0.00] | +8.60 [+6.33 to +10.71] |
| 150 ms | +0.22 [-0.68 to +1.07] | -0.95 [-3.04 to +1.17] | +0.00 [+0.00 to +0.00] | +1.62 [+0.42 to +2.89] |
| 500 ms | +0.80 [-0.02 to +1.59] | -0.26 [-1.89 to +1.44] | +0.00 [+0.00 to +0.00] | +2.65 [+1.56 to +3.58] |
| 1.5 s | +0.64 [+0.06 to +1.29] | +0.12 [-1.04 to +1.61] | +0.00 [+0.00 to +0.00] | +1.81 [+0.89 to +2.72] |
| 5 s subset | +0.79 [+0.00 to +2.04] | +1.81 [+0.00 to +5.42] | +0.00 [+0.00 to +0.00] | +0.57 [+0.00 to +1.08] |

- Geometry. Results vary by limit, with some intervals spanning zero.
- Payload. Equal utilization at all four common limits.
- Mixed. Hybrid ahead at all four common limits.

The 150 ms overall mean difference was +0.22
points, with a 95% interval of -0.68 to +1.07. Under the four-attempt
cap it was +2.66, with a 95% interval of
+0.95 to +4.51. Each family has ten instances at the common limits.
These comparisons do not make the different kinds of attempt
computationally equivalent.

| Limit | Cases | First-Fit | Hybrid | Mean attempts FF / hybrid |
| --- | --- | --- | --- | --- |
| 4 attempts | 30 | 67.35% | 70.01% | 3.5 / 3.5 |
| 150 ms | 30 | 69.17% | 69.40% | 255.2 / 2.6 |
| 500 ms | 30 | 69.77% | 70.57% | 856.4 / 8.8 |
| 1.5 s | 30 | 70.35% | 70.99% | 2,564.2 / 26.1 |
| 5 s subset | 9 | 72.06% | 72.85% | 7,726.1 / 73.7 |

## Time-limited exact selection on mixed cases

HiGHS gets the first pool that the hybrid builds for the same case and
seed. The deadline covers pool construction, solver time and validation.
A late result is discarded, and the score uses the empty fallback
if no validated incumbent is returned on time. The hybrid may try
more than one pool in its budget.

| Limit | HiGHS mean | Hybrid mean | On-time HiGHS | Proven on time |
| --- | --- | --- | --- | --- |
| 150 ms | 26.21% | 82.40% | 30/30 | 4 |
| 500 ms | 84.17% | 85.23% | 30/30 | 17 |
| 1.5 s | 84.32% | 86.10% | 30/30 | 30 |
| 5 s subset | 83.94% | 86.41% | 9/9 | 9 |

[Quality versus time on mixed cases](figures/mixed_effort_v4.png)

At 150 ms HiGHS returned a nonempty validated packing on every mixed
trial, but proved only four of 30 optima. Its mean was 26.21%.
At 1.5 seconds it certified all 30 first-pool optima. The hybrid still
scored higher on average while exploring multiple pools.

The earlier mixed-pool diagnosis remains a separate offline reference.
HiGHS proved a mean of 85.62% across those 30 original pools, compared
with 83.41% for the recorded hybrid, which matched 10 pool optima.
The earlier geometry gap was predominantly coverage. The mixed gap
leaves more room for improved selection.

## Explicit QUBO penalty sensitivity

The production sampler stays conflict-free and minimizes slack
analytically. The independent neal check samples the expanded binary
model. It varies the slack penalty by divisors of 1, 100, 10,000 and
1,000,000, with exact weight units and a 1 kg alternative. The
original full-penalty setting is included for comparison.

| Family | Original penalty | Best tested | Recorded compound | Valid raw reads |
| --- | --- | --- | --- | --- |
| Payload | 25.83% | 32.15% | 32.15% | 53/640 |
| Mixed | 53.54% | 85.38% | 86.01% | 321/768 |

The first three score columns average best post-repair utilization
across the three pools per family. The raw-read column counts valid
reads across the whole tuning grid. Best tested selects a setting
after observing each pool. It is an exploratory sensitivity check,
and does not justify a general comparison of QUBO samplers.

## Reproduce and validate

Run from the project directory in the environment described in the
[README](../README.md).

```sh
python effort_benchmark.py --followup --fixed-only --output reproduced/v4_fixed
python effort_benchmark.py --followup --output reproduced/v4_sweep
python -m pip install -r requirements-qubo.txt
python explicit_qubo.py --tune --output reproduced/v4_qubo_tuning.csv
```

[Paired intervals](../results/effort_v4/intervals.csv) ·
[Attempt counts](../results/effort_v4/summary.csv) ·
[Per-run scores](../results/effort_v4/runs.csv) ·
[Returned layouts](../results/effort_v4/packings.json) ·
[Penalty grid](../results/effort_v4/explicit_qubo_tuning.csv)
