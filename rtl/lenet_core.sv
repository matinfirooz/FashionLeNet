`timescale 1ns/1ps
// Five weighted layers, two pools, streaming argmax. Inputs/config stable while busy.
module lenet_core #(
    parameter integer INPUT_SIZE=32,C1=6,C2=16,C3=120,F1=84,ROWS=5,COLS=5
)(
    input wire clk,rst,start,sparse_en,
    output reg busy,done,
    output wire [3:0] prediction,
    output reg [31:0] cycles,mac_attempted,mac_executed,
    output reg req_valid,req_write,
    input wire req_ready,
    output reg [16:0] req_addr,
    output reg [7:0] req_data,
    input wire rsp_valid,
    output reg rsp_ready,
    input wire [7:0] rsp_data,
    output wire [3:0] debug_stage
);
    localparam A=65536,B=73728,H1=INPUT_SIZE-4,P1=H1/2,H2=P1-4,P2=H2/2;
    localparam W0=C1*25,W1=C2*C1*25,W2=C3*C2*P2*P2,W3=F1*C3,W4=10*F1;
    localparam TOTAL_W=W0+W1+W2+W3+W4;
    localparam IDLE=0,SHIFT_REQ=1,SHIFT_WAIT=2,GSTART=3,GWAIT=4,PSTART=5,PWAIT=6,
               ARG_START=7,ARG_REQ=8,ARG_WAIT=9,ARG_DONE=10;
    reg [3:0] state;
    reg [2:0] layer;
    reg [5:0] shift;
    reg [3:0] arg_index;
    reg [16:0] ib,ob,wb,bb;
    reg [15:0] ih,iw,oh,ow,ci,co,ks;
    wire gdone,pdone,adone;
    wire [31:0] gcycles,gattempt,gexecute;
    wire greq,gwrite,grsp_ready,preq,pwrite,prsp_ready;
    wire [16:0] gaddr,paddr;
    wire [7:0] gdata,pdata;
    assign debug_stage=state==PWAIT ? ((layer==0)?4'd2:4'd4) :
                       state==GWAIT ? ((layer==0)?4'd1:(layer==1)?4'd3:(layer==2)?4'd5:(layer==3)?4'd6:4'd7) : 4'd0;
    always @* begin
        ib=A;ob=B;wb=0;bb=TOTAL_W;ih=INPUT_SIZE;iw=INPUT_SIZE;oh=H1;ow=H1;ci=1;co=C1;ks=5;
        case(layer)
            1: begin ib=A;ob=B;wb=W0;bb=TOTAL_W+4*C1;ih=P1;iw=P1;oh=H2;ow=H2;ci=C1;co=C2;ks=5;end
            2: begin ib=A;ob=B;wb=W0+W1;bb=TOTAL_W+4*(C1+C2);ih=P2;iw=P2;oh=1;ow=1;ci=C2;co=C3;ks=P2;end
            3: begin ib=B;ob=A;wb=W0+W1+W2;bb=TOTAL_W+4*(C1+C2+C3);ih=1;iw=1;oh=1;ow=1;ci=C3;co=F1;ks=1;end
            4: begin ib=A;ob=B;wb=W0+W1+W2+W3;bb=TOTAL_W+4*(C1+C2+C3+F1);ih=1;iw=1;oh=1;ow=1;ci=F1;co=10;ks=1;end
            default: begin end
        endcase
    end
    gemm_engine #(.ROWS(ROWS),.COLS(COLS)) gemm(.clk(clk),.rst(rst),.start(state==GSTART),.sparse_en(sparse_en),
        .in_base(ib),.out_base(ob),.weight_base(wb),.bias_base(bb),.in_h(ih),.in_w(iw),.out_h(oh),.out_w(ow),
        .in_channels(ci),.out_channels(co),.kernel(ks),.shift(shift),.relu(layer!=4),
        .busy(),.done(gdone),.cycles(gcycles),.mac_attempted(gattempt),.mac_executed(gexecute),
        .req_valid(greq),.req_write(gwrite),.req_ready(req_ready && state==GWAIT),.req_addr(gaddr),.req_data(gdata),
        .rsp_valid(rsp_valid && state==GWAIT),.rsp_ready(grsp_ready),.rsp_data(rsp_data));
    pool_engine pool(.clk(clk),.rst(rst),.start(state==PSTART),.in_base(17'd73728),.out_base(17'd65536),
        .height(oh),.width(ow),.channels(co),.busy(),.done(pdone),
        .req_valid(preq),.req_write(pwrite),.req_ready(req_ready && state==PWAIT),.req_addr(paddr),.req_data(pdata),
        .rsp_valid(rsp_valid && state==PWAIT),.rsp_ready(prsp_ready),.rsp_data(rsp_data));
    argmax10 argmax(.clk(clk),.rst(rst),.start(state==ARG_START),
        .valid(state==ARG_WAIT && rsp_valid),.value(rsp_data),.done(adone),.prediction(prediction));
    always @* begin
        req_valid=0;req_write=0;req_addr=0;req_data=0;rsp_ready=0;
        case(state)
            SHIFT_REQ: begin req_valid=1;req_addr=65520+layer;end
            SHIFT_WAIT: rsp_ready=1;
            GWAIT: begin req_valid=greq;req_write=gwrite;req_addr=gaddr;req_data=gdata;rsp_ready=grsp_ready;end
            PWAIT: begin req_valid=preq;req_write=pwrite;req_addr=paddr;req_data=pdata;rsp_ready=prsp_ready;end
            ARG_REQ: begin req_valid=1;req_addr=B+arg_index;end
            ARG_WAIT: rsp_ready=1;
            default: begin end
        endcase
    end
    always @(posedge clk) begin
        if (rst) begin
            state<=IDLE;layer<=0;shift<=0;busy<=0;done<=0;cycles<=0;mac_attempted<=0;mac_executed<=0;arg_index<=0;
        end else begin
            done<=0;
            if (busy) cycles<=cycles+1;
            case(state)
                IDLE: if (start) begin
                    layer<=0;busy<=1;cycles<=0;mac_attempted<=0;mac_executed<=0;state<=SHIFT_REQ;
                end
                SHIFT_REQ: if (req_ready) state<=SHIFT_WAIT;
                SHIFT_WAIT: if (rsp_valid) begin shift<=rsp_data[5:0];state<=GSTART;end
                GSTART: state<=GWAIT;
                GWAIT: if (gdone) begin
                    mac_attempted<=mac_attempted+gattempt;mac_executed<=mac_executed+gexecute;
                    if (layer<2) state<=PSTART;
                    else if (layer<4) begin layer<=layer+1;state<=SHIFT_REQ;end
                    else state<=ARG_START;
                end
                PSTART: state<=PWAIT;
                PWAIT: if (pdone) begin layer<=layer+1;state<=SHIFT_REQ;end
                ARG_START: begin arg_index<=0;state<=ARG_REQ;end
                ARG_REQ: if (req_ready) state<=ARG_WAIT;
                ARG_WAIT: if (rsp_valid) begin
                    if (arg_index==9) state<=ARG_DONE;
                    else begin arg_index<=arg_index+1;state<=ARG_REQ;end
                end
                ARG_DONE: if (adone) begin busy<=0;done<=1;state<=IDLE;end
                default: state<=IDLE;
            endcase
        end
    end
endmodule
