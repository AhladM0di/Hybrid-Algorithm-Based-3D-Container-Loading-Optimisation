# Hybrid Algorithm-Based 3D Container Loading Optimisation

At the 150 ms scoring cutoff, the hybrid-minus-First-Fit difference was +0.48 percentage points (paired 95% interval -0.32 to +1.26). The main comparison uses five trials per case against weight-aware multi-start First-Fit. These are reused development cases, so the result is exploratory and does not establish an overall improvement. The cutoff determines which packings count toward the score. Measured elapsed time includes late attempts.

## Final deliverables

- [Technical report](container_loading/docs/technical_report.pdf)
- [Editable student lab report](container_loading/docs/container_loading_lab_report.docx)
- [Seven-minute demo guide](container_loading/docs/demo.md) and [PowerPoint slides](container_loading/docs/demo_slides.pptx)
- [3D geometry case](container_loading/docs/figures/packing_4108.png) and [3D mixed case](container_loading/docs/figures/packing_4302.png)

## Evidence and reproduction

- [Main five-trial v4 comparison](container_loading/results/main_v4/summary.csv) and [paired intervals](container_loading/results/main_v4/intervals.csv)
- [Earlier three-seed budget follow-up](container_loading/docs/effort_v4.md)
- [Setup and reproduction commands](container_loading/README.md)
- [Held-out and full-support findings](container_loading/docs/heldout.md)
- [Per-instance results](container_loading/results/heldout/instances.csv) and [HiGHS fixed-pool diagnostics](container_loading/results/heldout/geometry_pool_check.csv)
- [Payload and search ablation](container_loading/docs/payload_ablation.md)
- [IBM Quantum fixture results](container_loading/results/hardware.json)

The [v1 archive](container_loading/docs/archive/v1/) holds the initial report
and presentation materials.

The current submission is [the five-trial ZIP](container-loading-submission-v4-five-trial.zip). Older ZIPs are retained in `submission_archive/`.
