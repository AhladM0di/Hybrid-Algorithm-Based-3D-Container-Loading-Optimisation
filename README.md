# Hybrid Algorithm-Based 3D Container Loading Optimisation

An experimental Python research project for selecting and positioning rectangular
packages in a single container. It compares classical First-Fit methods with a
candidate-placement QUBO search and studies small QAOA circuits using Qiskit.
The motivation is to separate candidate coverage, search quality, payload
handling and sampling effects in a reproducible loading experiment.

The larger loading workflow is classical. Qiskit is used for small, fixed
hardware experiments; the saved results do not demonstrate full-size loading
on a QPU, quantum advantage or statistically established overall superiority.

## Optimization problem

Maximize packed volume (and hence utilization of a fixed container), allowing
packages to be omitted. A valid packing must obey permitted axis-aligned
rotations, container boundaries, non-overlap, at most one placement per package,
and total weight no greater than payload capacity. Dimensions and coordinates
are integer millimetres; weights are integer grams. Face contact is allowed.
Full-base support is optional and is not enforced in the main comparison.

Each candidate fixes a package, position and orientation. With selection bits
`x_i`, volume rewards `v_i` and conflicting pairs `C`, the geometry QUBO is:

```text
E(x) = -Σ_i v_i x_i + λ Σ_(i,j in C) x_i x_j
```

A pair conflicts if its placements overlap or represent the same package.
The default global penalty exceeds the largest reward. The optional expanded
payload formulation adds `μ(Σ_i a_i x_i + Σ_k 2^k y_k − B)^2`, where weights and
capacity are divided by their exact greatest common divisor and `y` encodes
nonnegative slack. See the [model specification](container_loading/docs/model.md)
for assumptions, penalties and experiment definitions.

## Classical and QUBO architecture

1. Generate a capped pool from layouts with different package orders and,
   optionally, coordinate priorities.
2. Search placement selections with classical simulated annealing and compound
   insertion/removal swaps. In exact-slack mode the production solver minimizes
   slack analytically; it does not sample all expanded slack bits.
3. Repair geometric conflicts and solve a weight knapsack over the remaining
   selections, then validate with the shared feasibility checker.
4. Compare against deterministic First-Fit Decreasing or weight-aware multi-start
   First-Fit. SciPy/HiGHS supplies fixed-pool reference optima or time-limited bounds.

The separate [explicit QUBO experiment](container_loading/explicit_qubo.py) samples
placement and slack bits with `dwave-neal`, a classical sampler. It is distinct
from both the production compound search and the Qiskit hardware experiment.

## Qiskit integration and IBM Quantum experiments

[hardware_fixtures.py](container_loading/hardware_fixtures.py) constructs Qiskit
`QuantumCircuit` objects. Substitution `x_i = (1 − Z_i)/2` maps the geometry QUBO
to an Ising constant, single-qubit fields and pair couplings. A depth-1 QAOA
ansatz starts in `|+⟩`, applies `RZ(2γh_i/λ)` and `RZZ(2γJ_ij/λ)` cost rotations,
then `RX(2β)` mixers. The constant contributes only global phase. Here depth-1
means one QAOA layer, not one compiled gate layer. Angles are selected on an
ideal statevector grid and frozen; there is no on-device variational optimizer.
The hardware circuits contain placement bits, not the expanded payload slack.

[qpu_benchmark.py](container_loading/qpu_benchmark.py) transpiles for the selected
IBM backend at optimization level 2 with seed 0, adds measurements, and executes
through IBM Quantum Runtime `SamplerV2`. It reverses Qiskit's register strings
into candidate-index order, evaluates raw QUBO energies and feasibility, and
separately reports the best packing after classical repair. Exact enumeration
provides references for these small fixed pools, not for unrestricted loading.

| Fixture | Logical qubits | Purpose |
|---|---:|---|
| H0 | 2 | Measurement-order check; not a QAOA optimization |
| H1 | 3 | Overlap tradeoff |
| H2 | 4 | Rotation and duplicate-package alternatives |
| H3 | 12 | Frozen reduced pool from the 10-package dataset |

The [saved physical results](container_loading/results/hardware.json) record
`ibm_fez` jobs dated November 9, 2026: H0 returned `01` on 1,013/1,024 shots;
H1–H3 each have five 1,024-shot runs. Pooled raw optimum-hit rates are 31.00%,
24.96% and 1.54%, respectively. Ideal statevector probabilities and classical
annealing samples are stored separately under `local`. These are workflow and
noise observations, not evidence of a quantum performance advantage. Job IDs,
counts and recorded metrics are retained; this documentation review did not
retrieve jobs or independently authenticate their execution with IBM.

## Project status and support

This experimental project is actively developed; breaking changes are possible,
and support through GitHub issues is provided on a best-effort basis.

## Installation and local execution

Use Python 3.13. From the repository root:

```sh
cd container_loading
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python check_packing.py data/packages_10.json data/example_packing.json
python baseline.py data/geometry_10.json
python hybrid.py data/geometry_10.json --cap 240 --seed 0 --sweeps 200 --reads 16
```

