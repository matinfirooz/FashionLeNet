#!/usr/bin/env python3
"""Editable RTL schematics: real buses, register enables, muxes, and local sums.

No performance data or RTL is modified. Native SVG shapes remain editable.
"""
from pathlib import Path
from html import escape
import argparse
import json
import hashlib
import zipfile
from PIL import ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/figures"
INK="#192d40"; TEAL="#087f86"; GRAY="#657580"; GRID="#c5d0d7"
BLUE="#eaf2f8"; GREEN="#e9f3f0"; CREAM="#faf3e7"; PAPER="#ffffff"


class Drawing:
    def __init__(self,name,title,subtitle,w=1800,h=1080):
        self.name=name;self.w=w;self.h=h;self.text_boxes=[]
        self.s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
                '<defs>'+''.join(f'<marker id="arr{n}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{color}"/></marker>' for n,color in [('d',INK),('c',TEAL),('g',GRAY)])+'</defs>',
                f'<rect width="{w}" height="{h}" fill="white"/>']
        self.text(48,48,title,31,bold=True)
        self.text(48,80,subtitle,17,color=GRAY)
        self.line([(48,105),(w-48,105)],width=1,color=GRID)

    def text(self,x,y,t,size=18,color=INK,anchor="start",bold=False,mono=False):
        font=("DejaVuSansMono" if mono else "DejaVuSans")+("-Bold" if bold else "")+".ttf"
        try:
            f=ImageFont.truetype(font,size)
        except OSError:
            from matplotlib.font_manager import findfont,FontProperties
            f=ImageFont.truetype(findfont(FontProperties(family="DejaVu Sans Mono" if mono else "DejaVu Sans",weight="bold" if bold else "normal")),size)
        width=f.getlength(str(t))
        left=x if anchor=="start" else x-width if anchor=="end" else x-width/2
        if left < 8 or left+width > self.w-8 or y-size < 0 or y > self.h-8:
            raise ValueError(f"Text leaves canvas: {self.name}: {t}")
        self.text_boxes.append((left,y-size,width,size,str(t)))
        family="DejaVu Sans Mono,monospace" if mono else "DejaVu Sans,Arial,sans-serif"
        self.s.append(f'<text x="{x}" y="{y}" fill="{color}" text-anchor="{anchor}" font-family="{family}" font-size="{size}" font-weight="'+('bold' if bold else 'normal')+f'">{escape(str(t))}</text>')

    def line(self,points,width=2.5,color=INK,arrow=False,dash=False,both=False):
        path="M"+" L".join(f"{x},{y}" for x,y in points)
        marker='c' if color==TEAL else 'g' if color==GRAY else 'd'
        self.s.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="square" stroke-linejoin="miter"'+
                      (f' marker-end="url(#arr{marker})"' if arrow else '')+(f' marker-start="url(#arr{marker})"' if both else '')+(' stroke-dasharray="7 5"' if dash else '')+'/>')

    def rect(self,x,y,w,h,fill=PAPER,stroke=INK,width=2,dash=False):
        self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"'+(' stroke-dasharray="8 5"' if dash else '')+'/>')

    def box(self,x,y,w,h,title,sub=None,fill=PAPER,size=21):
        self.rect(x,y,w,h,fill)
        self.text(x+w/2,y+h/2-(4 if sub else -7),title,size,anchor="middle",bold=True)
        if sub:self.text(x+w/2,y+h/2+25,sub,16,anchor="middle",color=GRAY)

    def reg(self,x,y,w,h,name,bits,enable=None,clear=None):
        self.rect(x,y,w,h,BLUE)
        self.text(x+12,y+24,"D",13,color=GRAY)
        self.text(x+w-12,y+24,"Q",13,color=GRAY,anchor="end")
        self.text(x+w/2,y+h/2+2,name,19,anchor="middle",bold=True)
        self.text(x+w/2,y+h/2+24,f"{bits}b",15,anchor="middle",color=GRAY)
        self.line([(x,y+h-25),(x+12,y+h-17),(x,y+h-9)],width=1.5)
        if enable:self.text(x+w/2,y+h-7,"EN: "+enable,12,anchor="middle",color=TEAL)
        if clear:self.text(x+w/2,y-10,"CLR: "+clear,12,anchor="middle",color=TEAL)

    def mux(self,x,y,w,h,label="2:1",flip=False):
        points=(f"{x+w},{y} {x},{y+17} {x},{y+h-17} {x+w},{y+h}" if flip else
                f"{x},{y} {x+w},{y+17} {x+w},{y+h-17} {x},{y+h}")
        self.s.append(f'<polygon points="{points}" fill="{CREAM}" stroke="{INK}" stroke-width="2"/>')
        self.text(x+w/2,y+h/2+6,label,17,anchor="middle",bold=True)
        if label=="2:1":
            self.text(x+12,y+h*.25+5,"1",12,color=GRAY)
            self.text(x+12,y+h*.75+5,"0",12,color=GRAY)

    def op(self,x,y,r,label):
        self.s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="white" stroke="{INK}" stroke-width="2.3"/>')
        self.text(x,y+10,label,30,anchor="middle")

    def dot(self,x,y,color=INK):self.s.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{color}"/>')

    def bus(self,points,bits=None,label=None,at=None,arrow=True,color=INK):
        self.line(points,width=3,color=color,arrow=arrow)
        if at is None:
            a,b=points[0],points[1];at=((a[0]+b[0])/2,(a[1]+b[1])/2)
        x,y=at
        if bits:
            self.line([(x-5,y+7),(x+5,y-7)],width=1.6,color=color)
            self.text(x+8,y-9,str(bits),14,color=color)
        if label:self.text(x,y-27,label,16,color=color,anchor="middle")

    def memory(self,x,y,w,h,title,rows):
        self.rect(x,y,w,h,fill=GREEN)
        self.line([(x+13,y),(x+13,y+h)],width=1,color=GRID)
        self.line([(x+w-13,y),(x+w-13,y+h)],width=1,color=GRID)
        self.text(x+w/2,y+35,title,22,anchor="middle",bold=True)
        start=y+60;step=(h-75)/max(1,len(rows))
        for i,row in enumerate(rows):
            self.line([(x+13,start+i*step-9),(x+w-13,start+i*step-9)],width=1,color=GRID)
            self.text(x+w/2,start+i*step+22,row,17,anchor="middle")

    def section(self,x,y,w,h,label):
        self.rect(x,y,w,h,fill="none",stroke=GRID,width=1.4,dash=True)
        self.text(x+14,y+26,label,16,color=GRAY,bold=True)

    def save(self):
        self.line([(48,self.h-70),(self.w-48,self.h-70)],width=1,color=GRID)
        self.bus([(55,self.h-38),(115,self.h-38)],arrow=False)
        self.text(132,self.h-31,"datapath bus",14,color=GRAY)
        self.line([(325,self.h-38),(390,self.h-38)],color=TEAL,width=1.6,dash=True,arrow=True)
        self.text(407,self.h-31,"control / enable",14,color=GRAY)
        self.text(self.w-48,self.h-31,"FashionLeNet | RTL microarchitecture",14,color=GRAY,anchor="end")
        self.s.append('</svg>')
        OUT.mkdir(parents=True,exist_ok=True)
        path=OUT/(self.name+".svg")
        path.write_text("\n".join(self.s)+"\n")
        import cairosvg
        cairosvg.svg2png(url=str(path),write_to=str(path.with_suffix('.png')),scale=1.4)
        return {"file":self.name,"width":self.w,"height":self.h,"text_elements":len(self.text_boxes),
                "svg_sha256":hashlib.sha256(path.read_bytes()).hexdigest()}


