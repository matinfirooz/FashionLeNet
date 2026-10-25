# Verification and the scope of evidence

Run `python -m unittest discover -s tests -v`, then `python scripts/run_rtl.py`.
The first command tests software; the second compiles and simulates the actual
SystemVerilog source with Icarus. A missing simulator is an error, not a passing
test. Installing training dependencies enables the optional PyTorch tests.

| Module | Bench | Principal checks |
|---|---|---|
| `os_pe` | `tb_os_pe` | Signed extremes, dense/sparse equality, accumulator, stalls, valid forwarding, clear |
| `skew_buffer` | `tb_skew_buffer` | Per-lane token delays and validity under stalls |
| `os_array` | `tb_os_array` | Exact signed GEMM, masked edges, rectangular shape, drains, counters |
| `requantize` | `tb_requantize` | 51,392 cases across all shifts 0..31 and both ReLU modes |
| `pool2x2` | `tb_pool2x2` | Signed comparisons |
| `argmax10` | `tb_argmax10` | Ties, all -128, valid bubbles |
| `backing_store` | `tb_backing_store` | Host loading, exact latency, writes, held response |
| `read_cache` | `tb_read_cache` | Hit/miss/conflict, full refill, write invalidation, bypass, response hold, flush |
| `gemm_engine` | `tb_gemm_engine` | Multi-channel convolution, rectangular/tail tiles, bias, scaling, sparse counts |
| `pool_engine` | `tb_pool_engine` | Multi-channel signed pooling over a delayed memory interface |
| `lenet_core` | `tb_lenet_core` | All five layers, both pools, custom widths, all-zero inference and ties |
| `fpga_top` | `tb_fpga_top` | Host-loaded trained weights, every INT32 dot+bias result, every INT8 stage, logits and prediction |

`tb_fpga_top` compiles the selected bundle's `model_config.svh`, loads its entire
byte memory image through the host interface, and checks the actual memory after
each of seven stages. It also compares every pre-requantization INT32 result at
output writeback. This prevents saturation from hiding a wrong dot product.
The 32-input case checks 6,518 INT32 values and 8,094 INT8 stage values. The
28-input case checks 4,694 INT32 and 5,814 INT8 stage values.

The software oracle uses direct NumPy convolution and matrix multiplication,
not a Python copy of the PE implementation. Scalar convolution tests check its
indexing independently; FP32 tests compare it with PyTorch for both geometries.
The transaction timing model has its own cache/scheduler logic and checks exact
clock counts, MACs and cache events against simulated RTL reports.

Full-dataset test accuracy is measured with the independent integer reference.
The stored RTL logs prove selected full-image regressions, not a 10,000-image RTL
run or exhaustive/formal equivalence. The source and batch regression script
allow expanding this coverage. No post-route or on-board validation is implied.

`results/waveforms/os_pe.vcd` comes from the actual PE bench. Its SVG/PNG preview
is regenerated from the VCD, rather than drawn from an imagined waveform.
