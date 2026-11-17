# Qiskit 2.x compatibility validation

Validated November 17, 2026, starting from project `main` commit
`57b7e9de36372c712fa297d129882cedb744f6da`, for
[Ecosystem PR #1466](https://github.com/Qiskit/ecosystem/pull/1466).

## Result and scope

The supported installation constraint is `qiskit>=2.4,<3`, retaining
`qiskit-ibm-runtime==0.47.0`. Three separate Python 3.13.5 virtual environments
on macOS arm64 passed the following checks. The latest non-yanked stable 2.x
release returned by [PyPI](https://pypi.org/pypi/qiskit/json) was 2.6.2,
uploaded November 5, 2026; prereleases were excluded.

| Qiskit | Runtime | Existing tests | Local quantum tests | pip check |
|---|---|---|---|---|
| 2.4.0 | 0.47.0 | 30 passed | 3 passed | No broken requirements |
| 2.4.2 | 0.47.0 | 30 passed | 3 passed | No broken requirements |
| 2.6.2 | 0.47.0 | 30 passed | 3 passed | No broken requirements |

The [evidence directory](validation/qiskit-2026-11-17/) contains complete test
output, `pip check` output, resolved package versions and platform information.
These are new compatibility records, not historical experiment environments.
Both hardware and optional neal requirements were installed together. The
2.4.2 environment also installed the new reproduction requirements file.

## Code and dependency review

All Qiskit imports are in `hardware_fixtures.py` and `qpu_benchmark.py`.
The integration uses public `QuantumCircuit`, `Statevector`,
`generate_preset_pass_manager`, `QiskitRuntimeService` and `SamplerV2` APIs.
The QAOA circuit uses H, RZ, RZZ and RX gates and one fixed layer. Runtime
uses backend-specific transpilation at optimization level 2, seed 0, and
`result.data.meas.get_counts()` decoding. No algorithm/API changes were needed.

[Runtime 0.47.0 package metadata](https://pypi.org/pypi/qiskit-ibm-runtime/0.47.0/json)
requires Qiskit >=2.2.0, which overlaps the proposed range. Resolution and
`pip check` succeeded for all three tested versions, including transitive
dependencies. The base requirements remain matplotlib 3.10.9 and SciPy 1.17.1;
optional dwave-neal remains 0.6.0. No other dependency manifest sets a competing
Qiskit version, except the intentionally pinned reproduction file.

## Local quantum coverage

The three new optional tests check:

1. Complete regeneration of H0–H3 ideal references, including angle-grid
   selection, exact energies, feasible volumes and optimum probabilities.
   Structural fields match exactly; floating values use absolute tolerance 1e-12.
2. H1–H3 transpilation onto finite line-connected fake backends, with logical
   output probabilities compared after accounting for final qubit layout.
   Absolute/relative tolerances are 1e-10/1e-8 for compiler numerical effects.
3. Actual Runtime SamplerV2 local execution on a 12-qubit GenericBackendV2,
   with 1,024 simulated shots for each H0–H3 circuit, measurement decoding and
   the production packing evaluator. H0 must return exactly `01` on every shot.

No cloud service was instantiated and no hardware jobs were submitted or
retrieved. These tests do not verify current IBM authentication, backend
availability, remote service behavior or hardware noise. They skip when the
optional quantum packages are absent, preserving the base-only test workflow.

The passing logs retain upstream warnings: GenericBackendV2 uses the noiseless
BasicSimulator fallback because Aer is not installed, and Runtime plugin
discovery emits a fractional-translation deprecation warning. Neither is a
test failure; noisy simulation and migration to a newer Runtime are outside
this compatibility change.

Initial development of the new tests exposed a test-backend mismatch:
BasicSimulator has an unspecified target qubit count, which Runtime's ISA
validator rejects. A finite GenericBackendV2 fixes that test setup. An initial
1e-12 transpilation tolerance also rejected approximately 1.53e-11 probability
differences on H3; the final tolerance above accounts for these numerical
effects. Neither finding required changing production code.

## Reproduce the checks

From `container_loading`, run each version in its own environment:

```sh
for version in 2.4.0 2.4.2 2.6.2; do
  python3.13 -m venv ".venv-qiskit-$version"
  ".venv-qiskit-$version/bin/python" -m pip install \
    -r requirements-hardware.txt -r requirements-qubo.txt "qiskit==$version"
  ".venv-qiskit-$version/bin/python" -m pip check
  ".venv-qiskit-$version/bin/python" -m unittest discover -s tests -v
done
```

The supported range is a compatibility policy backed by these tested releases,
not a claim that every intermediate or future 2.x release has been tested.
Re-run the checks when updating dependencies. No claim is made for Qiskit 3.

## Historical reproducibility

`requirements-hardware-reproduction.txt` preserves the original direct pins:
Qiskit 2.4.2, Runtime 0.47.0 and the unchanged base requirements. Original
transitive versions were not fully recorded, so this is not a reconstructed
historical lockfile. The dated readiness audit remains an unchanged historical
record. All production algorithms, benchmark protocols, inputs, frozen circuit
references, classical results and IBM hardware records remain unchanged.

## Ecosystem metadata follow-up

The bot-owned PR head is `Qiskit/ecosystem:submission-233af832`, inspected at
`15e754ddc4d8709c67911836623b2f0fd37e887c`. Authenticated repository permissions
showed `push: false`, `maintain: false`, `admin: false`. The connector's
collaborator-permission endpoint was unavailable (403), so the permissions were
confirmed through the authenticated GitHub CLI repository endpoint instead.

[ecosystem-1466.patch](ecosystem-1466.patch) is an exact unified patch against
that head. It removes the redundant README documentation field and `demo`,
retains optimization/research/benchmarking/circuit building, and updates the
dependency range and highest tested release metadata. It does not delete the
README. After the project change is merged, an Ecosystem maintainer can apply
the patch to the existing PR branch with `git apply ecosystem-1466.patch`.
No duplicate submission is needed. The prepared response is in
[ecosystem-review-response.md](ecosystem-review-response.md).
