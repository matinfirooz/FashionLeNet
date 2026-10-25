# Contributing

Install the package, run `python scripts/run_project.py --profile offline`, and
include the logs for any RTL/arithmetic change. Keep NumPy integer inference
independent of the systolic implementation. Add a failing example before fixing
an indexing, rounding, cache, or handshake error. Run the full trained regression
for datapath/control changes and compare every stage, not only predictions.

Keep measured data, analytic models, and target-device assumptions labeled.
Changes to quantization must version the arithmetic contract and regenerate
models, headers, golden traces and documentation together. Do not commit raw
Fashion-MNIST files, virtual environments, tool binaries or generated executables.
