"""Deterministic train/validation split and best-validation checkpoint selection."""
from pathlib import Path
import json
import platform
import time
import numpy as np
import torch
from .data import load, preprocess
from .model import LeNet, save_checkpoint


def evaluate(model, x, y, batch_size=256):
    model.eval()
    correct = 0
    with torch.inference_mode():
        for start in range(0, len(y), batch_size):
            logits = model(torch.from_numpy(x[start:start+batch_size]))
            correct += int((logits.argmax(1).numpy() == y[start:start+batch_size]).sum())
    return correct / len(y)


def train(data, output, input_size=32, epochs=15, batch_size=128, lr=0.001, seed=42,
          threads=4, limit=0, channels=(6, 16, 120, 84)):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(threads)
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.use_deterministic_algorithms(True)
    raw, labels = load(data, True)
    permutation = np.random.default_rng(seed).permutation(len(labels))
    vi, ti = permutation[:5000], permutation[5000:]
    if limit:
        ti = ti[:limit]
    x, vx = preprocess(raw[ti], input_size), preprocess(raw[vi], input_size)
    y, vy = labels[ti], labels[vi]
    model = LeNet(input_size, channels)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, epochs)
    generator = torch.Generator().manual_seed(seed)
    history, best = [], -1
    for epoch in range(epochs):
        model.train()
        order = torch.randperm(len(y), generator=generator).numpy()
        loss_sum, correct = 0.0, 0
        begin = time.perf_counter()
        for start in range(0, len(y), batch_size):
            ix = order[start:start+batch_size]
            xb, yb = torch.from_numpy(x[ix]), torch.from_numpy(y[ix])
            optimizer.zero_grad(set_to_none=True)
            logits = model(xb)
            loss = torch.nn.functional.cross_entropy(logits, yb)
            loss.backward()
            optimizer.step()
            loss_sum += float(loss.detach()) * len(ix)
            correct += int((logits.detach().argmax(1) == yb).sum())
        val = evaluate(model, vx, vy)
        row = {"epoch": epoch+1, "train_loss": loss_sum/len(y), "train_accuracy": correct/len(y),
               "validation_accuracy": val, "seconds": time.perf_counter()-begin}
        history.append(row)
        print(json.dumps(row), flush=True)
        if val > best:
            best = val
            save_checkpoint(model, output/"best.pt", seed=seed, epoch=epoch+1,
                            validation_accuracy=val, training_samples=len(y), validation_samples=len(vy),
                            split="seeded permutation: first 5000 validation, remaining training")
        scheduler.step()
        (output/"history.json").write_text(json.dumps(history, indent=2)+"\n")
    manifest = {"seed": seed, "epochs": epochs, "batch_size": batch_size, "lr": lr,
                "threads": threads, "torch": torch.__version__, "python": platform.python_version(),
                "input_size": input_size, "channels": channels, "training_samples": len(y),
                "best_validation_accuracy": best, "test_used_for_selection": False}
    (output/"training_manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    return manifest
