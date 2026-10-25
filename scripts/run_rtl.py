#!/usr/bin/env python3
"""Compile actual synthesizable source with Icarus; missing tools are failures."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
UNITS=["os_pe","skew_buffer","os_array","requantize","pool2x2","argmax10", "backing_store",
       "read_cache","gemm_engine","pool_engine","lenet_core"]


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--full",action="store_true")
    p.add_argument("--unit",choices=UNITS)
    p.add_argument("--bundle",default="examples/demo")
    p.add_argument("--sparse",type=int,choices=[0,1],default=1)
    p.add_argument("--cache",type=int,choices=[0,1],default=1)
    p.add_argument("--l2-latency",type=int,default=4)
    p.add_argument("--rows",type=int,default=5)
    p.add_argument("--cols",type=int,default=5)
    p.add_argument("--output",default="results/verification")
    a=p.parse_args()
    if min(a.rows,a.cols,a.l2_latency)<1: p.error("rows, cols, latency must be positive")
    compiler=os.environ.get("IVERILOG","iverilog")
    runner=os.environ.get("VVP","vvp")
    for tool in [compiler,runner]:
        if not shutil.which(tool): raise SystemExit(f"Missing {tool}: install Icarus Verilog")
    os.chdir(ROOT)
    build=ROOT/"build";build.mkdir(exist_ok=True)
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    sources=sorted(str(x) for x in (ROOT/"rtl").glob("*.sv"))
    tests=["fpga_top"] if a.full else [a.unit] if a.unit else UNITS
    records=[]
    for name in tests:
        top="tb_"+name
        stem=(f"full_{Path(a.bundle).name}_r{a.rows}c{a.cols}_s{a.sparse}_c{a.cache}_l{a.l2_latency}" if a.full else top)
        executable=build/(stem+".vvp")
        command=[compiler]
        if os.environ.get("IVERILOG_IVL"):command += ["-B",os.environ["IVERILOG_IVL"]]
        command += ["-g2012","-Wall","-s",top,"-o",str(executable)]
        if a.full:
            command += ["-I",str(Path(a.bundle).resolve()),f"-P{top}.ROWS={a.rows}",
                        f"-P{top}.COLS={a.cols}",f"-P{top}.L2_LATENCY={a.l2_latency}"]
        command += sources+[str(ROOT/"tb"/(top+".sv"))]
        begin=time.perf_counter()
        compile_result=subprocess.run(command,text=True,capture_output=True)
        (out/(stem+"_compile.log")).write_text(compile_result.stdout+compile_result.stderr)
        if compile_result.returncode:
            print(compile_result.stderr);raise SystemExit(f"Compile failed: {top}")
        run=[runner,str(executable)]
        if a.full:
            run += [f"+BUNDLE={a.bundle}",f"+SPARSE={a.sparse}",f"+CACHE={a.cache}",f"+REPORT={out/(stem+'.json')}"]
        result=subprocess.run(run,text=True,capture_output=True,timeout=240)
        (out/(stem+".log")).write_text(result.stdout+result.stderr)
        print(result.stdout,flush=True)
        if result.returncode or f"PASS {top}" not in result.stdout:
            print(result.stderr);raise SystemExit(f"RTL test failed: {top}")
        records.append({"test":top,"status":"PASS","seconds":time.perf_counter()-begin})
    if not a.full:
        (out/"rtl_units.json").write_text(json.dumps({"tool":"Icarus Verilog", "tests":records},indent=2)+"\n")


if __name__=="__main__":main()
