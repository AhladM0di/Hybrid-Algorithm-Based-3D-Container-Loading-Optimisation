# Qiskit Ecosystem submission draft

The existing submission is under review in
[Ecosystem PR #1466](https://github.com/Qiskit/ecosystem/pull/1466), originating
from issue #1465. Update that submission; do not create a duplicate. The license
and original readiness documentation are already merged into `main`.
See the [compatibility report and metadata patch](qiskit-compatibility.md).

| Field | Suggested value |
|---|---|
| Project name | Hybrid 3D Container Loading Optimisation |
| Description | Classical container-loading research with QUBO placement search and small Qiskit QAOA hardware experiments. |
| Category | Application |
| Suggested labels | optimization, research, benchmarking, circuit building |
| Interface/API | Python, CLI |
| Stability | experimental |
| GitHub repository | https://github.com/AhladM0di/Hybrid-Algorithm-Based-3D-Container-Loading-Optimisation |
| Documentation | Leave blank; the repository README is already discoverable |
| Qiskit dependency file | https://github.com/AhladM0di/Hybrid-Algorithm-Based-3D-Container-Loading-Optimisation/blob/main/container_loading/requirements-hardware.txt |
| Home page | Leave blank; no separate site |
| Packages | Leave blank; no published package claimed |
| Reference paper | Leave blank; no publication claimed |
| Contact email | Optional: maintainer to confirm preferred address |

The project display name is 40 characters, below the 50-character limit; the
GitHub repository name and URL remain unchanged. Ecosystem reads this value
from the `Project name` field in the submission issue body, not this file or
the issue title. The original display-name correction is already reflected in PR #1466.

The description is 107 characters, below the 135-character limit. Select labels
available in the live form; request any unavailable suggested labels in an issue
comment as directed by the form.

## Maintenance expectations

This experimental project is actively developed; breaking changes are possible,
and support through GitHub issues is provided on a best-effort basis.

## Integration explanation

The main container-loading solvers are classical. The project additionally
constructs depth-1 QAOA circuits from fixed geometry candidate-selection QUBOs
using Qiskit >=2.4,<3 (historical experiments used 2.4.2). It tunes angles by
ideal statevector simulation, transpiles
for IBM backends and runs circuits through qiskit-ibm-runtime 0.47.0 SamplerV2.
H0 checks measurement ordering; H1–H3 use 3, 4 and 12 placement qubits. Saved
IBM hardware samples are decoded, checked for raw feasibility, repaired
classically and compared with exact fixed-pool references and classical
annealing. These experiments demonstrate integration, not quantum advantage
or full-scale QPU container loading.

The exploratory classical comparison reports +0.48 percentage points with a
paired 95% interval of −0.32 to +1.26, which includes zero. The cases were reused
during development. Ideal, physical QPU and classical benchmark records are
separate and are not interchangeable evidence.

## Review follow-up

- Merge the compatibility changes so the dependency range is available on `main`.
- Ask an Ecosystem maintainer to apply the supplied patch to the existing PR branch.
