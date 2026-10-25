#!/usr/bin/env python3
"""Rebuild editable hardware SVGs and plots strictly from saved experiment data."""
from pathlib import Path
from html import escape
import json
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/figures"
OUT.mkdir(parents=True,exist_ok=True)
NAVY="#19324b";TEAL="#007f86";GOLD="#bd761c";PURPLE="#7160a4";GRAY="#607286"
LIGHT="#f3f7fa";BORDER="#cbd7e2";WHITE="#ffffff"


class SVG:
    def __init__(self,title,subtitle,height=760):
        self.h=height
        self.parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="{height}" viewBox="0 0 1280 {height}">',
                    '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#19324b"/></marker></defs>',
                    '<rect width="1280" height="100%" fill="white"/>']
        self.text(44,35,"FASHIONLENET  /  HARDWARE LAB",12,TEAL,weight="bold")
        self.text(44,79,title,30,NAVY,weight="bold")
        self.text(44,110,subtitle,16,GRAY)
        self.path("M44 134H1236",BORDER,1)

    def text(self,x,y,value,size=16,color=NAVY,anchor="start",weight="normal"):
        self.parts.append(f'<text x="{x}" y="{y}" font-family="DejaVu Sans,Arial,sans-serif" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{weight}">{escape(str(value))}</text>')

    def rect(self,x,y,w,h,fill=LIGHT,stroke=BORDER,rx=8,dash=False):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"'+(' stroke-dasharray="6 4"' if dash else '')+'/>')

    def card(self,x,y,w,h,title,lines,color=TEAL):
        self.rect(x,y,w,h)
        self.parts.append(f'<path d="M{x+10} {y}H{x+w-10}" stroke="{color}" stroke-width="4"/>')
        def fit(value,start,bold=False):
            font="DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
            while start>9 and ImageFont.truetype(font,start).getlength(value)>w-32:start-=1
            return start
        self.text(x+16,y+32,title,fit(title,19,True),NAVY,weight="bold")
        for i,line in enumerate(lines):self.text(x+16,y+61+i*23,line,fit(line,14),GRAY)

    def path(self,path,color=NAVY,width=2,arrow=False,both=False,dash=False):
        attrs=(' marker-end="url(#arrow)"' if arrow else '')+(' marker-start="url(#arrow)"' if both else '')+(' stroke-dasharray="6 5"' if dash else '')
        self.parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"{attrs}/>')

    def save(self,name):
        self.text(44,self.h-24,"INT8 operands  /  INT32 local sums  /  synchronous ready-valid interface",12,GRAY)
        self.parts.append('</svg>')
        path=OUT/(name+".svg")
        path.write_text("\n".join(self.parts))
        try:
            import cairosvg
            cairosvg.svg2png(url=str(path),write_to=str(OUT/(name+".png")))
        except ImportError:
            print("Install cairosvg to rebuild PNG companions; editable SVGs were generated")


def network_diagram():
    s=SVG("LeNet geometry and hardware mapping","32 x 32 input uses 2-pixel zero padding around each original 28 x 28 Fashion-MNIST image.",740)
    top=[(44,"Input",["1 x 32 x 32","Raw pixels / 255","INT8 scale = 1/128"],TEAL),
         (353,"Conv1 + ReLU",["6 x 28 x 28","6 filters / 5 x 5","117,600 MACs"],PURPLE),
         (662,"Max pool 1",["6 x 14 x 14","2 x 2 / stride 2","No multiplications"],GOLD),
         (971,"Conv2 + ReLU",["16 x 10 x 10","16 filters / 5 x 5","240,000 MACs"],PURPLE)]
    for x,title,lines,col in top:s.card(x,184,265,157,title,lines,col)
    for x in [309,618,927]:s.path(f"M{x} 259h44",arrow=True)
    bottom=[(44,"Max pool 2",["16 x 5 x 5","2 x 2 / stride 2","No multiplications"],GOLD),
            (353,"Conv3 + ReLU",["120 x 1 x 1","120 filters / 5 x 5","48,000 MACs"],PURPLE),
            (662,"FC1 + ReLU",["120 -> 84","84 x 120 weights","10,080 MACs"],PURPLE),
            (971,"FC2 + argmax",["84 -> 10 classes","Signed INT8 logits","840 MACs"],TEAL)]
    for x,title,lines,col in bottom:s.card(x,433,265,157,title,lines,col)
    for x in [309,618,927]:s.path(f"M{x} 508h44",arrow=True)
    s.path("M1103 341V383H176V433",arrow=True)
    s.text(44,645,"32 x 32: 61,706 trainable parameters; 416,520 MACs per image.",17,weight="bold")
    s.text(44,674,"28 x 28 variant: 24 -> 12 -> 8 -> 4 spatial sizes; Conv3 uses a 4 x 4 kernel.",15,GRAY)
    s.save("network")


def hardware():
    from hardware_figures import generate
    generate()
    network_diagram()


