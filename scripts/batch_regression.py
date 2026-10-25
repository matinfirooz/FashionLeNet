#!/usr/bin/env python3
"""Expand full-network RTL coverage with real test images. Requires local dataset."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument("--model",default="results/trained32/int8.npz")
p.add_argument("--data",default="data")
p.add_argument("--indices",default="0,1,2,8",help="Comma-separated test indices")
p.add_argument("--output",default="build/regression")
a=p.parse_args()
os.chdir(root)
env=os.environ.copy();env["PYTHONPATH"]=str(root/"src")+os.pathsep+env.get("PYTHONPATH","")
out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
records=[]
for index in [int(v) for v in a.indices.split(",")]:
    bundle=out/f"image_{index:05d}"
    subprocess.run([sys.executable,"-m","fashionlenet.cli","export","--model",a.model,"--data",a.data,
                    "--index",str(index),"--output",str(bundle)],check=True,env=env)
    subprocess.run([sys.executable,"scripts/run_rtl.py","--full","--bundle",str(bundle),"--output",str(out/"logs")],check=True,env=env)
    records.append({"index":index,"status":"PASS","bundle":str(bundle)})
(out/"summary.json").write_text(json.dumps(records,indent=2)+"\n")
