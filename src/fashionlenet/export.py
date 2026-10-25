"""Single memory map shared by host loader, synthesizable RTL, and golden traces."""
from pathlib import Path
import json
import hashlib
import numpy as np
from . import reference

ACT_A, ACT_B, DEPTH = 65536, 73728, 81920


def write_hex(path, array, width=2):
    mask = (1 << (4*width)) - 1
    Path(path).write_text("".join(f"{int(x)&mask:0{width}x}\n" for x in np.asarray(array).reshape(-1)))


def export_bundle(model, image, output, provenance=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    size=model["input_size"]
    channels=model["channels"]
    if size not in (28,32) or len(channels)!=4 or min(channels)<1:
        raise ValueError("Unsupported input size or nonpositive layer width")
    c1,c2,c3,f1=channels
    p1=(size-4)//2;h2=p1-4;p2=h2//2
    footprints=[size*size,c1*(size-4)**2,c1*p1*p1,c2*h2*h2,c2*p2*p2,c3,f1,10]
    if max(footprints)>8192:
        raise ValueError("A layer activation does not fit an 8 KiB ping-pong bank")
    shapes=[(c1,1,5,5),(c2,c1,5,5),(c3,c2,p2,p2),(f1,c3),(10,f1)]
    if len(model["layers"])!=5:
        raise ValueError("Exactly five weighted layers are required")
    for layer,shape in zip(model["layers"],shapes):
        if layer["weight"].shape!=shape or layer["bias"].shape!=(shape[0],):
            raise ValueError("Model tensor dimensions disagree with exported configuration")
    for layer in model["layers"]:
        if not 0<=layer["shift"]<=31: raise ValueError("Requantization shift must be 0..31")
        w=layer["weight"].astype(np.int64).reshape(layer["weight"].shape[0],-1)
        if np.any(128*np.abs(w).sum(1)+np.abs(layer["bias"].astype(np.int64))>2**31-1):
            raise OverflowError("Model cannot guarantee INT32 accumulation for all INT8 inputs")
    prediction, logits, traces = reference.infer(model, image, True)
    if len(prediction)!=1:
        raise ValueError("Export exactly one image per bundle")
    weights = np.concatenate([l["weight"].ravel().view(np.uint8) for l in model["layers"]])
    biases = np.concatenate([l["bias"].astype("<i4").view(np.uint8).ravel() for l in model["layers"]])
    if len(weights)+len(biases)>65520:
        raise ValueError("Weights/biases do not fit 64 KiB parameter region")
    memory=np.zeros(DEPTH,np.uint8)
    memory[:len(weights)]=weights
    memory[len(weights):len(weights)+len(biases)]=biases
    memory[65520:65525]=[l["shift"] for l in model["layers"]]
    x=traces["input"].ravel().view(np.uint8)
    memory[ACT_A:ACT_A+len(x)]=x
    write_hex(output/"memory.hex",memory)
    write_hex(output/"expected_logits.hex",logits)
    for name, value in traces.items():
        write_hex(output/f"expected_{name}.hex", value,8 if name.endswith("_acc") else 2)
    stages=[]
    mcounts=[]
    h=model["input_size"]
    for i,l in enumerate(model["layers"]):
        k=int(np.prod(l["weight"].shape[1:]))
        if i<3:
            h=h-l["weight"].shape[-1]+1
            m=h*h
        else:
            m=1
        n=l["weight"].shape[0]
        mcounts.append(m*n*k)
        stages.append({"name":["conv1","conv2","conv3","fc1","fc2"][i],
                       "M":m,"N":n,"K":k,"MACs":m*n*k})
        if i<2:
            h//=2
    manifest={"input_size":model["input_size"],"channels":list(model["channels"]),
              "weight_bytes":len(weights),"bias_bytes":len(biases),
              "parameter_payload_bytes":len(weights)+len(biases)+5,
              "prediction":int(prediction[0]),"logits":logits.ravel().astype(int).tolist(),
              "dense_macs":sum(mcounts),"layers":stages,"provenance":provenance or {},
              "memory_sha256":hashlib.sha256(memory.tobytes()).hexdigest(),
              "arithmetic":"signed INT8, signed INT32 accumulation and bias; round ties away; saturating INT8"}
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    c1,c2,c3,f1=model["channels"]
    header=(f"`define INPUT_SIZE {model['input_size']}\n`define C1 {c1}\n`define C2 {c2}\n"
            f"`define C3 {c3}\n`define F1 {f1}\n`define EXPECTED_CLASS {int(prediction[0])}\n"
            f"`define EXPECTED_MACS {sum(mcounts)}\n")
    (output/"model_config.svh").write_text(header)
    print(json.dumps({"export":str(output),"prediction":int(prediction[0]),"dense_macs":sum(mcounts)}))
    return manifest


def export_file(model,data,index,output,synthetic=False):
    from .quant import load
    qmodel=load(model)
    if synthetic:
        image=np.random.default_rng(index).integers(0,128,(1,1,qmodel["input_size"],qmodel["input_size"]),dtype=np.int8)
        provenance={"kind":"synthetic_input", "seed":index, "accuracy":None}
    else:
        from .data import load as load_data,preprocess
        raw,labels=load_data(data,False)
        if not 0<=index<len(raw):
            raise ValueError("Test index outside dataset")
        image=preprocess(raw[index:index+1],qmodel["input_size"])
        provenance={"kind":"Fashion-MNIST_test", "index":index,"label":int(labels[index])}
    export_bundle(qmodel,image,output,provenance)
