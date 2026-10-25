#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from fashionlenet.sim import simulate_bundle

p=argparse.ArgumentParser()
p.add_argument("--bundle",default="examples/trained32")
p.add_argument("--cache",type=int,choices=[0,1],default=1)
p.add_argument("--sparse",type=int,choices=[0,1],default=1)
p.add_argument("--latency",type=int,default=4)
p.add_argument("--rows",type=int,default=5)
p.add_argument("--cols",type=int,default=5)
p.add_argument("--output",default="results/timing_model.json")
p.add_argument("--compare-rtl")
a=p.parse_args()
r=simulate_bundle(a.bundle,a.rows,a.cols,bool(a.cache),a.latency,bool(a.sparse))
if a.compare_rtl:
    actual=json.loads(Path(a.compare_rtl).read_text())
    keys=["cycles","mac_attempted","mac_executed","cache_hits","cache_misses","cache_bypasses"]
    for key in keys:
        if r[key]!=actual[key]:raise SystemExit(f"Model/RTL disagree on {key}: {r[key]} != {actual[key]}")
    r["validated_against_rtl"]=a.compare_rtl
Path(a.output).parent.mkdir(parents=True,exist_ok=True)
Path(a.output).write_text(json.dumps(r,indent=2)+"\n")
print(json.dumps(r,indent=2))
