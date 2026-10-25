"""Post-training symmetric power-of-two INT8 calibration and portable NPZ format."""
from pathlib import Path
import json
import numpy as np


def pot_scale(maximum):
    maximum = max(float(maximum), 1e-12)
    return float(2.0 ** np.ceil(np.log2(maximum / 127.0)))


def round_away(x):
    x = np.asarray(x)
    return np.sign(x) * np.floor(np.abs(x) + 0.5)


def calibrate(model, images):
    """Use training/validation images, never the held-out test set."""
    import torch
    images = np.asarray(images)
    if not len(images):
        raise ValueError("Calibration requires images")
    maxima = np.zeros(5)
    model.eval()
    with torch.inference_mode():
        for offset in range(0, len(images), 64):
            values = model.intermediates(torch.from_numpy(images[offset:offset+64]))
            maxima = np.maximum(maxima, [float(v.abs().max()) for v in values])
    input_scale = 1 / 128
    inscale = input_scale
    layers = []
    for i, layer in enumerate(model.weighted_layers()):
        w = layer.weight.detach().cpu().numpy()
        b = layer.bias.detach().cpu().numpy()
        ws = pot_scale(np.abs(w).max())
        # A positive shift is required by the hardware's right-shift-only datapath.
        oscale = max(pot_scale(maxima[i]), inscale * ws)
        shift = int(round(np.log2(oscale / (inscale * ws))))
        if shift > 31:
            raise ValueError("Calibration shift exceeds 31")
        bq = round_away(b / (inscale * ws))
        if np.any(np.abs(bq) > 2**31 - 1):
            raise OverflowError("Quantized bias overflows INT32")
        wq=np.clip(round_away(w / ws), -127, 127).astype(np.int8)
        bound=128*np.abs(wq.astype(np.int64)).reshape(wq.shape[0],-1).sum(1)+np.abs(bq)
        if np.any(bound>2**31-1):
            raise OverflowError("Worst-case dot-product plus bias exceeds INT32")
        layers.append({"weight": wq,
                       "bias": bq.astype(np.int32), "shift": shift,
                       "weight_scale": ws, "output_scale": oscale})
        inscale = oscale
    return {"input_size": model.input_size, "channels": model.channels,
            "input_scale": input_scale, "layers": layers,
            "calibration_samples": len(images), "calibration_maxima": maxima.tolist()}


def save(model, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {k: v for k, v in model.items() if k != "layers"}
    metadata["layers"] = [{k: v for k, v in l.items() if k not in ("weight", "bias")} for l in model["layers"]]
    arrays = {f"w{i}": l["weight"] for i, l in enumerate(model["layers"])}
    arrays.update({f"b{i}": l["bias"] for i, l in enumerate(model["layers"])})
    np.savez_compressed(path, metadata=np.array(json.dumps(metadata)), **arrays)


def load(path):
    with np.load(path, allow_pickle=False) as archive:
        model = json.loads(str(archive["metadata"]))
        for i, layer in enumerate(model["layers"]):
            layer.update(weight=archive[f"w{i}"].copy(), bias=archive[f"b{i}"].copy())
    return model


def demo_model(seed=42, input_size=32, channels=(6, 16, 120, 84), sparsity=0.7):
    """Untrained deterministic integer fixture; never an accuracy benchmark."""
    rng = np.random.default_rng(seed)
    c1, c2, c3, f1 = channels
    shapes = [(c1, 1, 5, 5), (c2, c1, 5, 5),
              (c3, c2, 5 if input_size == 32 else 4, 5 if input_size == 32 else 4),
              (f1, c3), (10, f1)]
    layers = []
    for shape in shapes:
        w = rng.integers(-8, 9, size=shape, dtype=np.int8)
        w[rng.random(shape) < sparsity] = 0
        layers.append({"weight": w, "bias": rng.integers(-64, 65, shape[0], dtype=np.int32),
                       "shift": 5, "weight_scale": 1/32, "output_scale": 1/128})
    return {"input_size": input_size, "channels": channels, "input_scale": 1/128,
            "layers": layers, "provenance": "synthetic untrained arithmetic fixture", "seed": seed}
