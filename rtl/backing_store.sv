`timescale 1ns/1ps
// Byte-wide L2. read acceptance -> response assertion after LATENCY clocks.
// Host writes are legal only while the accelerator is idle, enforced by fpga_top.
module backing_store #(parameter integer DEPTH=81920, LATENCY=4)(
    input wire clk,rst,
    input wire host_we,
    input wire [16:0] host_addr,
    input wire [7:0] host_data,
    input wire req_valid,req_write,
    output wire req_ready,
    input wire [16:0] req_addr,
    input wire [7:0] req_data,
    output reg rsp_valid,
    input wire rsp_ready,
    output reg [7:0] rsp_data
);
    (* ram_style="block" *) reg [7:0] memory [0:DEPTH-1];
    reg pending;
    integer countdown;
    reg [7:0] pending_data;
    assign req_ready=!pending && !rsp_valid && !host_we;
    always @(posedge clk) begin
        if (host_we && host_addr<DEPTH) memory[host_addr]<=host_data;
        if (rst) begin pending<=0; rsp_valid<=0; rsp_data<=0; countdown<=0; pending_data<=0; end
        else begin
            if (rsp_valid && rsp_ready) rsp_valid<=0;
            if (req_valid && req_ready) begin
                pending<=1; countdown<=LATENCY;
                if (req_write) begin
                    memory[req_addr]<=req_data; pending_data<=0;
                end else pending_data<=memory[req_addr];
            end else if (pending) begin
                if (countdown==1) begin
                    rsp_data<=pending_data; rsp_valid<=1; pending<=0;
                end else countdown<=countdown-1;
            end
        end
    end
endmodule