def pe():
    d=Drawing("processing_element","Processing element: exact INT8 MAC with local INT32 state",
              "Registered A/B forwarding is independent of zero suppression. Accumulator and forwarding enables are shown explicitly.",1800,1110)
    d.section(330,140,1400,217,"Operand forwarding")
    d.section(330,380,1400,420,"Local output-stationary datapath")
    # Raw operand taps and forwarding registers.
    d.text(55,250,"a_in[7:0]",20,bold=True,mono=True)
    d.text(55,278,"+ a_valid",15,color=GRAY)
    d.text(55,500,"b_in[7:0]",20,bold=True,mono=True)
    d.text(55,528,"+ b_valid",15,color=GRAY)
    d.bus([(205,240),(390,240),(390,485),(500,485)],8,at=(265,240))
    d.bus([(205,490),(350,490),(350,665),(500,665)],8,at=(265,490))
    d.dot(300,240);d.bus([(300,240),(300,205),(1120,205)],9,at=(800,205))
    d.dot(275,490);d.bus([(275,490),(275,305),(1490,305)],9,at=(800,305))
    d.reg(1120,162,210,90,"A + valid",9,enable="step",clear="rst | clear")
    d.reg(1490,262,210,90,"B + valid",9,enable="step",clear="rst | clear")
    d.bus([(1330,207),(1710,207)],9,at=(1530,207))
    d.text(1510,181,"a_out + a_out_valid",15,anchor="middle",mono=True)
    d.bus([(1700,307),(1750,307),(1750,378)],9,at=(1725,307))
    d.text(1470,373,"b_out + b_out_valid",15,mono=True)
    # Isolation muxes: one=raw data, zero=0, select=executed.
    d.mux(500,450,80,140)
    d.mux(500,630,80,140)
    d.bus([(450,555),(500,555)],8,at=(465,555));d.text(436,562,"0",18,anchor="end")
    d.bus([(450,735),(500,735)],8,at=(465,735));d.text(436,742,"0",18,anchor="end")
    d.op(760,600,48,"x")
    d.bus([(580,520),(645,520),(645,580),(717,580)],8,at=(620,520))
    d.bus([(580,700),(645,700),(645,620),(717,620)],8,at=(620,700))
    d.text(760,679,"signed 8 x 8",17,anchor="middle")
    d.box(870,558,132,84,"SXT","16 -> 32",size=20)
    d.bus([(808,600),(870,600)],16,at=(837,600))
    d.op(1110,600,40,"+")
    d.bus([(1002,600),(1070,600)],32,at=(1032,600))
    d.reg(1260,550,230,110,"ACC",32,enable="executed",clear="rst | clear")
    d.bus([(1150,600),(1260,600)],32,at=(1195,600))
    d.bus([(1490,605),(1690,605)],32,at=(1580,605))
    d.text(1575,575,"accumulator[31:0]",16,anchor="middle",mono=True)
    d.dot(1540,605)
    d.bus([(1540,605),(1540,742),(1110,742),(1110,640)],32,at=(1320,742))
    d.text(1330,780,"Local feedback; sum does not move to adjacent PEs",15,anchor="middle",color=GRAY)
    # Enable logic, not an invented data-compaction path.
    d.rect(70,860,980,120,fill=GREEN)
    d.text(94,887,"Zero / validity / step logic",21,bold=True)
    d.text(94,929,"attempted = step & a_valid & b_valid & !clear",18,mono=True)
    d.text(94,962,"executed = attempted & (!sparse_en | ((a_in!=0) & (b_in!=0)))",17,mono=True)
    d.line([(540,860),(540,770)],color=TEAL,width=1.8,dash=True,arrow=True)
    d.line([(480,860),(480,610),(540,610),(540,590)],color=TEAL,width=1.8,dash=True,arrow=True)
    d.line([(1050,920),(1375,920),(1375,660)],color=TEAL,width=1.8,dash=True,arrow=True)
    d.text(1155,959,"All registers: posedge clk",16,color=GRAY)
    d.text(1155,984,"No change to token order in sparse mode",16,color=GRAY)
    return d.save()


