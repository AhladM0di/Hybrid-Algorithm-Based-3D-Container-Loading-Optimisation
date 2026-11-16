# Qiskit Ecosystem submission draft

Prepared for the [official submission form](https://github.com/Qiskit/ecosystem/issues/new?template=01_submission.yml).
The [MIT License](../../LICENSE) is adopted on this branch following maintainer
confirmation. Submit after the license and documentation are merged into `main`;
see the [readiness audit](ecosystem-readiness.md).

| Field | Suggested value |
|---|---|
| Project name | Hybrid Algorithm-Based 3D Container Loading Optimisation |
| Description | Classical container-loading research with QUBO placement search and small Qiskit QAOA hardware experiments. |
| Category | Application |
| Suggested labels | optimization, research, benchmarking, demo |
| Interface/API | Python, CLI |
| Stability | experimental |
| GitHub repository | https://github.com/AhladM0di/Hybrid-Algorithm-Based-3D-Container-Loading-Optimisation |
| Documentation | https://github.com/AhladM0di/Hybrid-Algorithm-Based-3D-Container-Loading-Optimisation/blob/main/README.md |
| Qiskit dependency file | https://github.com/AhladM0di/Hybrid-Algorithm-Based-3D-Container-Loading-Optimisation/blob/main/container_loading/requirements-hardware.txt |
| Home page | Leave blank; no separate site |
| Packages | Leave blank; no published package claimed |
| Reference paper | Leave blank; no publication claimed |
| Contact email | Optional: maintainer to confirm preferred address |

The description is 107 characters, below the 135-character limit. Select labels
available in the live form; request any unavailable suggested labels in an issue
comment as directed by the form.

## Maintenance expectations

This experimental project is actively developed; breaking changes are possible,
and support through GitHub issues is provided on a best-effort basis.

## Integration explanation

The main container-loading solvers are classical. The project additionally
constructs depth-1 QAOA circuits from fixed geometry candidate-selection QUBOs
using Qiskit 2.4.2. It tunes angles by ideal statevector simulation, transpiles
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

## Before submitting

- Merge the reviewed MIT license and documentation so they are available on `main`.
- Confirm the contact and personally accept the Qiskit Code of Conduct checkbox.
- Recheck recent activity and the live submission form at submission time.
