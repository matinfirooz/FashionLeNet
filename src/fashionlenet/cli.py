import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="FashionLeNet reproducible software-to-RTL flow")
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("download", help="Download and verify the four official Fashion-MNIST IDX files")
    d.add_argument("--data", default="data")
    t = sub.add_parser("train", help="Train FP32 with a held-out validation set")
    t.add_argument("--data", default="data")
    t.add_argument("--output", default="runs/baseline32")
    t.add_argument("--input-size", type=int, choices=[28,32], default=32)
    t.add_argument("--epochs", type=int, default=15)
    t.add_argument("--batch-size", type=int, default=128)
    t.add_argument("--lr", type=float, default=0.001)
    t.add_argument("--seed", type=int, default=42)
    t.add_argument("--threads", type=int, default=4)
    t.add_argument("--limit", type=int, default=0, help="Training subset size; zero means all 55000")
    q = sub.add_parser("quantize", help="Calibrate on training samples, save portable INT8 NPZ")
    q.add_argument("--checkpoint", required=True)
    q.add_argument("--data", default="data")
    q.add_argument("--output", default="runs/int8.npz")
    q.add_argument("--samples", type=int, default=500)
    q.add_argument("--threads", type=int, default=4)
    e = sub.add_parser("evaluate", help="Evaluate FP32 checkpoint or portable INT8 model on test split")
    e.add_argument("--model", required=True)
    e.add_argument("--data", default="data")
    e.add_argument("--limit", type=int, default=0)
    e.add_argument("--output", default="results/accuracy.json")
    p = sub.add_parser("prune", help="All prescribed sparsities, physical structural surgery, FP32 and PTQ")
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--data", default="data")
    p.add_argument("--output", default="runs/pruning")
    p.add_argument("--fractions", default="0.25,0.50,0.70,0.90,0.95,0.97,0.99")
    p.add_argument("--finetune-epochs", type=int, default=0)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--threads", type=int, default=4)
    ex = sub.add_parser("export", help="Generate host-loadable memory, RTL configuration, and golden traces")
    ex.add_argument("--model", required=True)
    ex.add_argument("--data", default="data")
    ex.add_argument("--index", type=int, default=0)
    ex.add_argument("--output", default="build/export")
    ex.add_argument("--synthetic", action="store_true")
    demo = sub.add_parser("demo", help="Deterministic offline, untrained fixture for arithmetic verification")
    demo.add_argument("--output", default="examples/demo")
    demo.add_argument("--seed", type=int, default=42)
    demo.add_argument("--input-size", type=int, choices=[28,32], default=32)
    bench = sub.add_parser("benchmark", help="Batch-one CPU latency with warm-up and percentiles")
    bench.add_argument("--checkpoint", required=True)
    bench.add_argument("--data", default="data")
    bench.add_argument("--output", default="results/cpu.json")
    bench.add_argument("--repeats", type=int, default=200)
    bench.add_argument("--threads", type=int, default=1)
    args = vars(parser.parse_args())
    cmd = args.pop("command")
    if cmd == "download":
        from .data import load
        for train in [True, False]:
            x,y = load(args["data"], train, True)
            print("train" if train else "test", x.shape, y.shape)
    elif cmd == "train":
        from .train import train
        train(**args)
    elif cmd == "quantize":
        import torch
        from .model import load_checkpoint
        from .data import load, preprocess
        from .quant import calibrate, save
        torch.set_num_threads(args["threads"])
        model,_ = load_checkpoint(args["checkpoint"])
        raw,_ = load(args["data"], True)
        # Fixed evenly spaced training indices, disjoint from the test set.
        import numpy as np
        n = args["samples"]
        if not 1 <= n <= len(raw):
            raise ValueError("samples must be 1..60000")
        ix = np.linspace(0, len(raw)-1, n, dtype=int)
        quant = calibrate(model, preprocess(raw[ix], model.input_size))
        save(quant, args["output"])
        print(json.dumps({"output":args["output"], "shifts":[l["shift"] for l in quant["layers"]]}))
    elif cmd == "evaluate":
        from .experiments import evaluate_file
        print(json.dumps(evaluate_file(**args), indent=2))
    elif cmd == "prune":
        from .experiments import pruning_sweep
        pruning_sweep(**args)
    elif cmd == "export":
        from .export import export_file
        export_file(**args)
    elif cmd == "demo":
        from .quant import demo_model, save
        from .export import export_bundle
        import numpy as np
        output = Path(args["output"])
        output.mkdir(parents=True, exist_ok=True)
        model = demo_model(args["seed"],args["input_size"])
        save(model,output/"model.npz")
        x = np.random.default_rng(args["seed"]+1).integers(0,128,(1,1,args["input_size"],args["input_size"]),dtype=np.int8)
        export_bundle(model,x,output,{"kind":"synthetic_untrained", "seed":args["seed"], "accuracy":None})
    elif cmd == "benchmark":
        from .experiments import benchmark
        print(json.dumps(benchmark(**args), indent=2))


if __name__ == "__main__":
    main()
