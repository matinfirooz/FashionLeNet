`timescale 1ns/1ps
// Portable synchronous host interface; board-specific UART/AXI/DDR is external.
module fpga_top #(
    parameter integer INPUT_SIZE=32,C1=6,C2=16,C3=120,F1=84,ROWS=5,COLS=5,L2_LATENCY=4
)(
    input wire clk,rst,start,sparse_en,cache_en,
    input wire host_we,
    input wire [16:0] host_addr,
    input wire [7:0] host_data,
    output wire host_ready,busy,done,
    output wire [3:0] prediction,
    output wire [31:0] cycles,mac_attempted,mac_executed,cache_hits,cache_misses,cache_bypasses,
    output wire [3:0] debug_stage
);
    wire req_valid,req_write,req_ready,rsp_valid,rsp_ready;
    wire [16:0] req_addr;
    wire [7:0] req_data,rsp_data;
    wire lv,lw,lr,lrv,lrr;
    wire [16:0] la;
    wire [7:0] ld,lrd;
    reg sparse_latched,cache_latched;
    assign host_ready=!busy && !start;
    always @(posedge clk) begin
        if(rst) begin sparse_latched<=0;cache_latched<=0;end
        else if(start && !busy) begin sparse_latched<=sparse_en;cache_latched<=cache_en;end
    end
    lenet_core #(.INPUT_SIZE(INPUT_SIZE),.C1(C1),.C2(C2),.C3(C3),.F1(F1),.ROWS(ROWS),.COLS(COLS)) core(
        .clk(clk),.rst(rst),.start(start && !busy),.sparse_en(sparse_latched),
        .busy(busy),.done(done),.prediction(prediction),.cycles(cycles),.mac_attempted(mac_attempted),.mac_executed(mac_executed),
        .req_valid(req_valid),.req_write(req_write),.req_ready(req_ready),.req_addr(req_addr),.req_data(req_data),
        .rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_data(rsp_data),.debug_stage(debug_stage));
    read_cache cache(.clk(clk),.rst(rst),.flush(start && !busy),.enable(cache_latched),
        .req_valid(req_valid),.req_write(req_write),.req_ready(req_ready),.req_addr(req_addr),.req_data(req_data),
        .rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_data(rsp_data),
        .l2_valid(lv),.l2_write(lw),.l2_ready(lr),.l2_addr(la),.l2_data(ld),
        .l2_rsp_valid(lrv),.l2_rsp_ready(lrr),.l2_rsp_data(lrd),
        .hits(cache_hits),.misses(cache_misses),.bypasses(cache_bypasses));
    backing_store #(.LATENCY(L2_LATENCY)) l2(.clk(clk),.rst(rst),
        .host_we(host_we && host_ready),.host_addr(host_addr),.host_data(host_data),
        .req_valid(lv),.req_write(lw),.req_ready(lr),.req_addr(la),.req_data(ld),
        .rsp_valid(lrv),.rsp_ready(lrr),.rsp_data(lrd));
endmodule
