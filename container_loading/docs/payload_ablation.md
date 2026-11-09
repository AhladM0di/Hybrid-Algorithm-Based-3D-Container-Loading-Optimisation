# Payload and Search Ablation

This follow-up uses the original 20-box payload case and the two tight
geometry cases with known full-container tilings. Each case uses five
candidate-pool seeds and three annealing seeds per pool. Every variant
uses the same 240-candidate cap, 80 sweeps and eight reads. These are
matched search settings. The CSV also gives actual wall times.

## Methods compared

- **Exact repair.** Resolve invalid geometry first. On the conflict-free
  subset, solve the payload knapsack exactly in integer grams with a
  sparse dynamic program. Repair can only retain placements already
  selected.
- **Weight price.** Subtract a volume-per-gram charge from each candidate
  reward. Start with the marginal ratio from fractional knapsack and
  test multipliers of 0.5, 0.75 and 1.0.
- **Squared slack penalty.** Round package weights up and capacity down
  in 10 kg units. Add the squared residual between selected weight plus
  binary slack and capacity. The 20-box case needs nine slack bits.
  The classical sampler minimizes over those bits analytically at every
  move. This is equivalent to choosing the best slack assignment for the
  current selected boxes. It avoids constructing the dense matrix or
  sampling slack bits on a QPU. Conservative rounding can exclude some
  legal gram-level packings.
- **Search moves.** The single-flip sampler caches neighbor sums and
  tests a global penalty and smaller per-pair penalties. Compound moves
  insert a box and remove all its current blockers together. They stay
  conflict-free, use temperatures calibrated from sampled energy
  changes, and finish with a local descent. Conflict penalties do not
  affect energies along a conflict-free trajectory.

The validator checks every final packing with the original dimensions and
weights. HiGHS solves the original-gram payload problem once per pool.
Pool quality divides that optimum by the full-instance upper bound.
Search quality divides final packed volume by the certified pool optimum.
The CSV reports how many runs have a certified ratio. The JSON keeps
time-limited reference bounds separate from proven optima.

## Results

| 20-box method | Mean utilization | Best utilization | Raw invalid runs |
|---|---:|---:|---:|
| Single flips and greedy repair | 50.02% | 54.60% | 15 of 15 |
| Single flips and exact repair | 51.38% | 56.39% | 15 of 15 |
| Single flips and exact repair with per-pair penalties | 55.27% | 61.12% | 15 of 15 |
| Compound search and exact repair | 55.47% | 57.80% | 15 of 15 |
| Compound search with 0.5 weight price | 58.78% | 61.12% | 15 of 15 |
| Compound search with 0.75 weight price | 58.66% | 61.12% | 10 of 15 |
| Compound search with full weight price | 52.84% | 58.95% | 0 of 15 |
| Compound search with squared slack penalty | 58.92% | 61.12% | 0 of 15 |

The 20-box baseline reached 57.80%. Across the five pools, the certified
payload optima were 92.80–98.80% of the 61.86% weight-only bound.
The 0.5 price reached 98.91% of the pool optimum on average after
repair. The slack variant reached 99.15% and needed no repair on this
case. Exact repair alone improved mean utilization by 1.36 percentage
points on the same raw selections.

All five pools for each tight geometry case had a certified 100%
packing. Unpriced compound search reached it in all 15 runs per case,
versus single-flip means of 91.44% and 72.33% with the same sweep and
read counts. The slack variant reached only 91.67% on the tight 15-box
case. Rounding each 1 kg box to a 10 kg tick makes the 100 kg payload
appear full after 10 boxes, even though the original weights allow all
15 boxes. This is a quantization loss.

All 360 final packings passed validation. The parameter comparisons
reuse these three cases. They do not estimate performance on unseen
instance families or at equal wall-clock budgets.

[Summary CSV](../results/payload_ablation/ablation.csv) ·
[Run data and reference bounds](../results/payload_ablation/ablation.json)
