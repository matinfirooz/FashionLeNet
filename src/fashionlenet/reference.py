"""Independent NumPy tensor implementation with a precise RTL arithmetic contract."""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def conv2d(x, w, bias):
    """NCHW, OIHW, valid cross-correlation. Integer inputs accumulate in int64."""
    kh, kw = w.shape[-2:]
    patches = sliding_window_view(x, (kh, kw), axis=(-2, -1))
    patches = patches.transpose(0, 2, 3, 1, 4, 5)
    shape = patches.shape
    cols = patches.reshape(-1, w.shape[1] * kh * kw)
    dtype = np.int64 if np.issubdtype(x.dtype, np.integer) else np.float32
    z = cols.astype(dtype) @ w.reshape(w.shape[0], -1).astype(dtype).T
    z += np.asarray(bias, dtype=dtype)
    return z.reshape(shape[0], shape[1], shape[2], w.shape[0]).transpose(0, 3, 1, 2)


def pool2d(x):
    n, c, h, w = x.shape
    if h % 2 or w % 2:
        raise ValueError("Pool requires even dimensions")
    return x.reshape(n, c, h // 2, 2, w // 2, 2).max(axis=(3, 5))


def requantize(acc, shift, relu):
    """Round nearest, ties away from zero; saturate signed INT8, optionally ReLU."""
    if not 0 <= int(shift) <= 31:
        raise ValueError("RTL supports right shifts 0..31")
    x = np.asarray(acc, dtype=np.int64)
    if np.any(x > 2147483647) or np.any(x < -2147483648):
        raise OverflowError("Accumulator exceeds RTL signed INT32 range")
    if shift:
        mag = (np.abs(x) + (1 << (shift - 1))) >> shift
        x = np.where(x < 0, -mag, mag)
    return np.clip(x, 0 if relu else -128, 127).astype(np.int8)


def infer(model, images, return_trace=False):
    """images are preprocessed floats or already signed INT8 NCHW."""
    x = np.asarray(images)
    if x.dtype != np.int8:
        x = np.clip(np.floor(x / model["input_scale"] + 0.5), 0, 127).astype(np.int8)
    if x.ndim == 3:
        x = x[None]
    traces = {"input": x.copy()}
    names = ["conv1", "conv2", "conv3", "fc1", "fc2"]
    for i, name in enumerate(names):
        layer = model["layers"][i]
        if i < 3:
            acc = conv2d(x, layer["weight"], layer["bias"])
        else:
            acc = x.reshape(x.shape[0], -1).astype(np.int64) @ layer["weight"].astype(np.int64).T
            acc += layer["bias"]
        traces[name + "_acc"] = acc.copy()
        x = requantize(acc, layer["shift"], i < 4)
        traces[name] = x.copy()
        if i < 2:
            x = pool2d(x)
            traces[f"pool{i+1}"] = x.copy()
    prediction = x.reshape(x.shape[0], 10).argmax(axis=1)
    return (prediction, x, traces) if return_trace else (prediction, x)


def float_infer(model, images):
    x = np.asarray(images, np.float32)
    for i, layer in enumerate(model["layers"]):
        if i < 3:
            x = conv2d(x, layer["weight"], layer["bias"])
        else:
            x = x.reshape(x.shape[0], -1) @ layer["weight"].T + layer["bias"]
        if i < 4:
            x = np.maximum(x, 0)
        if i < 2:
            x = pool2d(x)
    return x