def save_plot(fig,name):
    fig.savefig(OUT/(name+".svg"),bbox_inches="tight",facecolor="white")
    fig.savefig(OUT/(name+".png"),bbox_inches="tight",dpi=180,facecolor="white")
    plt.close(fig)


def plots():
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.spines.top":False,"axes.spines.right":False,
                         "axes.titleweight":"bold","axes.labelcolor":NAVY,"text.color":NAVY,"svg.fonttype":"none"})
    fig,ax=plt.subplots(1,2,figsize=(11,3.8),layout="constrained")
    for size,col in [(28,TEAL),(32,PURPLE)]:
        h=json.loads((ROOT/f"results/trained{size}/history.json").read_text())
        ax[0].plot([x["epoch"] for x in h],[x["train_loss"] for x in h],"o-",ms=3,label=f"{size} x {size}",color=col)
        ax[1].plot([x["epoch"] for x in h],[x["validation_accuracy"]*100 for x in h],"o-",ms=3,label=f"{size} x {size}",color=col)
    ax[0].set(xlabel="Epoch",ylabel="Training cross-entropy",title="Measured training loss")
    ax[1].set(xlabel="Epoch",ylabel="Validation accuracy (%)",title="5,000-image held-out validation")
    for a in ax:a.grid(alpha=.15);a.legend(frameon=False)
    save_plot(fig,"training")
    rows=json.loads((ROOT/"results/pruning28/summary.json").read_text())
    fig,ax=plt.subplots(1,2,figsize=(11,4),layout="constrained")
    for method,color in [("unstructured",TEAL),("structured",PURPLE)]:
        subset=[r for r in rows if r["method"]==method]
        xx=[r["target_fraction"]*100 for r in subset]
        ax[0].plot(xx,[r["fp32_accuracy"]*100 for r in subset],"o-",color=color,label=method+" FP32")
        ax[0].plot(xx,[r["int8_accuracy"]*100 for r in subset],"s--",color=color,alpha=.7,label=method+" INT8")
        ax[1].plot(xx,[r["int8_dense_payload_bytes"]/1024 for r in subset],"o-",color=color,label=method)
    ax[0].axhline(rows[0]["fp32_accuracy"]*100,color=GRAY,ls=":",label="FP32 baseline")
    ax[0].set(xlabel="Target weight / channel removal (%)",ylabel="Test accuracy (%)",title="Immediate pruning + PTQ (no recovery)",ylim=(0,100))
    ax[1].set(xlabel="Target weight / channel removal (%)",ylabel="Dense INT8 payload (KiB, includes bias)",title="Physical storage differs from nonzero count")
    for a in ax:a.grid(alpha=.15);a.legend(frameon=False,fontsize=8)
    save_plot(fig,"pruning")
    ft=json.loads((ROOT/"results/finetuned28/summary.json").read_text())
    fig,ax=plt.subplots(figsize=(8,3.8),layout="constrained")
    names=["Unstructured 50%","Structured 50%"]
    xx=np.arange(2)
    selected=ft[1:]
    for offset,key,color,label in [(-.25,"accuracy_before_finetune",GRAY,"FP32 immediate"),(0,"fp32_accuracy",TEAL,"FP32 after 3 epochs"),(.25,"int8_accuracy",PURPLE,"INT8 after 3 epochs")]:
        bars=ax.bar(xx+offset,[r[key]*100 for r in selected],.24,label=label,color=color)
        ax.bar_label(bars,fmt="%.2f",fontsize=9,padding=3)
    ax.set(xticks=xx,xticklabels=names,ylabel="Accuracy on 10,000 test images (%)",ylim=(0,103),title="Fixed three-epoch recovery on training data")
    ax.legend(frameon=False,loc="upper center",ncols=3,fontsize=8)
    save_plot(fig,"recovery")
    names_files=[("Single level / L=1", "full_trained32_r5c5_s0_c0_l1.json"),
                 ("L2 / L=4, cache off","full_trained32_r5c5_s1_c0_l4.json"),
                 ("L1 + L2, dense MAC","full_trained32_r5c5_s0_c1_l4.json"),
                 ("L1 + L2, zero gating","full_trained32_r5c5_s1_c1_l4.json")]
    results=[json.loads((ROOT/"results/verification"/f).read_text()) for _,f in names_files]
    fig,ax=plt.subplots(1,2,figsize=(11,4.2),layout="constrained")
    xx=np.arange(4)
    bars=ax[0].barh(xx,[r["cycles"]/1e6 for r in results],color=[GRAY,GOLD,TEAL,PURPLE])
    ax[0].bar_label(bars,fmt="%.3f M",padding=4,fontsize=9)
    ax[0].set(yticks=xx,yticklabels=[n for n,_ in names_files],xlabel="Simulated inference clocks (millions)",title="RTL timing: trained test image #0",xlim=(0,2.9));ax[0].invert_yaxis()
    last=results[-1]
    vals=[last["mac_executed"],last["mac_attempted"]-last["mac_executed"]]
    ax[1].pie(vals,labels=["Executed MACs","Suppressed MACs"],colors=[TEAL,"#dfe7ed"],autopct="%.1f%%",startangle=90,wedgeprops={"width":.38,"edgecolor":"white"})
    ax[1].set_title("Zero gating preserves the clock schedule")
    save_plot(fig,"rtl_results")
    cm=np.array(json.loads((ROOT/"results/trained32/int8_test.json").read_text())["confusion_matrix"])
    fig,ax=plt.subplots(figsize=(7,5.6),layout="constrained")
    im=ax.imshow(cm,cmap="Blues")
    labels=["T-shirt","Trouser","Pullover","Dress","Coat","Sandal","Shirt","Sneaker","Bag","Boot"]
    for i in range(10):
        for j in range(10):
            if cm[i,j]>=15:ax.text(j,i,str(cm[i,j]),ha="center",va="center",fontsize=7,color="white" if cm[i,j]>600 else NAVY)
    ax.set(xticks=range(10),yticks=range(10),xticklabels=labels,yticklabels=labels,xlabel="Predicted class",ylabel="True class",title="INT8 model: 89.03% / 10,000 test images")
    plt.setp(ax.get_xticklabels(),rotation=40,ha="right")
    fig.colorbar(im,ax=ax,label="Images")
    save_plot(fig,"confusion_matrix")
    fig,ax=plt.subplots(figsize=(10,4),layout="constrained")
    colors=[TEAL,PURPLE,GOLD,GRAY]
    for r in range(3):
        for c in range(3):
            row=r*3+c
            for k in range(4):
                ax.broken_barh([(k+r+c,.92)],(row-.35,.7),facecolors=colors[k])
                ax.text(k+r+c+.46,row,str(k),color="white",ha="center",va="center",fontsize=9)
    ax.set(yticks=range(9),yticklabels=[f"PE({r},{c})" for r in range(3) for c in range(3)],xticks=range(8),xlabel="Global advance pulse (memory stalls do not advance this axis)",title="Analytic systolic schedule: reduction index k arrives at k + row + column",ylim=(8.7,-.7),xlim=(-.2,8))
    ax.grid(axis="x",alpha=.15)
    save_plot(fig,"systolic_schedule")


