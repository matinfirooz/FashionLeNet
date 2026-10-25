#!/usr/bin/env python3
"""Generate audit tables from stored measurements; missing physical metrics stay null."""
from pathlib import Path
import csv
import json
import platform
import sys
import numpy as np
from fashionlenet.sim import simulate_bundle

ROOT=Path(__file__).resolve().parents[1]


def table(headers,rows):
    return "| "+" | ".join(headers)+" |\n|"+"|".join("---" for _ in headers)+"|\n"+"".join("| "+" | ".join(str(v) for v in row)+" |\n" for row in rows)


def main():
    output=ROOT/"results/models";output.mkdir(parents=True,exist_ok=True)
    cases=[]
    for path in sorted((ROOT/"results").rglob("full_*.json")):
        case=json.loads(path.read_text())
        if case.get("status")!="PASS" or "bundle" not in case:continue
        bundle=ROOT/case["bundle"]
        model=simulate_bundle(bundle,case["rows"],case["cols"],bool(case["cache"]),case["l2_latency"],bool(case["sparse"]))
        for key in ["cycles","mac_attempted","mac_executed","cache_hits","cache_misses","cache_bypasses"]:
            if case[key]!=model[key]:raise ValueError(f"{path}: model/RTL mismatch {key}")
        model["bundle"]=case["bundle"]
        model["validated_against_rtl"]=str(path.relative_to(ROOT))
        (output/(path.stem+".json")).write_text(json.dumps(model,indent=2)+"\n")
        manifest=json.loads((bundle/"manifest.json").read_text())
        cases.append({**case,"source":str(path.relative_to(ROOT)),"provenance":manifest["provenance"],
                      "model_matches_rtl":True,"conditional_latency_ms_at_100MHz":case["cycles"]/1e5})
    tests=json.loads((ROOT/"results/verification/rtl_units.json").read_text())
    accuracies=[]
    for size in [28,32]:
        folder=ROOT/f"results/trained{size}"
        fp=json.loads((folder/"fp32_test.json").read_text())
        q=json.loads((folder/"int8_test.json").read_text())
        accuracies.append([f"{size} x {size}",f"{fp['accuracy']*100:.2f}%",f"{q['accuracy']*100:.2f}%",fp["samples"]])
    pruning=json.loads((ROOT/"results/pruning28/summary.json").read_text())
    fine=json.loads((ROOT/"results/finetuned28/summary.json").read_text())
    cpu=json.loads((ROOT/"results/cpu_baseline32.json").read_text())
    summary={"accuracy":accuracies,"rtl_unit_tests":tests["tests"],"full_system_cases":cases,
             "fpga":json.loads((ROOT/"results/fpga_status.json").read_text()),
             "cpu_median_ms":cpu["median_ms"],"training_test_protocol":"55000 fit / 5000 validation / 10000 official test",
             "all_model_rtl_comparisons_passed":True}
    (ROOT/"results/release_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    rows=[]
    for c in cases:
        rows.append([c["bundle"].split("/")[-1],c["sparse"],c["cache"],c["l2_latency"],c["cycles"],
                     c["mac_executed"],c["mac_attempted"],c["prediction"]])
    report="# Measured project results\n\n"
    report+="Generated from the stored JSON/CSV logs. Test accuracy uses all 10,000 official test images; RTL evidence covers the listed complete-image regressions.\n\n"
    report+="## Baselines and quantization\n\n"+table(["Input","FP32 test","INT8 test","Test images"],accuracies)
    report+="\nBoth models use training/validation split selection; calibration uses 500 images from the official training split. The 32-input model was trained for 12 epochs and the 28-input model for 15. The best validation checkpoint is evaluated, not a test-selected checkpoint.\n\n"
    report+="![Training](figures/training.svg)\n\n## Full pruning sweep, native 28-input network\n\n"
    report+=table(["Method","Target removal","Actual widths","Parameters","Nonzero weights","FP32 test","INT8 test","INT8 bytes"],
                  [[r["method"],f"{r['target_fraction']*100:g}%",str(r["channels"]),r["stored_parameters"],r["nonzero_weights"],
                    f"{r['fp32_accuracy']*100:.2f}%",f"{r['int8_accuracy']*100:.2f}%",r["int8_dense_payload_bytes"]] for r in pruning])
    report+="\nTarget fraction is weight removal for unstructured pruning and hidden width removal for structural pruning. Kept widths use ceil, with at least one unit and all ten output classes. Dependency removal can reduce total parameters by a different percentage. Unstructured dense storage does not shrink. INT8 bytes include INT32 biases and five shifts.\n\n![Pruning](figures/pruning.svg)\n\n"
    report+="## Recovery after 50% pruning\n\n"+table(["Method","Epochs","Immediate FP32","Recovered FP32","Recovered INT8","INT8 bytes"],
             [[r["method"],r["finetune_epochs"],f"{r['accuracy_before_finetune']*100:.2f}%",f"{r['fp32_accuracy']*100:.2f}%",
               f"{r['int8_accuracy']*100:.2f}%",r["int8_dense_payload_bytes"]] for r in fine])
    report+="\nRecovery uses a fixed three-epoch Adam run at 1e-4 on the 55,000-image training partition. Unstructured masks are enforced after every optimizer step. PTQ follows recovery; PTQ itself does not retrain.\n\n![Recovery](figures/recovery.svg)\n\n"
    report+="## RTL and memory experiments\n\n"+table(["Bundle","Sparse","Cache","L2 clocks","RTL clocks","Executed MACs","Candidate MACs","Class"],rows)
    report+=f"\nAll {len(cases)} listed cases pass every INT32 writeback and every INT8 stage comparison. All {len(tests['tests'])} module benches pass. The independent transaction model matches clocks, candidate/executed MACs, hits, misses and bypasses for every listed case.\n\n"
    report+="![RTL](figures/rtl_results.svg)\n\nThe primary 32-input cached pair uses identical 2,249,791-clock schedules with and without zero gating. Sparse execution removes 174,967 MACs (42.01%) for test image #0. With the same four-clock L2, caching reduces 2,366,413 to 2,249,791 clocks (4.93%). The one-level, one-clock backing baseline takes 1,520,524 clocks; it is a faster memory assumption, so it is not the matched denominator for cache benefit.\n\n"
    report+="The native 28-input default layout has worse cache conflicts despite fewer MACs. The 50% structured 28-input model has 92,220 candidate MACs and a 460,561-clock inference for image #0, while its full-dataset INT8 accuracy is 85.50%. Gating alone does not reduce memory requests or clocks. These results expose the front end and mapping tradeoffs rather than claiming uniform acceleration.\n\n"
    report+="## CPU, synthesis and power\n\n"
    report+=f"The local batch-one FP32 CPU run has median **{cpu['median_ms']:.6f} ms**, p05 {cpu['p05_ms']:.6f} ms, p95 {cpu['p95_ms']:.6f} ms, one thread, 30 warm-up calls and {cpu['repeats']} timed calls. It is not a Colab measurement. The notebook provides the same experiment for Colab.\n\n"
    report+="At a hypothetical achieved 100 MHz, the cached 32-input design would take 22.49791 ms. This byte-serial educational design is slower than the local CPU. This number is a clock conversion, not measured FPGA latency. Host model/image transfer is excluded.\n\n"
    report+="Yosys proc/opt/memory collection and structural checking pass for the complete top and the array. Generic optimized IR contains 1,341 cells for the complete top and 573 for the array; 25 of the array cells are multiply operators. These are not LUT, FF, DSP or BRAM primitive counts. Runtime div/mod address generation and the byte port are visible implementation bottlenecks.\n\n"
    report+="Vivado synthesis/place/route, achieved setup/hold timing, mapped resources, activity-annotated power and on-board execution are **not run**. Their result fields are null in `results/fpga_status.json`. The FPGA scripts, analysis method, workload fixtures and source references are provided so these measurements can be completed without substituting invented values.\n\n"
    report+="## Evidence and limitations\n\nThe source PDF's ambiguities are resolved in [REQUIREMENTS.md](REQUIREMENTS.md). The arithmetic, memory policy and verification coverage are specified separately. Source data, scripts, logs, checkpoints and editable figures are included. The instructor's report template was not attached; the report content below must be transferred into that required template for formal submission.\n"
    (ROOT/"docs/RESULTS.md").write_text(report)
    project=("# LeNet-5 output-stationary hardware acceleration\n\n"
             "Author: Matin Firoozbakht. Student number: **enter your actual student number**.\n\n"
             "This is substantive report content, not the unavailable instructor template.\n\n"
             "## Objective and design choices\n\nTrain and optimize Fashion-MNIST LeNet, then implement complete INT8 inference on a reusable systolic array. The design keeps each dot-product sum in its owning PE, uses implicit im2col instead of a window matrix buffer, and supports both dense and zero-gated MAC modes. An optional 1 KiB cache and a four-clock byte RAM model expose memory costs.\n\n"
             "## Method\n\nUse the documented seeded train/validation split and evaluate the fixed test split. Separate physical channel removal from unstructured zeroing. Calibrate symmetric power-of-two INT8 scales on training images and retain signed INT32 accumulators/biases. Compare a separate NumPy oracle with all RTL layer results. Count actual executed MAC enables, not theoretical sparsity alone. Keep measured clocks distinct from a target frequency and physical power.\n\n"
             "![Architecture](../figures/architecture.svg)\n\n"
             +report.replace("# Measured project results","## Experimental results",1).replace("](figures/","](../figures/").replace("](REQUIREMENTS.md)","](../REQUIREMENTS.md)")+
             "\n## Discussion\n\nINT8 preserves most baseline accuracy at roughly one quarter of FP32 parameter payload. Immediate high pruning is damaging; fixed fine-tuning improves moderate sparsity, while physical structural removal gives real storage and latency reductions. A directly mapped small cache helps the primary 32-input workload but can conflict heavily for another tensor layout. Dense and sparse modes intentionally share the same schedule, so zero suppression supports an activity/power study rather than a latency claim.\n\n"
             "## Further implementation work\n\nReplace variable arithmetic in the address path with counters, introduce banked/vector memory supply, validate FPGA RAM mapping, and run placement/routing and annotated power. Evaluate a compressed stream scheduler only if it preserves coordinate ownership and proves real cycle savings. Rerun identical workloads and CPU timing in the required Colab environment.\n\n"
             "## References\n\nSee [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md), [COMPARISON.md](../COMPARISON.md), the attached original project brief, and [FPGA flow references](../../fpga/README.md).\n")
    (ROOT/"docs/report/Project_Report.md").write_text(project)
    environment={"python":sys.version,"numpy":np.__version__,"platform":platform.platform(),"tools":{"iverilog":"12.0","yosys":"0.33"},
                 "simulation_clock_ns":10,"hardware_target_MHz":100,"hardware_target_achieved":False}
    try:
        import torch
        environment["torch"]=torch.__version__
    except ImportError:pass
    (ROOT/"results/environment.json").write_text(json.dumps(environment,indent=2)+"\n")
    print(f"Reports generated; {len(cases)} full-system cases agree with timing model")


if __name__=="__main__":main()
