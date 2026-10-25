from pathlib import Path
import json
import csv
import time
import platform
import numpy as np
from .data import load,preprocess


def evaluate_file(model,data,limit=0,output="results/accuracy.json"):
    raw,y=load(data,False)
    if limit:
        raw,y=raw[:limit],y[:limit]
    if str(model).endswith(".npz"):
        from .quant import load as load_quant
        from .reference import infer
        q=load_quant(model)
        x=preprocess(raw,q["input_size"])
        predictions=[]
        for start in range(0,len(y),64):
            predictions.extend(infer(q,x[start:start+64])[0].tolist())
        kind="numpy_integer_reference"
    else:
        import torch
        from .model import load_checkpoint
        torch.set_num_threads(4)
        net,_=load_checkpoint(model)
        x=preprocess(raw,net.input_size)
        with torch.inference_mode():
            predictions=np.concatenate([net(torch.from_numpy(x[i:i+256])).argmax(1).numpy()
                                        for i in range(0,len(y),256)])
        kind="pytorch_fp32"
    predictions=np.asarray(predictions)
    confusion=np.zeros((10,10),dtype=int)
    np.add.at(confusion,(y,predictions),1)
    result={"model":str(model),"split":"official_test", "samples":len(y),
            "accuracy":float(np.mean(y==predictions)),"engine":kind,"confusion_matrix":confusion.tolist()}
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(result,indent=2)+"\n")
    return result


def pruning_sweep(checkpoint,data,output,fractions,finetune_epochs=0,limit=0,threads=4):
    import torch
    from .model import load_checkpoint,save_checkpoint
    from .pruning import unstructured,structured,statistics
    from .quant import calibrate,save
    from .train import evaluate
    torch.set_num_threads(threads)
    torch.manual_seed(42)
    model,_=load_checkpoint(checkpoint)
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    raw,y=load(data,False)
    if limit: raw,y=raw[:limit],y[:limit]
    x=preprocess(raw,model.input_size)
    train_raw,train_labels=load(data,True)
    cal=preprocess(train_raw[np.linspace(0,len(train_raw)-1,500,dtype=int)],model.input_size)
    ix=np.random.default_rng(42).permutation(len(train_labels))[5000:]
    tx,ty=preprocess(train_raw[ix],model.input_size),train_labels[ix]
    rows=[]
    cases=[("baseline",0.0)]+[(method,float(f)) for method in ["unstructured","structured"] for f in fractions.split(",")]
    for method,fraction in cases:
        masks=None
        if method=="unstructured": net,masks=unstructured(model,fraction)
        elif method=="structured": net=structured(model,fraction)
        else: net=model
        before=evaluate(net,x,y)
        if finetune_epochs and method!="baseline":
            opt=torch.optim.Adam(net.parameters(),lr=1e-4)
            for epoch in range(finetune_epochs):
                net.train()
                order=np.random.default_rng(42+epoch).permutation(len(ty))
                for start in range(0,len(ty),128):
                    b=order[start:start+128]
                    opt.zero_grad(set_to_none=True)
                    loss=torch.nn.functional.cross_entropy(net(torch.from_numpy(tx[b])),torch.from_numpy(ty[b]))
                    loss.backward()
                    if masks:
                        for l,mask in zip(net.weighted_layers(),masks): l.weight.grad.mul_(mask)
                    opt.step()
                    if masks:
                        with torch.no_grad():
                            for l,mask in zip(net.weighted_layers(),masks): l.weight.mul_(mask)
        net.eval()
        stem=f"{method}_{fraction:.2f}"
        performed_epochs=finetune_epochs if method!="baseline" else 0
        save_checkpoint(net,output/f"{stem}.pt",method=method,target_fraction=fraction,finetune_epochs=performed_epochs)
        q=calibrate(net,cal)
        save(q,output/f"{stem}.npz")
        # Integer test uses the independent portable reference, not fake quantization.
        result=evaluate_file(str(output/f"{stem}.npz"),data,limit,str(output/f"{stem}_test.json"))
        row={"method":method,"target_fraction":fraction,"accuracy_before_finetune":before,
             "fp32_accuracy":evaluate(net,x,y),"int8_accuracy":result["accuracy"],
             "test_samples":len(y),"finetune_epochs":performed_epochs,**statistics(net)}
        rows.append(row)
        print(json.dumps(row),flush=True)
        (output/"summary.json").write_text(json.dumps(rows,indent=2)+"\n")
    with (output/"summary.csv").open("w",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    return rows


def benchmark(checkpoint,data,output,repeats=200,threads=1):
    import torch
    from .model import load_checkpoint
    torch.set_num_threads(threads)
    net,_=load_checkpoint(checkpoint)
    raw,_=load(data,False)
    x=torch.from_numpy(preprocess(raw[:1],net.input_size))
    samples=[]
    with torch.inference_mode():
        for _ in range(30): net(x)
        for _ in range(repeats):
            begin=time.perf_counter_ns();net(x);samples.append((time.perf_counter_ns()-begin)/1e6)
    result={"engine":"PyTorch FP32 CPU", "batch_size":1,"threads":threads,"warmup":30,
            "repeats":repeats,"median_ms":float(np.median(samples)),"p05_ms":float(np.percentile(samples,5)),
            "p95_ms":float(np.percentile(samples,95)),"machine":platform.machine(),
            "processor":platform.processor(),"platform":platform.platform(),"torch":torch.__version__,
            "includes_preprocessing":False,"samples_ms":samples}
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(result,indent=2)+"\n")
    return result
