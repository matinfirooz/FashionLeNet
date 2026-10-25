"""Global unstructured masks and physical, dependency-aware structural removal."""
import copy
import numpy as np
import torch
from .model import LeNet


def unstructured(model, fraction):
    if not 0 <= fraction < 1:
        raise ValueError("fraction must be in [0,1)")
    result=copy.deepcopy(model)
    layers=result.weighted_layers()
    flat=torch.cat([l.weight.detach().abs().flatten() for l in layers])
    count=int(np.floor(fraction*flat.numel()))
    # Stable argsort makes equal-magnitude ties deterministic and gives exact counts.
    order=torch.argsort(flat,stable=True)
    keep=torch.ones(flat.numel(),dtype=torch.bool)
    keep[order[:count]]=False
    masks=[]
    offset=0
    with torch.no_grad():
        for layer in layers:
            mask=keep[offset:offset+layer.weight.numel()].reshape_as(layer.weight)
            layer.weight.mul_(mask)
            masks.append(mask)
            offset+=layer.weight.numel()
    return result,masks


def structured(model, fraction):
    """Remove output channels/hidden neurons, propagate indices, retain ten labels."""
    if not 0 <= fraction < 1:
        raise ValueError("fraction must be in [0,1)")
    old=model.weighted_layers()
    selections=[]
    for layer in old[:-1]:
        norms=layer.weight.detach().flatten(1).square().sum(1)
        n=max(1,int(np.ceil(round(layer.weight.shape[0]*(1-fraction),12))))
        # Sort selected indices into original order to simplify inter-layer surgery.
        selections.append(torch.argsort(norms,descending=True,stable=True)[:n].sort().values)
    result=LeNet(model.input_size,tuple(len(ix) for ix in selections))
    previous=torch.tensor([0])
    with torch.no_grad():
        for i,(src,dst) in enumerate(zip(old,result.weighted_layers())):
            current=selections[i] if i<4 else torch.arange(10)
            dst.weight.copy_(src.weight[current][:,previous])
            dst.bias.copy_(src.bias[current])
            previous=current
    return result.eval()


def statistics(model):
    layers=model.weighted_layers()
    weights=sum(l.weight.numel() for l in layers)
    nz=sum(int(torch.count_nonzero(l.weight)) for l in layers)
    biases=sum(l.bias.numel() for l in layers)
    # CSR payload estimate per flattened output row: values f32 + index u16 + rowptr u32.
    csr_fp32=nz*6+sum((l.weight.shape[0]+1)*4 for l in layers)+biases*4
    csr_int8=nz*3+sum((l.weight.shape[0]+1)*4 for l in layers)+biases*4+5
    return {"stored_parameters":weights+biases,"weight_parameters":weights,"nonzero_weights":nz,
            "weight_sparsity":1-nz/weights,"fp32_dense_payload_bytes":4*(weights+biases),
            "int8_dense_payload_bytes":weights+4*biases+5,
            "csr_fp32_estimate_bytes":csr_fp32,"csr_int8_estimate_bytes":csr_int8,
            "channels":list(model.channels)}