Optional Qiskit installation and **local-only** ideal fixture reproduction:

```sh
python -m pip install -r requirements-hardware.txt
mkdir -p reproduced
python hardware_fixtures.py > reproduced/hardware_ideal.json
```

[requirements-hardware.txt](container_loading/requirements-hardware.txt) supports
Qiskit **>=2.4,<3** with `qiskit-ibm-runtime` **0.47.0**, and includes the base
requirements. Local compatibility tests pass on Qiskit 2.4.0, 2.4.2 and 2.6.2;
see the [validation report](container_loading/docs/qiskit-compatibility.md).
For the original direct experiment versions, install
[requirements-hardware-reproduction.txt](container_loading/requirements-hardware-reproduction.txt)
instead, which retains Qiskit **2.4.2** and Runtime **0.47.0**.
[requirements-qubo.txt](container_loading/requirements-qubo.txt)
adds `dwave-neal` for the separate explicit-QUBO experiment. Other direct
dependencies are pinned; transitive dependencies are not fully locked.

For a deliberately requested physical rerun, see the
[hardware instructions](container_loading/README.md#optional-ibm-hardware-experiment).
That command requires a configured IBM account and consumes hardware allocation.
Local tests and ideal simulation require neither credentials nor a QPU.

## Benchmarks and findings

From `container_loading`, write new outputs outside the historical `results`:

```sh
python main_comparison.py --output reproduced/main_v4
python heldout_benchmark.py --output reproduced/heldout
python benchmark.py --output reproduced/revised
```

The [main protocol](container_loading/data/main_comparison_protocol.json) compares
30 generated geometry, payload and mixed cases, with five paired trials (seeds
301–305). Both methods score only validated results completed within 150 ms;
actual elapsed time includes late attempts. “First-Fit” in these result tables
is the stronger weight-aware multi-start method, not the single-pass baseline.

| Main comparison | Mean utilization |
|---|---:|
| Weight-aware multi-start First-Fit | 69.1479% |
| Classical hybrid | 69.6299% |
| Paired hybrid difference | +0.4819 percentage points |
| Paired bootstrap 95% interval | −0.3194 to +1.2639 percentage points |

Sources: [summary](container_loading/results/main_v4/summary.csv) and
[intervals](container_loading/results/main_v4/intervals.csv). The bootstrap
resamples 30 case means with 5,000 draws (seed 9503). Both methods have zero
recorded final violations. The interval includes zero. These cases were reused
during development, so the result is exploratory, not a fresh held-out test.
The earlier [held-out evaluation](container_loading/results/heldout/) used three
trials per instance; its cases were subsequently reused in the main comparison.
Neither that directory name nor five repeated trials establishes independent
confirmation of the final method. Ideal simulation, physical hardware results
and these classical loading benchmarks answer different questions.

The historical main run did not record its environment; its inputs were later
reconstructed and checked. New runs save environment versions and source hashes.
Timing-limited runs can differ across machines even with identical seeds. See
[the detailed reproduction guide](container_loading/README.md) for fixed-work
comparisons, candidate-pool diagnostics, support modes and payload ablations.

## Limitations and research directions

Candidate-pool restriction can exclude good placements. Exact pool references
and payload repair do not prove globally optimal loading. Physical stability,
load-bearing capacity, weight distribution and cargo securing are outside the
model. Support checks alone do not certify a safe physical load.

Future work includes preregistered independent test cases, wider timing and
fixed-work studies, better candidate coverage, payload coefficient scaling,
and larger or deeper QAOA experiments with explicit resource accounting.
Any claimed benefit would require suitable classical comparators and uncertainty
analysis. The Python/CLI interface and experimental settings may change.

## Repository structure

- `container_loading/baseline.py`, `hybrid.py`: classical solvers and QUBO search.
- `container_loading/feasibility.py`, `check_packing.py`: model and validation.
- `container_loading/hardware_fixtures.py`, `qpu_benchmark.py`: Qiskit experiments.
- `container_loading/explicit_qubo.py`, `reference_solver.py`: independent samplers/references.
- `container_loading/data/`: inputs, witnesses and frozen protocols.
- `container_loading/results/`: historical numerical results and plots.
- `container_loading/tests/`: existing unit tests.
- `container_loading/docs/`: model, readiness audit and submission draft.

## Licensing and community

This project is licensed under the [MIT License](LICENSE), with copyright
attributed to Ahlad Modi. Adoption is based on the maintainer's rights
confirmation; see the [ownership and eligibility audit](container_loading/docs/ecosystem-readiness.md).
Third-party dependencies and any third-party material retain their own terms.

### AI assistance

This project was developed by Ahlad Modi with assistance from OpenAI Codex.
Codex assisted with code and documentation development. AI assistance does not
constitute independent validation of the implementation or experimental findings.

Community participation follows the [Code of Conduct](CODE_OF_CONDUCT.md).
The [Qiskit Ecosystem submission draft](container_loading/docs/qiskit-ecosystem-submission.md)
is prepared for use after the documented gaps are resolved.