def array():
    d=Drawing("systolic_array","5 x 5 systolic array: explicit inter-PE operand paths",
              "Each input bundle is one INT8 operand plus one valid bit. Skew delays count advance pulses, not wall-clock stalls.",1740,1320)
    X,Y,DX,DY,W,H=530,405,210,150,144,108
    # Column skew chains contain exactly c registers.
    for c in range(5):
        x=X+c*DX+W/2
        d.text(x,143,f"B[{c}] + valid",17,anchor="middle",bold=True)
        last=163
        for j in range(c):
            yy=181+j*43
            d.bus([(x,last),(x,yy)],arrow=True)
            d.rect(x-21,yy,42,31,BLUE)
            d.line([(x-21,yy+21),(x-13,yy+26),(x-21,yy+30)],width=1)
            d.text(x,yy+20,"D",13,anchor="middle")
            last=yy+31
        d.bus([(x,last),(x,Y)],9,at=(x,369))
        d.text(x+34,344,f"{c}D",14,color=TEAL)
    # Row skew chains contain exactly r registers.
    for r in range(5):
        y=Y+r*DY+H/2
        d.text(48,y-22,f"A[{r}] + valid",17,bold=True)
        last=190
        for j in range(r):
            xx=212+j*61
            d.bus([(last,y),(xx,y)],arrow=True)
            d.rect(xx,y-21,42,42,BLUE)
            d.line([(xx,y+10),(xx+9,y+15),(xx,y+20)],width=1)
            d.text(xx+23,y+5,"D",14,anchor="middle")
            last=xx+42
        d.bus([(last,y),(X,y)],9,at=(480,y))
        d.text(465,y+35,f"{r}D",14,color=TEAL)
    for r in range(5):
        for c in range(5):
            x=X+c*DX;y=Y+r*DY
            d.rect(x,y,W,H)
            d.text(x+W/2,y+24,f"PE({r},{c})",17,anchor="middle",bold=True)
            d.op(x+37,y+49,13,"x")
            d.op(x+82,y+49,13,"+")
            d.line([(x+50,y+49),(x+69,y+49)],width=1.4,arrow=True)
            d.rect(x+15,y+77,W-30,23,BLUE,width=1)
            d.text(x+W/2,y+94,"ACC 32b",13,anchor="middle",bold=True)
            if c<4:d.bus([(x+W,y+H/2),(x+DX,y+H/2)],9,at=(x+W+32,y+H/2))
            if r<4:d.bus([(x+W/2,y+H),(x+W/2,y+DY)],9,at=(x+W/2,y+H+22))
    # Meaning of the local accumulator bank and shared control.
    d.text(530,1203,"25 local sums x 32b = 800b; output selection is outside the mesh.",19,bold=True)
    d.text(530,1231,"A moves east. B moves south. All forwarding and skew stages share step.",17,color=GRAY)
    d.text(48,1203,"Shared control",17,color=TEAL,bold=True)
    d.line([(48,1224),(400,1224)],color=TEAL,width=1.6,dash=True,arrow=True)
    d.text(48,1246,"step / clear / sparse_en",16,color=TEAL,mono=True)
    return d.save()


