"""Transaction-level model of the RTL scheduler/cache, including refill traffic.

Timing is derived from the implemented ready/valid FSM, not peak array throughput.
It models clocks only; it does not estimate physical timing or watts.
"""
from pathlib import Path
import json
import numpy as np


class Memory:
    def __init__(self, contents, cache=True, latency=4):
        self.contents=np.asarray(contents,np.uint8).copy()
        self.cache=cache
        self.latency=latency
        self.tags=[None]*64
        self.lines=np.zeros((64,16),np.uint8)
        self.cycles=self.hits=self.misses=self.bypasses=self.reads=self.writes=self.l2_reads=0

    def read(self,address):
        address=int(address)
        self.reads+=1
        if not self.cache:
            self.cycles+=self.latency+4;self.bypasses+=1;self.l2_reads+=1
            return int(self.contents[address])
        index=(address>>4)&63;tag=address>>10;offset=address&15
        if self.tags[index]==tag:
            self.hits+=1;self.cycles+=2
        else:
            self.misses+=1;self.l2_reads+=16
            self.cycles+=2+16*(self.latency+2)
            base=address&~15
            self.lines[index]=self.contents[base:base+16]
            self.tags[index]=tag
        return int(self.lines[index,offset])

    def write(self,address,value):
        self.writes+=1;self.cycles+=self.latency+4
        self.contents[address]=int(value)&255
        self.tags[(address>>4)&63]=None


def signed(value):
    return value-256 if value>=128 else value


def simulate_bundle(bundle, rows=5, cols=5, cache=True, latency=4, sparse=True):
    bundle=Path(bundle)
    manifest=json.loads((bundle/"manifest.json").read_text())
    memory=Memory([int(v,16) for v in (bundle/"memory.hex").read_text().split()],cache,latency)
    h=manifest["input_size"]
    c1,c2,c3,f1=manifest["channels"]
    p1=(h-4)//2;h2=p1-4;p2=h2//2
    shapes=[(h,h,1,c1,5),(p1,p1,c1,c2,5),(p2,p2,c2,c3,p2),(1,1,c3,f1,1),(1,1,f1,10,1)]
    total_weights=manifest["weight_bytes"]
    wb=0;bb=total_weights
    extra=0;attempts=executed=0;phases=[]
    for layer,(ih,iw,ci,co,ks) in enumerate(shapes):
        name=["conv1","conv2","conv3","fc1","fc2"][layer]
        oh=ih-ks+1;ow=iw-ks+1;M=oh*ow;K=ci*ks*ks
        ib=73728 if layer==3 else 65536
        ob=65536 if layer==3 else 73728
        gold=[int(v,16) for v in (bundle/f"expected_{name}.hex").read_text().split()]
        begin=memory.cycles+extra
        memory.read(65520+layer)
        layer_attempts=layer_executed=0
        for m0 in range(0,M,rows):
            for n0 in range(0,co,cols):
                extra+=1 # CLEAR
                for k in range(K):
                    aa=[];bb_values=[]
                    ic=k//(ks*ks);ky=(k//ks)%ks;kx=k%ks
                    for r in range(rows):
                        if m0+r<M:
                            m=m0+r
                            a=memory.read(ib+ic*ih*iw+(m//ow+ky)*iw+m%ow+kx)
                            aa.append(signed(a))
                        else:extra+=1
                    for c in range(cols):
                        if n0+c<co:bb_values.append(signed(memory.read(wb+(n0+c)*K+k)))
                        else:extra+=1
                    layer_attempts+=len(aa)*len(bb_values)
                    layer_executed+=sum(a!=0 for a in aa)*sum(b!=0 for b in bb_values) if sparse else len(aa)*len(bb_values)
                    extra+=1 # FEED
                extra+=rows+cols-2 # Drain skew/network
                for r in range(min(rows,M-m0)):
                    for c in range(min(cols,co-n0)):
                        for byte in range(4):memory.read(bb+4*(n0+c)+byte)
                        address=(n0+c)*M+m0+r
                        memory.write(ob+address,gold[address])
        extra+=2 # GSTART and GWAIT observing the done pulse
        phases.append({"phase":name,"cycles":memory.cycles+extra-begin,"MACs":layer_attempts,
                       "executed_MACs":layer_executed})
        attempts+=layer_attempts;executed+=layer_executed
        if layer<2:
            begin=memory.cycles+extra
            pgold=[int(v,16) for v in (bundle/f"expected_pool{layer+1}.hex").read_text().split()]
            for ch in range(co):
                for y in range(oh//2):
                    for x in range(ow//2):
                        for sample in range(4):
                            memory.read(ob+ch*oh*ow+(2*y+sample//2)*ow+2*x+sample%2)
                        pos=ch*(oh//2)*(ow//2)+y*(ow//2)+x
                        memory.write(65536+pos,pgold[pos])
            extra+=2
            phases.append({"phase":f"pool{layer+1}","cycles":memory.cycles+extra-begin,"MACs":0,"executed_MACs":0})
        wb+=co*K;bb+=co*4
    for c in range(10):memory.read(73728+c)
    extra+=2 # ARG_START, ARG_DONE
    return {"kind":"transaction_level_model", "bundle":str(bundle),"rows":rows,"cols":cols,
            "cache":int(cache),"sparse":int(sparse),"l2_latency":latency,
            "cycles":memory.cycles+extra,"mac_attempted":attempts,"mac_executed":executed,
            "cache_hits":memory.hits,"cache_misses":memory.misses,"cache_bypasses":memory.bypasses,
            "logical_reads":memory.reads,"logical_writes":memory.writes,
            "l2_byte_reads":memory.l2_reads,"l2_byte_writes":memory.writes,"phases":phases}
