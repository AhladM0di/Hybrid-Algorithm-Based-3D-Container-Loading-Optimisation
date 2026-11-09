# Assignment review fixes

The QUBO equation, exact weight units, penalties, reduced search objective
and generated inputs are documented in model.md and the technical report.
The deterministic reference is now reported separately from the stronger
weight-aware multi-start comparator. Historical demo plots are labelled.

The main experiment reuses development cases. No fresh held-out performance
claim is made. No original main trial score, seed, placement or runtime was
changed during this review. Full instance specifications were reconstructed
and verified against the earlier stored inputs. The original main-run
environment remains unknown, explicitly recorded as null. Future main runs
record environment versions, source hashes, input protocol, complete inputs
and a deterministic reference alongside the stochastic methods.

The five-trial ZIP is the current submission. Older ZIPs are moved to the
repository-level submission_archive directory and excluded from packaging.
The report, editable report and slides retain historical supporting evidence
with its original provenance. The technical report's primary evidence paths
now identify main_v4 instead of the earlier effort_v4 comparison.
