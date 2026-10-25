# FPGA flow

Default target: Artix-7 `xc7a200tfbg484-2`; edit it for your board/device.
The clock target is 100 MHz, **not a measured achieved clock**.

```bash
vivado -mode batch -source fpga/build_vivado.tcl -tclargs xc7a200tfbg484-2 10.0 baseline
vivado -mode batch -source fpga/generate_saif.tcl -tclargs examples/trained32 0 1
vivado -mode batch -source fpga/generate_saif.tcl -tclargs examples/trained32 1 1
vivado -mode batch -source fpga/power_from_saif.tcl -tclargs results/vivado/baseline/routed.dcp results/activity/s1_c1/inference.saif results/vivado/power_s1_c1
```

The supplied SAIF flow is behavioral simulation of real trained operands. For a
publication-quality power result, also run a separate post-route functional/timing
simulation using the exported netlist/SDF and a pin-level host driver. The RTL
testbench checks internal hierarchical signal names; these names can change in a
mapped netlist, so it is intentionally **not** a post-route bench. Check the
`read_saif` annotation coverage, clock, voltage, temperature, device, input activity,
and workload window. Repeat sparse modes on the same netlist and input. No watts
are inferred from MAC counts.

`generate_saif.tcl` uses the 10 ns testbench clock. Change its warm-up duration and
the testbench clock together if changing frequency. The benchmark excludes host
weight/image loading. Behavioral SAIF records an approximate compute window;
validate the window again if changing the host loader/reset sequence.

The memory is inferred byte-wide synchronous on-chip RAM with a response delay.
Four cycles describe the interface model, not a fixed BRAM primitive latency or
an external DRAM model. Placement, RAM inference, timing, and these Tcl scripts
require verification in your Vivado installation. No Vivado run is claimed here.

The default build is an out-of-context IP core. Board UART/AXI/PCIe, pins, clock
and reset crossing, and bitstream programming depend on a board and are external
to the portable core. Connect a synchronous host loader and respect `host_ready`.

For a 28x28 or structurally narrowed model, set synthesis generics from its exported
`model_config.svh`: `INPUT_SIZE`, `C1`, `C2`, `C3`, `F1`. For example, add
`-generic {INPUT_SIZE=28 C1=3 C2=8 C3=60 F1=42}` to `synth_design`.

References: [AMD UG900](https://docs.amd.com/r/en-US/ug900-vivado-logic-simulation/Generating-SAIF-Dumping),
[AMD UG907](https://www.amd.com/content/dam/xilinx/support/documents/sw_manuals/xilinx2021_1/ug907-vivado-power-analysis-optimization.pdf).
