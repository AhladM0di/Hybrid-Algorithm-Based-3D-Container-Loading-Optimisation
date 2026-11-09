# Held-Out Packing Comparison

The earlier three cases are development cases. This comparison uses
30 new instances across three groups, with 10, 15 and 20 boxes in each
group's count schedule. The geometry group uses container splits with
saved tilings that certify 100% utilization. The payload group uses
smaller boxes and varying weights under a tighter weight limit.
The mixed group varies size, rotation permission and weight, and offers
more box volume than the container can hold. Every generated case was
included, even when deterministic First-Fit packed all boxes.

The [frozen protocol](../data/heldout_protocol.json) fixes generator and
trial seeds, a 150 ms deadline per method, and the hybrid's search
settings. Multi-start First-Fit tries deterministic volume order first,
then longest edge and seeded shuffled orders. It randomizes orientation
order on restarts. The hybrid uses the same deadline for independent
candidate generation, scoring, search, repair and validation. Both
retain only results that finish validation and reporting before the
deadline. An in-flight attempt can finish late and is discarded, so
recorded elapsed time can exceed the scoring deadline. Methods alternate
run order within cases.

Each method runs three times per instance. The analysis averages those
trials first, then counts wins, ties and losses across instances. The
95% interval resamples paired instance differences. These intervals
describe this set of generated families at this budget. Since the number
of completed attempts depends on the machine and system load, a rerun
can produce different scores.

## Full base support

Both methods also run with the same optional support rule. A box can
sit on the floor or rest with its full base covered by one or more boxes
beneath it. First-Fit checks the rule at placement time. The hybrid uses
it while building candidate layouts and removes unsupported boxes in
bottom-up order after payload repair. This handles lost support when
the selected subset differs from a source layout. It measures geometric
contact. Load-bearing strength and physical stability remain outside the
model.

## Held-out results

Differences are hybrid utilization minus multi-start First-Fit
utilization, in percentage points. Win, tie and loss counts are for
the hybrid after averaging the three trials within each instance.

| Mode and family | First-Fit mean | Hybrid mean | Difference | 95% interval | Wins / ties / losses | Mean attempts First-Fit / hybrid |
|---|---:|---:|---:|---:|---:|---:|
| Brief, all | 69.41% | 68.89% | −0.52 | −1.89 to +0.61 | 13 / 9 / 8 | 260.7 / 3.0 |
| Brief, geometry | 98.72% | 95.24% | −3.48 | −6.16 to −1.14 | 1 / 3 / 6 | 17.0 / 2.6 |
| Brief, payload | 27.71% | 28.02% | +0.31 | +0.03 to +0.63 | 4 / 6 / 0 | 668.4 / 3.7 |
| Brief, mixed | 81.80% | 83.41% | +1.61 | +0.10 to +2.85 | 8 / 0 / 2 | 96.6 / 2.8 |
| Full support, all | 67.96% | 63.72% | −4.24 | −6.17 to −2.39 | 6 / 1 / 23 | 263.3 / 3.1 |
| Full support, geometry | 98.14% | 91.62% | −6.52 | −10.23 to −2.84 | 2 / 1 / 7 | 36.4 / 2.8 |
| Full support, payload | 27.71% | 22.78% | −4.92 | −7.29 to −2.92 | 0 / 0 / 10 | 661.7 / 3.7 |
| Full support, mixed | 78.03% | 76.75% | −1.28 | −3.87 to +1.28 | 4 / 0 / 6 | 91.7 / 2.8 |

Five cases packed every box on the deterministic first pass. The
overall brief-mode interval crosses zero, so the run leaves the
overall ordering uncertain at this budget. The hybrid had higher
mean utilization on the payload and mixed families, while
multi-start First-Fit did better on the geometry family.

Requiring full support reduced overall mean utilization by 1.45
points for First-Fit and 5.17 points for the hybrid. The hybrid's
bottom-up cleanup removed 76 boxes across the 90 best-per-trial
outputs in support mode. The sampler still scores geometric conflicts
and payload without scoring support dependencies during search.
Every final result passed the relevant shared validator.

[Instance scores](../results/heldout/instances.csv) ·
[Run data, settings, and tiling witnesses](../results/heldout/heldout.json)


## Exact weight units on the development cases

The slack sampler now uses the greatest common divisor of the package
weights and payload capacity in grams when exact slack is selected.
The 45 matched development runs all passed validation before repair.

| Case | Mean utilization | Best utilization |
|---|---:|---:|
| Tight geometry, 10 boxes | 100.00% | 100.00% |
| Tight geometry, 15 boxes | 100.00% | 100.00% |
| Payload, 20 boxes | 58.98% | 61.12% |

The tight 15-box case recovered from 91.67% with 10 kg rounding to
100.00% with exact units. [Development results](../results/exact_slack/ablation.csv)

## Support during search

The post-repair losses motivated a separate rerun with the frozen
settings and the same full-support rule. This variant rejects a
compound move if it leaves any selected box without full support,
including boxes that would lose a supporting neighbor. The hybrid
averaged 66.30% utilization, up from 63.72% with support checked only
during candidate generation and after repair. It still trailed
multi-start First-Fit by 1.66 points overall. The paired 95% interval
was −3.65 to +0.01 points, with 14 wins, seven ties and nine losses.

All 90 returned raw hybrid selections passed full-support validation
and needed no support cleanup. The search still considers only the
generated candidates, and these results apply to the recorded deadline.

[Instance scores](../results/support_search/instances.csv) ·
[Support-aware run data](../results/support_search/heldout.json)

## Fixed-pool check on the geometry cases

HiGHS solved the 30 candidate pools behind the recorded brief-mode
hybrid results, three per geometry instance. Each pool was rebuilt
from its recorded seed and cap. The check matched the candidate and
conflict counts, verified that the recorded placements belonged to
the reconstructed pool, and validated the HiGHS packing under the
original geometry and payload rules. The primary benchmark results
and time budget were kept separate from this diagnostic.

All 30 solves returned proven optima within a 12-second limit per pool.
There were no time-limited results. The mean recorded hybrid score
was 95.24%, and the mean fixed-pool optimum was 95.45%, against the
verified full-instance optimum of 100%. The average gap breaks down
into **4.55 percentage points from candidate coverage** and **0.21
points from search within the available pool**.

- **17 of 30 pools** could not represent a full tiling.
- The hybrid reached the fixed-pool optimum on **27 of 30 pools**.
- On instance 4100, trial 301, the pool could reach 100% and the
  hybrid reached 96.25%. The other two search gaps occurred in
  pools whose proven optima were below 100%.

For these recorded geometry runs, candidate coverage accounts for
most of the gap to the full-instance optimum. The CSV keeps solver
status, incumbent, and lower and upper bounds separate so the same
check can report unresolved pools if a rerun reaches the time limit.

```sh
python geometry_pool_check.py --seconds 12 --output reproduced/geometry_pool_check.csv
```

[Fixed-pool diagnostic CSV](../results/heldout/geometry_pool_check.csv)

See the [effort follow-up](effort.md) for fixed-work and budget-sweep results.
