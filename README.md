# Hybrid Algorithm-Based 3D Container Loading Optimisation

In the repeatable four-attempt comparison on 30 cases, weight-aware
First-Fit averaged 67.17% utilization and the hybrid averaged 69.26%.
The methods do different work per attempt. At 150 ms, the follow-up
averaged 69.11% for First-Fit and 68.94% for the hybrid, with 259 versus
three attempts per method on average.

## Final deliverables

- [Technical report](container_loading/docs/technical_report.pdf)
- [Editable student lab report](container_loading/docs/container_loading_lab_report.docx)
- [Seven-minute demo guide](container_loading/docs/demo.md) and [PowerPoint slides](container_loading/docs/demo_slides.pptx)
- [3D geometry case](container_loading/docs/figures/packing_4108.png) and [3D mixed case](container_loading/docs/figures/packing_4302.png)

## Evidence and reproduction

- [Fixed-work and budget follow-up](container_loading/docs/effort.md)
- [Setup and reproduction commands](container_loading/README.md)
- [Held-out and full-support findings](container_loading/docs/heldout.md)
- [Per-instance results](container_loading/results/heldout/instances.csv) and [HiGHS fixed-pool diagnostics](container_loading/results/heldout/geometry_pool_check.csv)
- [Payload and search ablation](container_loading/docs/payload_ablation.md)
- [IBM Quantum fixture results](container_loading/results/hardware.json)

The [v1 archive](container_loading/docs/archive/v1/) holds the initial report
and presentation materials.
