# FashionLeNet hardware schematics

The six hardware figures are drawn as editable RTL schematics with register
clock symbols, muxes, arithmetic operators, memory structures, bus widths and
control wiring. SVG is the editable vector source; PNG is a rendered companion.
All figures refer to the existing implementation, without adding pipeline stages
or changing the RTL. Thick dark wires carry data; thin teal wires carry controls.
A filled junction dot indicates a branch. Crossings without a dot do not connect.

| Hardware figure | Source RTL in the main project |
|---|---|
| architecture | fpga_top.sv, lenet_core.sv, gemm_engine.sv |
| processing_element | os_pe.sv |
| systolic_array | skew_buffer.sv, os_array.sv |
| memory_hierarchy | read_cache.sv, backing_store.sv |
| postprocess_datapath | gemm_engine.sv, requantize.sv |
| controller_fsm | lenet_core.sv |

The array's 9-bit link is an 8-bit signed operand bundled with one valid bit.
Its input skew lane i has i register stages. Registers advance only on `step`.
Sums remain local in the PEs. The memory drawing separates tag match from the
controller's read/bypass policy. A write invalidates the indexed cache line.
The output drawing shows a combinational requantizer; the bias and shift
registers are actual state, not additional arithmetic pipeline stages.

## Rebuild

From the complete project:

```bash
python -m pip install -r requirements-figures.txt
python scripts/hardware_figures.py --package
python scripts/make_figures.py
```

From the standalone hardware-figure ZIP:

```bash
python -m pip install -r requirements.txt
python source/hardware_figures.py
```

Standalone regeneration writes to `docs/figures/` below the extracted folder.
CairoSVG requires a working Cairo installation; Ubuntu/WSL can install
`libcairo2` using its package manager. The supplied SVGs can also be opened
in a browser or vector editor without Python. Text remains editable.

## Other figures in the complete project

The network geometry, measured training/pruning/recovery results, RTL counters,
confusion matrix, analytic systolic schedule, and measured PE waveform retain
their SVG/PNG companions. The measured plots use saved experiment results;
the schedule is explicitly analytic, and the waveform is parsed from the VCD.