def architecture():
    d=Drawing("architecture","FashionLeNet: hardware datapath and shared memory interface",
              "The five weighted layers reuse one 5 x 5 output-stationary array; the byte-wide memory port gathers each boundary vector.",2110,1150)
    d.section(750,135,1300,870,"lenet_core: compute and output datapaths")
    d.memory(65,280,300,420,"L2: 80 KiB RAM",["Parameters: 64 KiB","Activation A: 8 KiB","Activation B: 8 KiB","Response delay: 1 / 4 clk"])
    d.text(65,221,"Host byte loader",20,bold=True)
    d.bus([(215,235),(215,280)],"17A / 8D",at=(215,250))
    d.text(65,751,"host_ready = !busy & !start",16,mono=True)
    d.box(445,330,235,245,"L1 cache","1 KiB / direct mapped",fill=GREEN)
    d.text(562,515,"64 lines x 16 bytes",16,anchor="middle")
    d.text(562,544,"cache_en / bypass",16,anchor="middle",color=TEAL)
    d.bus([(445,385),(365,385)],"17A",at=(400,385))
    d.text(400,348,"write / read",13,anchor="middle")
    d.bus([(365,490),(445,490)],8,at=(402,490))
    d.text(398,530,"rsp_data",14,anchor="middle")
    d.box(795,200,260,115,"Address / tile logic","m0, n0, k_index, lane",fill=GREEN)
    d.box(800,360,210,170,"Byte gather","lane write enables",fill=PAPER)
    d.bus([(680,452),(800,452)],8,at=(737,452))
    d.text(735,416,"rsp_data",15,anchor="middle")
    d.reg(1090,239,185,93,"A_pack",40,enable="A_WAIT")
    d.reg(1090,419,185,93,"B_pack",40,enable="B_WAIT")
    d.bus([(1010,405),(1050,405),(1050,285),(1090,285)],40,at=(1050,353))
    d.bus([(1010,490),(1050,490),(1050,465),(1090,465)],40,at=(1030,490))
    d.box(1330,239,165,93,"A skew","0,1,2,3,4D",fill=BLUE)
    d.box(1330,419,165,93,"B skew","0,1,2,3,4D",fill=BLUE)
    d.bus([(1275,285),(1330,285)],40,at=(1302,285))
    d.bus([(1275,465),(1330,465)],40,at=(1302,465))
    d.rect(1575,235,390,315,fill=PAPER)
    d.text(1770,273,"5 x 5 PE mesh",23,anchor="middle",bold=True)
    for r in range(5):
        for c in range(5):
            x=1615+c*62;y=302+r*43
            d.rect(x,y,44,31,BLUE,width=1.3)
            d.text(x+22,y+21,"PE",13,anchor="middle")
            if c<4:d.line([(x+44,y+15),(x+62,y+15)],width=1.3,arrow=True)
            if r<4:d.line([(x+22,y+31),(x+22,y+43)],width=1.3,arrow=True)
    d.text(1770,535,"Local ACC bank: 25 x 32b",17,anchor="middle")
    d.bus([(1495,285),(1575,285)],40,at=(1535,285))
    d.text(1535,321,"+5 valid",12,anchor="middle",color=GRAY)
    d.bus([(1495,465),(1525,465),(1525,180),(1770,180),(1770,235)],40,at=(1665,180))
    d.text(1615,160,"B north + 5 valid bits",15)
    d.mux(1690,645,100,160,"25:1")
    d.bus([(1770,550),(1770,600),(1660,600),(1660,685),(1690,685)],800,at=(1770,575))
    d.text(1678,830,"pr / pc",15,color=TEAL)
    d.line([(1740,830),(1740,805)],color=TEAL,dash=True,arrow=True,width=1.5)
    d.box(1850,680,190,110,"Bias + scale","INT32 -> INT8",fill=CREAM)
    d.bus([(1790,725),(1850,725)],32,at=(1820,725))
    d.box(1050,755,225,115,"Pool engine","4 x INT8 signed max",fill=PAPER)
    d.box(1325,850,225,105,"Class scan","argmax / 10 logits",fill=PAPER)
    d.bus([(1550,905),(1980,905)],4,at=(1800,905))
    d.text(1795,878,"prediction[3:0]",16,anchor="middle",mono=True)
    d.mux(785,650,150,245,"Req select",flip=True)
    d.bus([(1050,785),(935,785)],"17A / 8D",at=(992,785))
    d.bus([(1325,905),(1090,905),(1090,845),(935,845)],17,at=(1195,905))
    d.bus([(2040,735),(2070,735),(2070,985),(970,985),(970,705),(935,705)],8,at=(1780,985))
    d.text(1495,966,"Quantized writeback / shared activation RAM",16,anchor="middle")
    d.bus([(795,315),(795,610),(860,610),(860,650)],17,at=(830,610))
    d.bus([(785,772),(710,772),(710,370),(680,370)],"17A / 8D / W",at=(710,670))
    d.dot(750,452)
    d.bus([(750,452),(750,590),(1437,590),(1437,850)],8,at=(1350,590))
    d.dot(1162,590)
    d.bus([(1162,590),(1162,755)],8,at=(1162,660))
    d.text(1260,570,"Shared read response; valid qualified by engine",15,anchor="middle",color=GRAY)
    d.box(65,875,610,120,"Layer / memory control FSM","GEMM, pool, shift read and class read arbitration",fill=GREEN)
    d.line([(675,930),(750,930),(750,1028),(2085,1028),(2085,445),(1965,445)],color=TEAL,width=1.6,dash=True,arrow=True)
    d.text(1195,1055,"Shared step / clear / sparse_en and engine start/done",16,color=TEAL,anchor="middle")
    d.text(65,818,"One outstanding ready/valid transaction",16,color=GRAY)
    return d.save()


