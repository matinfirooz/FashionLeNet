"""Official Fashion-MNIST IDX files, verified before use; no torchvision needed."""
from pathlib import Path
import gzip
import hashlib
import struct
import urllib.request
import numpy as np

FILES = {
    "train-images-idx3-ubyte.gz": "8d4fb7e6c68d591d4c3dfef9ec88bf0d",
    "train-labels-idx1-ubyte.gz": "25c81989df183df01b3e8a0aad5dffbe",
    "t10k-images-idx3-ubyte.gz": "bef4ecab320f06d8554ea6380940ec79",
    "t10k-labels-idx1-ubyte.gz": "bb300cfdad3c16e7a12a480ee83cd310",
}
BASE = "https://raw.githubusercontent.com/zalandoresearch/fashion-mnist/master/data/fashion/"
CLASSES = ["T-shirt/top", "Trouser", "Pullover", "Dress", "Coat", "Sandal", "Shirt", "Sneaker", "Bag", "Ankle boot"]


def load(root="data", train=True, download=False):
    root = Path(root)
    prefix = "train" if train else "t10k"
    names = [f"{prefix}-images-idx3-ubyte.gz", f"{prefix}-labels-idx1-ubyte.gz"]
    payloads = []
    for name in names:
        path = root / name
        if not path.exists():
            if not download:
                raise FileNotFoundError(f"{path}; run fashionlenet download --data {root}")
            root.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(BASE + name, timeout=90) as response:
                content = response.read()
            if hashlib.md5(content).hexdigest() != FILES[name]:
                raise ValueError(f"Checksum failed: {name}")
            path.write_bytes(content)
        content = path.read_bytes()
        if hashlib.md5(content).hexdigest() != FILES[name]:
            raise ValueError(f"Checksum failed: {path}; remove and download again")
        payloads.append(gzip.decompress(content))
    magic, n, h, w = struct.unpack(">IIII", payloads[0][:16])
    label_magic, nl = struct.unpack(">II", payloads[1][:8])
    if (magic, label_magic, h, w, n) != (2051, 2049, 28, 28, nl):
        raise ValueError("Unexpected IDX header")
    x = np.frombuffer(payloads[0], np.uint8, offset=16).reshape(n, 1, h, w).copy()
    y = np.frombuffer(payloads[1], np.uint8, offset=8).astype(np.int64)
    return x, y


def preprocess(images, input_size=32):
    x = np.asarray(images, dtype=np.float32) / 255.0
    if x.ndim == 3:
        x = x[None]
    if input_size == 32:
        x = np.pad(x, ((0, 0), (0, 0), (2, 2), (2, 2)))
    elif input_size != 28:
        raise ValueError("input_size must be 28 or 32")
    return x
