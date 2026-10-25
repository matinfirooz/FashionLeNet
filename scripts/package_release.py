#!/usr/bin/env python3
"""Create a clean GitHub ZIP with per-file hashes, excluding caches and raw datasets."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument("--output",default=str(root.parent/"FashionLeNet-GitHub.zip"))
a=p.parse_args()
excluded={".git",".venv","__pycache__","data","build",".pytest_cache",".ipynb_checkpoints"}
def selected(path):
    rel=path.relative_to(root)
    return path.is_file() and not any(v in excluded or v.endswith('.egg-info') for v in rel.parts) and path.suffix not in (".pyc",".vvp",".zip")
files=sorted(p for p in root.rglob("*") if selected(p) and p.name!="SHA256SUMS.json")
hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(root/"SHA256SUMS.json").write_text(json.dumps(hashes,indent=2)+"\n")
files.append(root/"SHA256SUMS.json")
out=Path(a.output).resolve();out.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for path in files:z.write(path,"FashionLeNet/"+path.relative_to(root).as_posix())
with zipfile.ZipFile(out) as z:
    bad=z.testzip()
    if bad:raise SystemExit(f"ZIP integrity error: {bad}")
print(json.dumps({"archive":str(out),"files":len(files),"bytes":out.stat().st_size,
                  "sha256":hashlib.sha256(out.read_bytes()).hexdigest()},indent=2))
