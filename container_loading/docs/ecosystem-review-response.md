Thank you, Luciano, for reviewing the submission. I have prepared the following
changes in the project compatibility pull request:

1. **Qiskit compatibility:** The normal hardware requirements now use
   `qiskit>=2.4,<3`, keeping `qiskit-ibm-runtime==0.47.0`. I validated Qiskit
   2.4.0, 2.4.2 and 2.6.2 (the latest stable 2.x available on November 17) in
   separate Python 3.13.5 environments. Each passed all 30 existing tests,
   three new local quantum regression tests, and `pip check`. The quantum
   checks regenerate the frozen ideal references, verify routed transpilation,
   and execute Runtime SamplerV2 on a local fake backend. A separate reproduction
   requirements file retains Qiskit 2.4.2 and Runtime 0.47.0; historical inputs,
   circuits and results are unchanged. These checks used no IBM hardware credits.
2. **Documentation metadata:** Agreed—the patch removes the `documentation`
   entry pointing to the README. The project README remains in place.
3. **Classification:** Agreed—the patch removes `demo` and retains
   `optimization`, `research`, `benchmarking` and `circuit building`.

I do not have push permission on `Qiskit/ecosystem:submission-233af832`, so I
have included an exact `ecosystem-1466.patch` in the project PR for a maintainer
to apply to this existing submission after the dependency change is merged.
It also updates `requires_qiskit` and the highest tested release metadata to
2.6.2, released November 5, 2026. The project PR includes the validation report,
test logs and resolved dependency lists. No duplicate submission was created.

Thank you again for the guidance.
