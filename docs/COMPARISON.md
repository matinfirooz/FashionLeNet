# CPU, FPGA, and ShiDianNao: reporting compatible quantities

The design follows an output-stationary principle associated with accelerators
such as ShiDianNao; it does not reproduce its complete NFU, sensor interface,
technology, memory system, or workloads. Read the original publication before
copying a number into a comparison table:

- Zidong Du et al., **ShiDianNao: Shifting Vision Processing Closer to the Sensor**,
  ISCA 2015, [publisher DOI](https://doi.org/10.1145/2749469.2750389).
- [Author/institution publication record](https://infoscience.epfl.ch/entities/publication/d4885b73-976c-4a11-9967-2d0871bb9fc2).
- [ISCA retrospective by the authors](https://sites.coecis.cornell.edu/isca50retrospective/files/2023/06/Du_2015_ShiDianNao_v2.pdf).

| Dimension | This release | Information required for a fair comparison |
|---|---|---|
| Implementation | Portable FPGA RTL; generic Yosys checks | ShiDianNao ASIC implementation conditions |
| Model/data | Specified LeNet ReLU/max-pool variant; Fashion-MNIST | Identical layer shapes and dataset, or clear workload mismatch |
| Arithmetic | Signed INT8 / INT32; documented rounding | Published operand/accumulator formats |
| Clock | 100 MHz target only | Measured routed/on-board clock and published clock |
| Latency | Actual RTL clocks, excluding host loading | Inference latency with identical boundaries |
| Memory | On-chip byte port; 1 KiB direct cache option | Memory capacities, port widths, off-chip traffic, bandwidth |
| Power | Not measured; SAIF/Vivado scripts included | Voltage, temperature, process, activity, static/dynamic breakdown |
| CPU | Local batch-one FP32 timing with metadata | Rerun same command in Colab as required by the brief |

For a measured achieved frequency `f_Hz` and simulated `C` clocks,
`latency_seconds=C/f_Hz`, and sequential throughput is `f_Hz/C` images/s. A
frequency target yields only a conditional estimate. `CPU_time/FPGA_time` is a
speed ratio and can be below one. Do not multiply by an unrelated published
speedup to obtain your design's speedup. At the conditional 100 MHz target, the
byte-serial implementation is slower than the measured local CPU; this is a
documented bottleneck rather than a hidden result.

Dynamic power and total on-chip power are different. If measured power in mW
and inference latency in ms are available, energy is `power_mW*latency_ms` in
microjoules. Use actual activity and time windows, and report whether host traffic
and static power are included. FPGA-versus-ASIC watts alone do not isolate an
architectural improvement. The report leaves the ShiDianNao numeric fields and
unmeasured FPGA metrics empty rather than substituting incomparable numbers.
