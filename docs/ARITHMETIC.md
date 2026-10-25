# Bit-accurate arithmetic contract

## Floating-point network

Inputs are uint8 grayscale pixels divided by 255. The 32-input model pads two
zero pixels per side **before** entering Conv1. There is no mean/std normalization,
batch normalization, dropout, augmentation, tanh, or softmax in the inference path.
Weighted layers use biases. Conv1/2/3 and FC1 are followed by ReLU; max pooling
follows Conv1 and Conv2. Cross-entropy consumes FP32 logits during training.

## Symmetric power-of-two post-training quantization

The hardware uses signed INT8 for activations and weights and signed INT32 for
dot products and biases. All zero points are zero. Nonnegative inputs/ReLU outputs
use codes 0..127; weights use -127..127. The input scale is 2^-7. Inputs are
`clip(floor(x/scale+0.5),0,127)`, so a white pixel saturates at 127.

For each layer choose a weight scale `sw=2^ceil(log2(max(abs(w))/127))`. Calibration
observes the largest absolute FP32 layer output over 500 evenly spaced images
from the official 60,000-image training split. These are never test images.
The output scale `so` is the next power of two covering that output range, with
`so >= si*sw` to ensure a nonnegative shift. This is a hardware-friendly PTQ design
choice, not a claim to implement every affine quantization backend.

```text
qw = clip(round_ties_away(w / sw), -127, 127)
qb = round_ties_away(b / (si*sw))          # signed INT32
acc = sum(qx * qw) + qb                  # signed INT32
shift = log2(so / (si*sw))               # exact integer, 0..31
mag = (abs(acc) + 2^(shift-1)) >> shift  # if shift > 0
rounded = sign(acc) * mag               # shift 0 leaves acc unchanged
out = clip(rounded, 0, 127)              # ReLU layers
out = clip(rounded, -128, 127)           # final logits
```

For example, `acc=-5, shift=1` produces -3, not -2. Saturation follows rounding.
The RTL uses 33-bit magnitude arithmetic so `abs(-2147483648)` is representable.
The exporter checks a conservative per-output bound
`128*sum(abs(qw))+abs(qb) <= 2^31-1`, preventing dot-product/bias overflow for all
signed INT8 inputs. The NumPy reference accumulates in INT64, checks the INT32
boundary explicitly, and then implements the identical rounding/saturation rules.
This keeps the reference independent of accidental Python/HDL overflow behavior.

Pooling compares signed codes and preserves their scale. A final argmax over
equal-scale signed codes preserves their ordering; it can differ from FP32 when
quantization creates ties or saturation, which is included in measured accuracy.

## Serialization and size

An NPZ is a compressed portable container, not the accelerator's SRAM footprint.
The hardware payload is `sum(weight_count) + 4*sum(bias_count) + 5` bytes. JSON
calibration metadata and archive headers are excluded from this payload count.
`memory.hex` contains the full padded 80 KiB byte map for deterministic loading;
its textual file size is three bytes per byte plus no binary packing. Neither
that text size nor compressed ZIP size should be reported as model payload.

Unstructured pruning zeroes values without changing dense tensor shapes. Dense
storage stays constant. CSR estimates include one uint16 column index per nonzero,
one uint32 row pointer per output row plus terminal row pointer, biases and shifts.
The current RTL reads dense weights; CSR is an explicit storage estimate, not an
implemented compressed-memory interface.