def memory():
    d=Drawing("memory_hierarchy","Direct-mapped L1: tag lookup, byte storage and miss refill",
              "The diagram follows read_cache.sv: 1024 x 8 data bits, 64 x 7 tags, 64 valid bits, and a held response register.",1840,1190)
    d.text(55,163,"req_addr[16:0]",20,bold=True,mono=True)
    for x,w,title in [(55,430,"TAG [16:10] / 7b"),(485,390,"INDEX [9:4] / 6b"),(875,270,"OFFSET [3:0] / 4b")]:
        d.box(x,185,w,68,title,fill=BLUE,size=20)
    d.bus([(200,253),(200,395),(440,395)],7,at=(200,325))
    d.memory(440,345,240,150,"TAG RAM",["64 x 7b"])
    d.memory(440,550,240,150,"VALID",["64 x 1b"])
    d.memory(890,345,310,225,"DATA RAM",["1024 x 8b","addr = {index, offset}"])
    d.bus([(680,253),(680,310),(550,310),(550,345)],6,at=(630,310))
    d.dot(680,310)
    d.bus([(680,310),(725,310),(725,600),(680,600)],6,at=(725,525))
    d.box(960,280,100,55,"CAT",fill=PAPER,size=17)
    d.bus([(820,253),(820,308),(960,308)],6,at=(900,308))
    d.bus([(1010,253),(1010,280)],4,at=(1010,263))
    d.bus([(1060,308),(1130,308),(1130,345)],10,at=(1094,308))
    d.box(750,390,85,75,"=",fill=PAPER,size=34)
    d.bus([(680,420),(750,420)],7,at=(712,420))
    d.bus([(270,253),(270,285),(792,285),(792,390)],7,at=(465,285))
    d.box(770,605,120,65,"AND",fill=PAPER,size=20)
    d.line([(792,465),(792,605)],color=TEAL,width=1.7,arrow=True)
    d.line([(680,635),(770,635)],color=TEAL,width=1.7,arrow=True)
    d.text(700,663,"valid",14,color=TEAL)
    d.line([(890,637),(962,637),(962,805)],color=TEAL,width=1.7,arrow=True)
    d.text(928,684,"hit",17,color=TEAL,bold=True)
    d.reg(1380,417,220,105,"rsp_data",8,enable="hit / refill",clear="rst | flush")
    d.mux(1250,390,80,160)
    d.bus([(1200,430),(1250,430)],8,at=(1224,430))
    d.bus([(1330,470),(1380,470)],8,at=(1355,470))
    d.bus([(1600,470),(1775,470)],8,at=(1680,470))
    d.text(1695,425,"Core response",18,anchor="middle",bold=True)
    d.text(1685,552,"held until rsp_ready",15,anchor="middle",color=GRAY)
    d.memory(1395,685,345,260,"L2: 80 KiB RAM",["17-bit byte address","8-bit read / write data","Response delay: 4 clocks"])
    d.bus([(1395,785),(1210,785),(1210,510),(1250,510)],8,at=(1210,640))
    d.text(1227,616,"L2 return",15)
    d.dot(1210,730)
    d.bus([(1210,730),(1100,730),(1100,570)],8,at=(1170,730))
    d.text(1090,700,"refill byte",15,anchor="end")
    d.box(765,805,430,155,"Miss / response FSM","IDLE -> SEND -> WAIT_L2 -> RESP",fill=GREEN,size=22)
    d.bus([(1195,865),(1395,865)],17,at=(1295,865))
    d.text(1295,830,"{addr[16:4], fill_offset}",13,anchor="middle",mono=True)
    d.text(1298,918,"+ WDATA / WRITE",14,anchor="middle")
    d.line([(1150,805),(1150,640),(1290,640),(1290,550)],color=TEAL,width=1.5,dash=True,arrow=True)
    d.line([(1040,805),(1040,605),(1490,605),(1490,522)],color=TEAL,width=1.5,dash=True,arrow=True)
    d.text(1440,592,"hit or requested refill offset",14,color=TEAL,anchor="middle")
    d.box(55,825,560,135,"Write-through / invalidate","No write allocation; no dirty lines; no prefetch",fill=CREAM,size=22)
    d.text(55,1030,"Miss refill: 16 independent byte transactions. Direct mapping needs no LRU state.",19,bold=True)
    d.text(55,1063,"cache_en=0 bypasses L1. flush at each accepted start clears valid bits and cache counters.",17,color=GRAY)
    return d.save()


