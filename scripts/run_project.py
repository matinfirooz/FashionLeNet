#!/usr/bin/env python3
"""Cross-platform orchestration. No implicit success when a requested tool is missing."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--profile",choices=["offline","verify","full"],default="offline")
    p.add_argument("--software-only",action="store_true",help="Explicitly omit RTL; do not claim hardware validation")
    p.add_argument("--data",default="data")
    a=p.parse_args()
    os.chdir(ROOT)
    env=os.environ.copy()
    env["PYTHONPATH"]=str(ROOT/"src")+os.pathsep+env.get("PYTHONPATH","")
    def run(*args):
        print("\n+ "+" ".join(args),flush=True)
        subprocess.run([sys.executable,*args],env=env,check=True)
    def cli(*args):run("-m","fashionlenet.cli",*args)
    if a.profile=="full":
        cli("download","--data",a.data)
        for size in [32,28]:
            config=json.loads((ROOT/f"configs/baseline{size}.json").read_text())
            params=[]
            for key,value in config.items():params += ["--"+key.replace("_","-"),str(value)]
            cli("train","--data",a.data,*params)
            folder=f"results/trained{size}"
            cli("quantize","--checkpoint",f"{folder}/best.pt","--data",a.data,"--output",f"{folder}/int8.npz")
            for model,out in [("best.pt","fp32_test.json"),("int8.npz","int8_test.json")]:
                cli("evaluate","--model",f"{folder}/{model}","--data",a.data,"--output",f"{folder}/{out}")
            cli("export","--model",f"{folder}/int8.npz","--data",a.data,"--output",f"examples/trained{size}")
        cli("prune","--checkpoint","results/trained28/best.pt","--data",a.data,"--output","results/pruning28")
        cli("prune","--checkpoint","results/trained28/best.pt","--data",a.data,"--output","results/finetuned28",
            "--fractions","0.50","--finetune-epochs","3")
        for method,folder in [("structured","structured28"),("unstructured","pruned28")]:
            cli("export","--model",f"results/finetuned28/{method}_0.50.npz","--data",a.data,"--output",f"examples/{folder}")
        cli("benchmark","--checkpoint","results/trained32/best.pt","--data",a.data,"--output","results/cpu_baseline32.json")
    if a.profile=="offline":cli("demo")
    run("-m","unittest","discover","-s","tests","-v")
    if not a.software_only:
        run("scripts/run_rtl.py")
        if a.profile=="offline":
            run("scripts/run_rtl.py","--full","--bundle","examples/demo")
        else:
            cases=[("trained32",0,0,1),("trained32",1,0,4),("trained32",0,1,4),("trained32",1,1,4),
                   ("trained28",1,1,4),("structured28",1,1,4),("pruned28",1,1,4)]
            for bundle,sparse,cache,latency in cases:
                run("scripts/run_rtl.py","--full","--bundle",f"examples/{bundle}","--sparse",str(sparse),
                    "--cache",str(cache),"--l2-latency",str(latency))
                stem=f"full_{bundle}_r5c5_s{sparse}_c{cache}_l{latency}"
                run("scripts/model_timing.py","--bundle",f"examples/{bundle}","--sparse",str(sparse),
                    "--cache",str(cache),"--latency",str(latency),"--compare-rtl",f"results/verification/{stem}.json",
                    "--output",f"results/models/{stem}.json")
    if a.profile=="full" and not a.software_only:
        run("scripts/make_figures.py")
        run("scripts/make_report.py")
    print("Completed requested profile."+(" RTL was explicitly omitted." if a.software_only else ""))


if __name__=="__main__":main()
