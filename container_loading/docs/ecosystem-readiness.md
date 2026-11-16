# Qiskit Ecosystem readiness audit

Reviewed November 16, 2026 against `origin/main` at `02cc570` (fetched before
creating `docs/qiskit-ecosystem-readiness`). Scope is the Git-tracked project,
not unrelated ignored learning materials in the surrounding workspace.

## Eligibility

The [official submission form](https://github.com/Qiskit/ecosystem/blob/main/.github/ISSUE_TEMPLATE/01_submission.yml)
requires Qiskit integration, Qiskit 2.0+ compatibility, an OSI-approved license,
maintainer activity in the last six months, and adherence to Qiskit's conduct
policy. Acceptance remains the Ecosystem reviewers' decision.

| Requirement | Evidence and status |
|---|---|
| Genuine integration | `hardware_fixtures.py` builds QAOA circuits; `qpu_benchmark.py` uses Runtime SamplerV2, backend transpilation and measurement decoding. Present. |
| Qiskit 2.0+ | Hardware requirements pin 2.4.2 and Runtime 0.47.0; ideal fixtures reproduced locally using these versions. Verified for this environment, not every 2.x release. |
| OSI-approved license | MIT text prepared in [LICENSE-MIT.proposed](LICENSE-MIT.proposed). **Open:** rights review and adoption of root `LICENSE` required. |
| Recent activity | Existing main commit `02cc570`, November 10, 2026, is within six months of this review. Recheck when submitting. |
| Conduct | [Project policy](../../CODE_OF_CONDUCT.md) requires Qiskit's policy. The submitting maintainer must personally accept the form's conduct agreement. |

## Ownership and licensing review

All nine commits reachable in the inspected history identify Ahlad Modi
(`ahlad08@vt.edu`) as author and committer. No LICENSE, COPYING or NOTICE file
was found in that history. No third-party copyright notices, copied-code
attributions or vendored dependency source were found in the current tracked
Python/Markdown files. This is a limited provenance review, not proof of sole
ownership or exhaustive similarity detection.

Generated benchmark families are defined in `heldout_benchmark.py`; the model
specification records seeds and generators. The original package JSON inputs
entered with the initial implementation commits without an external dataset
license or provenance statement. Historical commits include coursework reports,
presentations and a preserved supporting PDF; those artifacts were removed
from the current tree. Their rights and any course, collaborator or institutional
terms cannot be established from commit authorship. No historical attribution
or notice has been removed or changed by this readiness work.

Before adopting the proposed MIT text, the maintainer should confirm ownership
or permission for the original inputs, code and retained outputs, whether any
collaborators require attribution, and whether coursework/institutional terms
apply. The proposed `Copyright (c) 2026 Ahlad Modi` follows the visible history;
it must be corrected if other rights holders exist. After confirmation, adopt
the proposal as root `LICENSE` and update the README and submission status.
Do not assume that adopting it licenses third-party historical artifacts.

Direct external dependencies are matplotlib, SciPy, Qiskit, Qiskit IBM Runtime
and optional dwave-neal; NumPy is also imported and supplied transitively.
They are installed dependencies, not vendored project code. Their own licenses
and bundled notices remain authoritative; a project MIT license does not
replace them. Requirements files are consistent through shared base includes,
but they are not complete transitive lockfiles.

## Scientific and implementation checks

Inspected both READMEs, all three requirements files, hardware fixture and
Runtime code, explicit QUBO expansion, classical search and repair, validator,
reference solver, benchmark protocols, tests and saved results. The main paired
mean difference and bootstrap interval were recomputed from `instances.csv`:
+0.481944 percentage points, 95% interval −0.319444 to +1.263889. This matches
the stored tables and does not establish overall superiority.

The main comparison reuses the earlier held-out cases. The QPU fixtures encode
only geometry selection; payload slack in the expanded classical experiment
must not be attributed to those circuits. Physical result samples were decoded
and reevaluated locally against frozen fixtures. No IBM jobs were queried or
submitted, and no QPU allocation was consumed.

## Validation

- Python 3.13 project environment: all 30 existing unit tests pass.
- Installed Qiskit 2.4.2, Runtime 0.47.0, matplotlib 3.10.9 and SciPy 1.17.1
  match the direct pins; optional dwave-neal 0.6.0 installed for validation.
- `pip check` reports no broken requirements.
- `hardware_fixtures.py` reproduces the entire frozen ideal reference exactly.
- All 15 saved H1–H3 physical evaluations reproduce from their saved samples;
  each contains 1,024 shots. H0 saved counts and bit ordering were inspected.
- Feasibility checker, baseline and hybrid README examples execute locally.
- Optional explicit-QUBO experiment completed with neal, writing six cases to
  `/tmp/qiskit-readiness-explicit.csv`.
- Main five-trial reproduction completed (30 cases, 300 stochastic runs), writing to `/tmp/qiskit-readiness-main`, preserving
  historical outputs. Timing-limited reruns are not expected to match numerically.
- Relative documentation links and Git diff whitespace checked.
- No core algorithms, dependency pins, inputs or historical results changed.

The full ablation/budget sweeps and physical hardware reruns are outside this
lightweight validation. Historical execution provenance is limited to saved
records; the original main environment is explicitly unknown. No package,
publication or independent benchmark replication is claimed.
