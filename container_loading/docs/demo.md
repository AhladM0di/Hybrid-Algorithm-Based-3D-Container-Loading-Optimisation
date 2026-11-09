# Seven-Minute Container Loading Demo

Run from the `container_loading` directory with the [project environment](../README.md) activated.
Use the [seven-slide deck](demo_slides.pptx) and the two recorded packing views.
The live commands verify saved results. The published comparison comes from
the frozen benchmark, since a live timed run can finish a different number
of attempts.

| Time | Show | Explain |
|---|---|---|
| 0:00–0:50 | Slides 1–2 and `data/heldout_protocol.json` | Each box has dimensions, weight and allowed rotations. Both methods had 150 ms per trial. |
| 0:50–2:00 | Extract and validate both saved layout pairs using the commands below | Both results obey the same boundaries, overlap, rotation and payload checks. Utilization is packed volume divided by container volume. |
| 2:00–3:00 | Slide 3 and the held-out summary | Average three trials within each of 30 cases. Overall, First-Fit averaged 69.41% and the hybrid averaged 68.89%. The paired interval crosses zero. |
| 3:00–4:00 | Slide 4 and [geometry case 4108](figures/packing_4108.png) | Show a recorded geometry trial where First-Fit used more space. Point out the pale-blue free space in the mid-height cross-section. |
| 4:00–5:00 | Slide 5 and [mixed case 4302](figures/packing_4302.png) | Show a recorded mixed trial where the hybrid used more space. These examples illustrate each outcome. The overall table uses all cases. |
| 5:00–5:55 | Slide 6 and the [fixed-pool CSV](../results/heldout/geometry_pool_check.csv) | HiGHS proved all 30 geometry pool optima. Missing placements cost 4.55 points on average. Search within the pools cost another 0.21. |
| 5:55–7:00 | Slide 7 and the [attempt summary](../results/effort/summary.csv) | Under the four-attempt cap, the hybrid averaged 69.26% and First-Fit averaged 67.17%. At 150 ms First-Fit finished about 259 attempts and the hybrid finished about three. A hybrid attempt includes building a pool and searching it. |

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
python baseline.py "$demo_dir/4108.json" --seconds 0.15 --seed 301
python hybrid.py "$demo_dir/4108.json" --cap 160 --sweeps 45 --reads 4 --exact-slack
```

The last command runs a single hybrid attempt for illustration. The timed
benchmark uses the full deadline logic in `heldout_benchmark.py`.
