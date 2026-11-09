# Deterministic reference on the same 30 inputs

These single-pass First-Fit Decreasing results are copied from the earlier recorded brief-mode run in `results/heldout/heldout.json`. Inputs match the main comparison exactly. Timings belong to that earlier run; they were not measured alongside the five-trial main run. This deterministic reference is distinct from weight-aware multi-start First-Fit.

| Family | Utilization | Boxes | Volume (L) | Runtime (s) | Violations |
|---|---:|---:|---:|---:|---:|
| all | 65.79% | 9.13 | 631.60 | 0.001899 | 0 |
| geometry | 98.72% | 13.70 | 947.70 | 0.002608 | 0 |
| payload | 26.80% | 7.60 | 257.30 | 0.000501 | 0 |
| mixed | 71.85% | 6.10 | 689.80 | 0.002589 | 0 |

The main five-trial results use the stronger weight-aware multi-start comparator: 69.15% utilization versus 69.63% for the hybrid. Its paired interval includes zero. The deterministic reference answers the assignment baseline requirement but does not replace that stronger comparison.
