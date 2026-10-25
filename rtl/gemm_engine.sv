`timescale 1ns/1ps
// Implicit im2col: rows=output spatial positions, columns=output channels.
// Scalar memory gathers boundary vectors; one global step keeps every PE aligned.
module gemm_engine #(parameter integer ROWS=5,COLS=5)(
    input wire clk,rst,start,sparse_en,
    input wire [16:0] in_base,out_base,weight_base,bias_base,
    input wire [15:0] in_h,in_w,out_h,out_w,in_channels,out_channels,kernel,
    input wire [5:0] shift,
    input wire relu,
    output reg busy,done,
    output reg [31:0] cycles,mac_attempted,mac_executed,
    output reg req_valid,req_write,
    input wire req_ready,
    output reg [16:0] req_addr,
    output reg [7:0] req_data,
    input wire rsp_valid,
    output wire rsp_ready,
    input wire [7:0] rsp_data
);
    localparam IDLE=0,CLEAR=1,A_REQ=2,A_WAIT=3,B_REQ=4,B_WAIT=5,FEED=6,
               FLUSH=7,BIAS_REQ=8,BIAS_WAIT=9,WRITE_REQ=10,WRITE_WAIT=11;
    reg [3:0] state;
    integer m0,n0,k_index,lane,flush_left,pr,pc,bbyte;
    integer m_size,k_size,ic,kr,kc,mpos;
    reg [ROWS*8-1:0] a_pack;
    reg [COLS*8-1:0] b_pack;
    reg [ROWS-1:0] a_valid_pack;
    reg [COLS-1:0] b_valid_pack;
    reg signed [31:0] bias;
    wire clear_array=(state==CLEAR);
    wire step=(state==FEED)||(state==FLUSH);
    wire [ROWS*8-1:0] skewed_a;
    wire [COLS*8-1:0] skewed_b;
    wire [ROWS-1:0] skewed_av;
    wire [COLS-1:0] skewed_bv;
    wire [ROWS*COLS*32-1:0] sums;
    wire [31:0] attempted,executed;
    wire signed [31:0] selected_sum=sums[32*(pr*COLS+pc)+:32];
    wire signed [31:0] biased_sum=selected_sum+bias;
    wire signed [7:0] quantized;
    assign rsp_ready=(state==A_WAIT)||(state==B_WAIT)||(state==BIAS_WAIT)||(state==WRITE_WAIT);
    skew_buffer #(.LANES(ROWS)) a_skew(.clk(clk),.rst(rst),.clear(clear_array),.advance(step),
        .data_in(a_pack),.valid_in(a_valid_pack),.data_out(skewed_a),.valid_out(skewed_av));
    skew_buffer #(.LANES(COLS)) b_skew(.clk(clk),.rst(rst),.clear(clear_array),.advance(step),
        .data_in(b_pack),.valid_in(b_valid_pack),.data_out(skewed_b),.valid_out(skewed_bv));
    os_array #(.ROWS(ROWS),.COLS(COLS)) array(.clk(clk),.rst(rst),.clear(clear_array),.step(step),
        .sparse_en(sparse_en),.a_west(skewed_a),.b_north(skewed_b),
        .a_valid(skewed_av),.b_valid(skewed_bv),.sums(sums),
        .attempted_count(attempted),.executed_count(executed));
    requantize quant(.value(biased_sum),.shift(shift),.relu(relu),.result(quantized));
    always @* begin
        m_size=out_h*out_w;
        k_size=in_channels*kernel*kernel;
        mpos=m0+lane;
        ic=k_index/(kernel*kernel);
        kr=(k_index/kernel)%kernel;
        kc=k_index%kernel;
        req_valid=0; req_write=0; req_addr=0; req_data=0;
        case(state)
            A_REQ: if (mpos<m_size) begin
                req_valid=1;
                req_addr=in_base+ic*in_h*in_w+(mpos/out_w+kr)*in_w+mpos%out_w+kc;
            end
            B_REQ: if (n0+lane<out_channels) begin
                req_valid=1; req_addr=weight_base+(n0+lane)*k_size+k_index;
            end
            BIAS_REQ: begin req_valid=1; req_addr=bias_base+4*(n0+pc)+bbyte; end
            WRITE_REQ: begin
                req_valid=1; req_write=1; req_addr=out_base+(n0+pc)*m_size+m0+pr;
                req_data=quantized;
            end
            default: begin end
        endcase
    end
    always @(posedge clk) begin
        if (rst) begin
            state<=IDLE; busy<=0; done<=0; cycles<=0; mac_attempted<=0; mac_executed<=0;
            m0<=0; n0<=0; k_index<=0; lane<=0; flush_left<=0;
            pr<=0; pc<=0; bbyte<=0; bias<=0;
            a_pack<=0; b_pack<=0; a_valid_pack<=0; b_valid_pack<=0;
        end else begin
            done<=0;
            if (busy) cycles<=cycles+1;
            if (step) begin mac_attempted<=mac_attempted+attempted; mac_executed<=mac_executed+executed; end
            case(state)
                IDLE: if (start) begin
                    busy<=1; cycles<=0; mac_attempted<=0; mac_executed<=0;
                    m0<=0; n0<=0; state<=CLEAR;
                end
                CLEAR: begin
                    a_pack<=0; b_pack<=0; a_valid_pack<=0; b_valid_pack<=0;
                    k_index<=0; lane<=0; state<=A_REQ;
                end
                A_REQ: begin
                    if (m0+lane>=m_size) begin
                        a_pack[8*lane+:8]<=0; a_valid_pack[lane]<=0;
                        if (lane==ROWS-1) begin lane<=0; state<=B_REQ; end else lane<=lane+1;
                    end else if (req_ready) state<=A_WAIT;
                end
                A_WAIT: if (rsp_valid) begin
                    a_pack[8*lane+:8]<=rsp_data; a_valid_pack[lane]<=1;
                    if (lane==ROWS-1) begin lane<=0; state<=B_REQ; end
                    else begin lane<=lane+1; state<=A_REQ; end
                end
                B_REQ: begin
                    if (n0+lane>=out_channels) begin
                        b_pack[8*lane+:8]<=0; b_valid_pack[lane]<=0;
                        if (lane==COLS-1) begin lane<=0; state<=FEED; end else lane<=lane+1;
                    end else if (req_ready) state<=B_WAIT;
                end
                B_WAIT: if (rsp_valid) begin
                    b_pack[8*lane+:8]<=rsp_data; b_valid_pack[lane]<=1;
                    if (lane==COLS-1) begin lane<=0; state<=FEED; end
                    else begin lane<=lane+1; state<=B_REQ; end
                end
                FEED: begin
                    a_valid_pack<=0; b_valid_pack<=0; a_pack<=0; b_pack<=0;
                    if (k_index==k_size-1) begin
                        if (ROWS+COLS==2) begin pr<=0; pc<=0; bbyte<=0; bias<=0; state<=BIAS_REQ; end
                        else begin flush_left<=ROWS+COLS-2; state<=FLUSH; end
                    end else begin k_index<=k_index+1; lane<=0; state<=A_REQ; end
                end
                FLUSH: begin
                    if (flush_left==1) begin
                        pr<=0; pc<=0; bbyte<=0; bias<=0; state<=BIAS_REQ;
                    end else flush_left<=flush_left-1;
                end
                BIAS_REQ: if (req_ready) state<=BIAS_WAIT;
                BIAS_WAIT: if (rsp_valid) begin
                    bias[8*bbyte+:8]<=rsp_data;
                    if (bbyte==3) state<=WRITE_REQ;
                    else begin bbyte<=bbyte+1; state<=BIAS_REQ; end
                end
                WRITE_REQ: if (req_ready) state<=WRITE_WAIT;
                WRITE_WAIT: if (rsp_valid) begin
                    bbyte<=0; bias<=0;
                    if (pc+1<COLS && n0+pc+1<out_channels) begin pc<=pc+1; state<=BIAS_REQ; end
                    else if (pr+1<ROWS && m0+pr+1<m_size) begin pr<=pr+1; pc<=0; state<=BIAS_REQ; end
                    else if (n0+COLS<out_channels) begin n0<=n0+COLS; state<=CLEAR; end
                    else if (m0+ROWS<m_size) begin m0<=m0+ROWS; n0<=0; state<=CLEAR; end
                    else begin busy<=0; done<=1; state<=IDLE; end
                end
                default: state<=IDLE;
            endcase
        end
    end
endmodule
