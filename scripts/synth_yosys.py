#!/usr/bin/env python3
"""Technology-independent RTL lowering/check. These cells are NOT FPGA resources."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument("--top",default="fpga_top",choices=["fpga_top","os_array","os_pe"])
p.add_argument("--output",default="results/yosys")
a=p.parse_args()
yosys=os.environ.get("YOSYS","yosys")
if not shutil.which(yosys):raise SystemExit("Install Yosys or set YOSYS to its executable")
os.chdir(root)
out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
files=" ".join(str(f.relative_to(root)) for f in sorted((root/"rtl").glob("*.sv")))
relative_out=Path(os.path.relpath(out,root)).as_posix()
if any(ch.isspace() for ch in relative_out):raise SystemExit("Choose an output directory without spaces")
script=(f"read_verilog -sv {files}; hierarchy -check -top {a.top}; proc; opt; "
        f'memory_dff; memory_collect; check -assert; tee -o {relative_out}/{a.top}.json stat -json; '
        f'write_json {relative_out}/{a.top}_netlist.json')
(out/(a.top+".ys")).write_text(script+"\n")
r=subprocess.run([yosys,"-Q","-T","-l",str(out/(a.top+".log")),"-s",str(out/(a.top+".ys"))],capture_output=True,text=True)
if r.returncode:
    print(r.stdout[-6000:]);print(r.stderr);raise SystemExit(r.returncode)
stat=json.loads((out/(a.top+".json")).read_text())
design=stat.get("design",next(iter(stat["modules"].values())))
summary={"status":"PASS", "flow":"Yosys proc/opt/memory_collect/check -assert", "top":a.top,
         "technology_mapped":False,"num_generic_cells":design["num_cells"],
         "cell_types":design["num_cells_by_type"],"LUT":None,"FF":None,"DSP":None,"BRAM":None,
         "routed_frequency_MHz":None,"power_mW":None}
(out/(a.top+"_summary.json")).write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary,indent=2))
