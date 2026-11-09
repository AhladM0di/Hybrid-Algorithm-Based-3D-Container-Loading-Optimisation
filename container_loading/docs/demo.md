# Live demo · 7 minutes

Run from the project directory in an activated environment with the
dependencies installed. Keep the recorded plots and results available for the
comparison. The hardware section uses retrieved IBM results.

| Time | Show | Explain |
|---|---|---|
| 0:00–0:50 | Open `data/packages_20.json`. | Dimensions are in millimetres. The payload cap is 4,000 kg. Each package declares its rotation permission. |
| 0:50–1:40 | Run the feasibility checker and the tests. | Face contact is allowed. The tests reject overlap, forbidden rotations, duplicate IDs and excess payload. |
| 1:40–2:40 | Run the classical baseline on the 20-package case. | It tries large packages first and uses a fixed order for all ties and positions. |
| 2:40–4:00 | Run the hybrid solver with seed 0. | Every binary variable selects a placement. The QUBO penalizes overlap and duplicate package choices. Repair enforces the payload cap. |
| 4:00–5:15 | Open the 20-package plot and the benchmark CSV. | Both methods packed eight packages at 57.80%. On these cases, the baseline achieved the same volume faster. |
| 5:15–6:25 | Show the hardware summary below. | H0 verifies bit order. H1–H3 compare QPU samples against exact optima for the same reduced models. |
| 6:25–7:00 | Return to the 3D plot. | Identify the unused space and explain why geometric feasibility alone cannot certify a physical load. |

## Commands

```sh
python check_packing.py data/packages_10.json data/example_packing.json
python -m unittest discover -s tests
python baseline.py data/packages_20.json > /tmp/container-baseline.json
python hybrid.py data/packages_20.json --seed 0 > /tmp/container-hybrid.json
python -c 'import json; from pathlib import Path; paths = [Path("/tmp/container-baseline.json"), Path("/tmp/container-hybrid.json")]; print(*[(p.stem, json.loads(p.read_text())["metrics"]) for p in paths], sep="\n")'
cat results/benchmark.csv
```

Open [the 20-package comparison](../results/packing_20.png) and
[the recorded hardware results](../results/hardware.json). IBM `ibm_fez`
returned the intended H0 pattern on 1,013 of 1,024 shots. Across five
1,024-shot runs per fixture, the QPU reached the exact raw optimum on
31.00% of H1 shots, 24.96% of H2 shots, and 1.54% of H3 shots.

## Rehearsal cues

- Show raw and final validity separately in the hybrid JSON output.
- Point to a package ID in both panels and then to an unused region.
- Distinguish a raw optimum hit from the best feasible packing after repair.