def postprocess():
    d=Drawing("postprocess_datapath","Bias, rounding and saturation: the integer output datapath",
              "Combinational requantization follows a completed INT32 dot product. Magnitude arithmetic is 33 bits, including abs(INT32_MIN).",1960,1070)
    d.text(55,230,"selected_sum[31:0]",20,bold=True,mono=True)
    d.bus([(55,258),(310,258)],32,at=(205,258))
    d.op(350,258,40,"+")
    d.reg(90,425,230,110,"BIAS",32,enable="BIAS_WAIT")
    d.text(90,581,"Four little-endian byte reads",16,color=GRAY)
    d.bus([(205,425),(205,370),(350,370),(350,298)],32,at=(282,370))
    d.box(465,210,220,95,"ABS / sign","signed 32 -> mag 33",fill=PAPER)
    d.bus([(390,258),(465,258)],32,at=(427,258))
    d.bus([(685,258),(780,258)],33,at=(735,258))
    d.op(820,258,40,"+")
    d.box(700,450,245,120,"Round constant","shift=0 ? 0 : 1<<(shift-1)",fill=CREAM,size=22)
    d.bus([(820,450),(820,298)],33,at=(820,365))
    d.box(955,210,230,95,"Barrel shift",">> shift[5:0]",fill=PAPER)
    d.bus([(860,258),(955,258)],33,at=(908,258))
    d.box(1280,210,225,95,"Restore sign","signed 33b",fill=PAPER)
    d.bus([(1185,258),(1280,258)],33,at=(1230,258))
    d.line([(575,305),(575,365),(1392,365),(1392,305)],color=TEAL,width=1.8,dash=True,arrow=True)
    d.text(1080,392,"saved sign bit",16,color=TEAL,anchor="middle")
    d.box(1590,188,290,140,"Clip / ReLU","[-128,127] or [0,127]",fill=CREAM,size=22)
    d.bus([(1505,258),(1590,258)],33,at=(1547,258))
    d.bus([(1735,328),(1735,695),(1875,695)],8,at=(1735,480))
    d.text(1815,662,"req_data[7:0]",18,anchor="middle",mono=True)
    d.text(1815,735,"INT8 writeback",18,anchor="middle",bold=True)
    d.reg(1040,665,230,110,"SHIFT",6,enable="SHIFT_WAIT")
    d.text(1040,820,"One scale setting per layer",16,color=GRAY)
    d.line([(1155,665),(1155,585),(1070,585),(1070,305)],color=TEAL,dash=True,arrow=True,width=1.7)
    d.line([(1155,585),(820,585),(820,570)],color=TEAL,dash=True,arrow=True,width=1.7)
    d.dot(1155,585,TEAL)
    d.text(1345,535,"relu = (layer != 4)",18,color=TEAL,mono=True)
    d.line([(1570,530),(1640,530),(1640,328)],color=TEAL,dash=True,arrow=True,width=1.7)
    d.text(55,910,"Rounding: nearest with ties away from zero. Bias is added once, after the full reduction.",20,bold=True)
    d.text(55,947,"No floating-point multiply, divide, exponent or softmax is used in this output path.",18,color=GRAY)
    return d.save()


