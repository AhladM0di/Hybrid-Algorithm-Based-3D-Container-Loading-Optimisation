# Seven-Minute Container Loading Demo

Run from the `container_loading` directory with the [project environment](../README.md) activated.
Use the [seven-slide deck](demo_slides.pptx) and the two recorded packing views.
The live commands verify saved results. The published comparison comes from
the frozen benchmark, since a live timed run can finish a different number
of attempts.

| Time | Show | Explain |
|---|---|---|
| 0:00–0:50 | Slides 1–2 and `data/main_comparison_protocol.json` | Each box has dimensions, weight and allowed rotations. Both methods used a 150 ms scoring cutoff. |
| 0:50–2:00 | Extract and validate both saved layout pairs using the commands below | Both results obey the same boundaries, overlap, rotation and payload checks. Utilization is packed volume divided by container volume. |
| 2:00–3:00 | Slide 3 and the main five-trial summary | Average five trials within each of 30 cases. Read the main table below. |
| 3:00–4:00 | Slide 4 and [geometry case 4108](figures/packing_4108.png) | Show a historical three-trial-run geometry example where First-Fit used more space. Point out the pale-blue free space in the mid-height cross-section. |
| 4:00–5:00 | Slide 5 and [mixed case 4302](figures/packing_4302.png) | Show a historical three-trial-run mixed example where the hybrid used more space. These examples illustrate each outcome. The overall table uses all cases. |
| 5:00–5:55 | Slide 6 and the [fixed-pool CSV](../results/heldout/geometry_pool_check.csv) | HiGHS proved all 30 geometry pool optima. Missing placements cost 4.55 points on average. Search within the pools cost another 0.21. |
| 5:55–7:00 | Slide 7 and the [earlier attempt sweep](../results/effort_v4/summary.csv) | In the earlier three-trial sweep at 150 ms First-Fit averaged 255.2 attempts and the hybrid averaged 2.6. A hybrid attempt includes building a pool and searching it. |

The two plotted examples and live validation commands use the earlier three-trial
run, not the v4 trials. Slides 4 and 5 label them as historical. The main
comparison uses weight-aware multi-start First-Fit on reused development cases.
See [the deterministic reference](deterministic_reference.md) for the assignment
baseline. The overall interval includes zero; generalization needs new cases.

## Main v4 comparison

At the 150 ms scoring cutoff, the hybrid-minus-First-Fit difference was +0.48 percentage points (paired 95% interval -0.32 to +1.26).

| Method | Mean util. | Best util. | Mean boxes | Mean volume (L) | Mean ms | Max ms | Final violations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| First-Fit | 69.15% | 70.09% | 10.31 | 663.82 | 126.44 | 162.34 | 0 |
| Hybrid | 69.63% | 70.55% | 10.15 | 668.45 | 154.71 | 200.23 | 0 |

Each method ran five times per case on 30 cases. Best utilization is the mean of the best trial on each case. Count, volume and mean elapsed time average all 150 trials per method. Final violations are counted across all 150 returned packings.

The 150 ms cutoff governs the score. A trial can keep running while its final attempt finishes. Results that finish after the cutoff are excluded. Elapsed time includes that late work. In the earlier three-trial sweep at the same cutoff, the longest calls were 165.80 ms for First-Fit and 201.54 ms for the hybrid.

[Summary CSV](../results/main_v4/summary.csv) · [Paired intervals](../results/main_v4/intervals.csv)

## Live commands

```sh
demo_dir=$(mktemp -d)
python - "$demo_dir" <<'PY'
import json
import sys
from pathlib import Path

out = Path(sys.argv[1])
results = json.loads(Path("results/heldout/heldout.json").read_text())
for case in results["cases"]:
    seed = case["seed"]
    if seed not in (4108, 4302):
        continue
    trial = case["modes"]["brief"]["trials"][0]
    (out / f"{seed}.json").write_text(json.dumps(case["instance"]))
    for method in ("first_fit", "hybrid"):
        (out / f"{seed}-{method}.json").write_text(json.dumps(trial[method]["placements"]))
PY
for seed in 4108 4302; do
    for method in first_fit hybrid; do
        printf '\nCase %s · %s\n' "$seed" "$method"
        python check_packing.py "$demo_dir/$seed.json" "$demo_dir/$seed-$method.json"
    done
done
```

To show a fresh solver run if time permits, use the extracted geometry input:

```sh
python -c 'import json,sys; from pathlib import Path; from baseline import multistart_report; from check_packing import load_instance; print(json.dumps(multistart_report(load_instance(Path(sys.argv[1])), 0.15, 301, weight_aware=True)))' "$demo_dir/4108.json"
python hybrid.py "$demo_dir/4108.json" --cap 160 --sweeps 45 --reads 4 --exact-slack --varied-corners
```

The last command runs a single hybrid attempt for illustration. The timed
benchmark uses the full deadline logic in `heldout_benchmark.py`.