def waveform():
    path=ROOT/"results/waveforms/os_pe.vcd"
    symbols={};widths={};events={};stack=[];time=0;header=True
    for line in path.read_text().splitlines():
        fields=line.split()
        if not fields:continue
        if header:
            if fields[0]=="$scope":stack.append(fields[2])
            elif fields[0]=="$upscope":stack.pop()
            elif fields[0]=="$var":
                name=".".join(stack+[fields[4]])
                symbols[name]=fields[3];widths[fields[3]]=int(fields[2]);events.setdefault(fields[3],[])
            elif fields[0]=="$enddefinitions":header=False
            continue
        if line.startswith("#"):time=int(line[1:])/1000
        elif line[0] in "01xz":
            symbol=line[1:];value=line[0]
            if symbol in events and value in "01":events[symbol].append((time,int(value)))
        elif line[0] in "bB":
            bits,symbol=fields[0][1:],fields[1]
            if symbol in events and not any(v in bits.lower() for v in "xz"):
                value=int(bits,2);width=widths[symbol]
                if width>1 and value>=2**(width-1):value-=2**width
                events[symbol].append((time,value))
    signals=[("clk",False),("step",False),("sparse_en",False),("a",True),("b",True),("executed",False),("acc",True)]
    fig,axes=plt.subplots(len(signals),2,figsize=(12,7),sharex="col",layout="constrained")
    # Two measured windows from the dense and sparse portions of the actual VCD.
    for col,(lo,hi) in enumerate([(30,190),(4040,4200)]):
        for row,(signal,bus) in enumerate(signals):
            ax=axes[row,col];arr=events[symbols["tb_os_pe."+signal]]
            before=[e for e in arr if e[0]<=lo]
            points=([(lo,before[-1][1])] if before else [(lo,0)])+[e for e in arr if lo<e[0]<=hi]
            points.append((hi,points[-1][1]))
            t,v=zip(*points);ax.step(np.array(t)-lo,v,where="post",color=PURPLE if bus else TEAL,lw=1.3)
            ax.set_ylabel(signal,rotation=0,ha="right",va="center",fontsize=9)
            ax.grid(axis="x",alpha=.12);ax.spines["left"].set_visible(False)
            ax.tick_params(axis="y",labelsize=7,length=0)
            if not bus:ax.set(ylim=(-.2,1.3),yticks=[0,1])
            if row==0:ax.set_title(f"Measured VCD: {lo}-{hi} ns")
        axes[-1,col].set_xlabel("Time from window start (ns)")
    save_plot(fig,"pe_waveform")


if __name__=="__main__":
    hardware();plots();waveform()
    print(f"Figures written to {OUT}")