def controller():
    d=Drawing("controller_fsm","Layer controller: actual RTL state transitions",
              "States and guards are taken from lenet_core.sv. Unlabeled sequential transitions occur on the next clock.",1870,1190)
    def node(x,y,label,sub=None,fill=PAPER):
        d.box(x,y,240,90,label,sub,fill,size=21)
    # Main compute row.
    node(55,190,"IDLE","start: layer <- 0",GREEN)
    node(410,190,"SHIFT_REQ","req_addr = 65520+layer")
    node(765,190,"SHIFT_WAIT","latch 6-bit shift")
    node(1120,190,"GSTART","gemm.start = 1",GREEN)
    node(1475,190,"GWAIT","wait for gdone")
    for x in [295,650,1005,1360]:d.line([(x,235),(x+115,235)],arrow=True)
    d.text(348,220,"start",15,color=TEAL,anchor="middle")
    d.text(705,220,"req_ready",15,color=TEAL,anchor="middle")
    d.text(1062,220,"rsp_valid",15,color=TEAL,anchor="middle")
    # Pool branch for first two weighted layers.
    node(1475,455,"PSTART","pool.start = 1",GREEN)
    node(1120,455,"PWAIT","wait for pdone")
    d.line([(1595,280),(1595,455)],arrow=True)
    d.text(1573,400,"gdone & layer<2",16,color=TEAL,anchor="end")
    d.line([(1475,500),(1360,500)],arrow=True)
    d.line([(1120,500),(530,500),(530,280)],arrow=True)
    d.text(790,482,"pdone: layer <- layer+1",17,color=TEAL,anchor="middle")
    # Conv3 / FC1 go straight to next shift read.
    d.line([(1715,235),(1798,235),(1798,350),(530,350),(530,280)],arrow=True)
    d.text(1110,335,"gdone & (layer=2 or 3): layer <- layer+1",17,color=TEAL,anchor="middle")
    # Final class scan branch.
    node(1475,750,"ARG_START","arg_index <- 0",GREEN)
    node(1120,750,"ARG_REQ","read logit[arg_index]")
    node(765,750,"ARG_WAIT","feed argmax.valid")
    node(410,750,"ARG_DONE","wait for adone")
    d.line([(1715,260),(1755,260),(1755,795),(1715,795)],arrow=True)
    d.text(1737,661,"gdone",16,color=TEAL,anchor="end")
    d.text(1737,685,"layer=4",16,color=TEAL,anchor="end")
    for x in [1475,1120,765]:d.line([(x,795),(x-115,795)],arrow=True)
    d.text(1062,778,"req_ready",15,color=TEAL,anchor="middle")
    d.text(707,864,"rsp_valid & index=9",14,color=TEAL,anchor="middle")
    d.line([(885,840),(885,930),(1240,930),(1240,840)],arrow=True)
    d.text(1060,960,"rsp_valid & index<9: index++",16,color=TEAL,anchor="middle")
    d.line([(530,840),(530,1035),(175,1035),(175,280)],arrow=True)
    d.text(340,1066,"adone: busy <- 0; done <- 1",17,color=TEAL,anchor="middle")
    d.text(410,590,"Engine selection",19,bold=True)
    d.text(410,625,"GWAIT: GEMM owns req/rsp",18)
    d.text(410,658,"PWAIT: pool owns req/rsp",18)
    d.text(410,691,"SHIFT / ARG: controller owns req/rsp",18)
    return d.save()


