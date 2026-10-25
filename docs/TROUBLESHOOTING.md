# Troubleshooting

- **`No module named fashionlenet`:** activate the intended Python environment and
  run `python -m pip install -e .` from the repository root. To avoid activation on
  Windows, call `.\.venv\Scripts\python.exe` explicitly.
- **PyTorch unavailable:** integer demo/reference need only core dependencies;
  training and pruning need `python -m pip install -e ".[train]"`. Use the official
  CPU wheel index when appropriate. No torchvision dependency is required.
- **`iverilog`/`vvp` missing:** install Icarus Verilog; on Ubuntu/WSL run
  `sudo apt-get install iverilog`. Ensure both commands are on PATH. Use the
  `IVERILOG` and `VVP` environment variables for custom executable locations.
  A relocated Icarus may also require `IVERILOG_IVL` for its support directory.
- **`$readmemh` / `model_config.svh` error:** run commands from the project root
  and point `--bundle` to a complete exported directory. Do not mix a header
  from one model with memory or expected traces from another.
- **Dataset checksum fails:** remove only the corrupt IDX gzip file from the
  chosen data directory and rerun `fashionlenet download`. An HTML error page is
  never accepted as dataset bytes. Offline users can copy the four verified IDX
  files into `data/`; they are intentionally not bundled in the ZIP.
- **Pruning does not shrink a dense file:** unstructured zeros retain shapes.
  The CSR estimate counts indices; structural pruning actually removes widths.
  High pruning levels can destroy accuracy without recovery training.
- **MACs fall but cycles do not:** zero gating suppresses arithmetic without
  compacting time slots or skipping memory reads. Compare the explicit counters.
- **Cache is slower in a particular layer:** a miss fills 16 separate L2 bytes;
  conflict misses and poor spatial reuse can overwhelm hit savings. Compare
  cached and uncached runs with the same L2 latency.
- **Timing/resource issue in Vivado:** inspect runtime div/mod address generation,
  memory inference and critical paths. The portable design uses a simple shared
  byte port, not a guaranteed high-throughput banked SRAM architecture. The
  provided target frequency and default part are configurable assumptions.
- **Power report has low SAIF coverage:** inspect `annotation.rpt` and scope,
  use a matching netlist and simulation hierarchy, and validate post-route
  activity. Do not replace missing activity with an asserted measured result.
- **Instructor report rejected:** transfer the content into the exact required
  course template, which was not included with the supplied PDF. Rename your
  final submission using your own student number and full name.
