# Mapping the supplied brief to this repository

The original Persian brief is preserved in [docs/spec/HWACC-Project-2025.pdf](spec/HWACC-Project-2025.pdf).
This is an independent implementation of the course project, not a reproduction of
the complete ShiDianNao chip. No unpublished course code is assumed.

| Requirement | Implementation | Evidence / reproduction |
|---|---|---|
| Train LeNet on Fashion-MNIST | `model.py`, `train.py`, checksum-verified IDX reader | Both 28 and 32 input checkpoints, histories and test matrices |
| 25, 50, 70, 90, 95, 97, 99% unstructured pruning | Global smallest-magnitude masks; biases retained | `results/pruning28/summary.csv`, all models |
| Same levels of structured pruning | L2 ranking, actual channel/neuron removal and dependent input slicing | Same CSV; changed checkpoint shapes and physical parameter counts |
| Parameter count and model size | Stored/nonzero counts, dense FP32/INT8 bytes and CSR estimates | `pruning.statistics`; metadata versus payload is distinguished |
| INT8 PTQ without retraining | 500 calibration images from official training split; symmetric power-of-two scales | Portable INT8 NPZ models; independent integer test evaluation |
| Pruning followed by PTQ | Separate calibration for each pruned model | Every pruning row contains FP32 and INT8 accuracy |
| Recovery study | Fixed three-epoch training-only fine-tuning at 50% | `results/finetuned28/`; no test-based checkpoint selection |
| Five weighted layers, output-stationary array | Three convolutions, two dense layers, two max pools and argmax | `rtl/lenet_core.sv`, `rtl/gemm_engine.sv`, full INT32/INT8 trace checking |
| Single-level memory baseline | L1 bypass, backing latency one clock | RTL log and counter report for `s0_c0_l1` |
| Optional unstructured sparsity support | Valid-preserving zero checks, multiplier operand isolation, accumulator enable | Dense/sparse equality; exact executed-MAC counters |
| Two-level memory | 1 KiB direct-mapped cache, 16-byte lines, four-cycle backing response | Tag/conflict/refill/write/bypass test; full cached inference |
| Memory policies/controller | Write-through, no write allocation, index invalidation, demand refill FSM | `read_cache.sv`, `MEMORY_MAP.md` |
| Compare inference latency | Measured RTL clocks; exact transaction model | RTL and model agreement on clocks and cache counters |
| FPGA LUT/FF/DSP/BRAM, timing and power | Vivado synthesis/place/route, SAIF import and report scripts | Pending execution in Vivado; null fields in `fpga_status.json` |
| CPU baseline / speedup | Batch-one PyTorch timer, warm-up, percentiles, thread metadata | Measured local CPU result; notebook supports rerun in Colab |
| ShiDianNao comparison | Methodology table and source links | `COMPARISON.md`; no invented cross-platform speedup/power |
| Course submission report | Detailed Markdown report and source evidence | Transfer into the instructor's required report template |

## Ambiguities resolved explicitly

1. **Input geometry.** The table specifies 32x32 hardware input. Hardware therefore
   uses valid 5x5 Conv1, pool, valid 5x5 Conv2, pool, valid 5x5 Conv3. The software
   optimization variant uses native 28x28 input and a 4x4 Conv3 after the second
   pool. This is equivalent to a 256-to-120 dense transform; it keeps five weighted
   layers and makes both variants executable with the same engine. They are
   separately trained and reported; their accuracies are not interchangeable.
2. **The table's Input row.** It shows 32x32 on the input side and 28x28 on the
   output side. We treat 32x32 as the tensor entering Conv1; Conv1 produces 28x28.
3. **WS versus OS wording.** The implementation follows the final requested
   output-stationary dataflow. Sums remain in each PE through the full reduction.
4. **Direct mapping versus LRU.** A direct-mapped cache has one candidate line per
   index. No LRU state is required or meaningful. Index/tag replacement is used.
5. **Nonlinearities.** The brief does not fix a bit-accurate activation or pooling
   formula. We choose ReLU and 2x2 max pool, document them, and train accordingly.
   This is a modern LeNet variant rather than the original 1998 tanh/average-pool
   network with partially connected C3 and RBF outputs.
6. **Sparsity and speed.** Zero gating removes executed MACs, not memory requests
   or valid time slots. There are no compressed operand streams or hidden cycle
   savings in the baseline. All memory and throughput claims reflect this.
7. **Report format.** The required instructor report template was not attached.
   A substantive report is included; it cannot honestly be labeled as that template.