def generate():
    records=[architecture(),pe(),array(),memory(),postprocess(),controller()]
    (OUT/"hardware_figures_manifest.json").write_text(json.dumps({"style":"RTL circuit schematics","figures":records},indent=2)+"\n")
    return records


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--package",action="store_true")
    a=p.parse_args()
    records=generate()
    if a.package:
        target=ROOT.parent/"FashionLeNet-Hardware-Figures.zip"
        with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as z:
            for r in records:
                for ext in ["svg","png"]:
                    path=OUT/(r["file"]+"."+ext);z.write(path,"FashionLeNet-Hardware-Figures/"+path.name)
            z.write(Path(__file__),"FashionLeNet-Hardware-Figures/source/hardware_figures.py")
            z.write(OUT/"hardware_figures_manifest.json","FashionLeNet-Hardware-Figures/manifest.json")
            z.write(OUT/"README.md","FashionLeNet-Hardware-Figures/README.md")
            z.writestr("FashionLeNet-Hardware-Figures/requirements.txt","pillow>=10\ncairosvg>=2.7\nmatplotlib>=3.7\n")
            if (ROOT/"LICENSE").exists():z.write(ROOT/"LICENSE","FashionLeNet-Hardware-Figures/LICENSE")
        print(target)
    print("Generated six hardware schematics (SVG + PNG)")


if __name__=="__main__":main()
