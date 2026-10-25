`timescale 1ns/1ps
// 1 KiB direct-mapped, 16-byte lines, write-through/no-write-allocate.
// A miss refills the full line using the byte-wide L2 port. No prefetch.
module read_cache(
    input wire clk,rst,flush,enable,
    input wire req_valid,req_write,
    output wire req_ready,
    input wire [16:0] req_addr,
    input wire [7:0] req_data,
    output wire rsp_valid,
    input wire rsp_ready,
    output reg [7:0] rsp_data,
    output wire l2_valid,l2_write,
    input wire l2_ready,
    output wire [16:0] l2_addr,
    output wire [7:0] l2_data,
    input wire l2_rsp_valid,
    output wire l2_rsp_ready,
    input wire [7:0] l2_rsp_data,
    output reg [31:0] hits,misses,bypasses
);
    localparam IDLE=0,SEND=1,WAIT_L2=2,RESP=3;
    reg [1:0] state;
    reg [7:0] data [0:1023];
    reg [6:0] tags [0:63];
    reg [63:0] valid_bits;
    reg [16:0] address;
    reg [7:0] write_data;
    reg writing,refilling;
    reg [3:0] fill_offset;
    wire [5:0] line_index=address[9:4];
    assign req_ready=(state==IDLE) && !flush;
    assign rsp_valid=(state==RESP);
    assign l2_valid=(state==SEND);
    assign l2_write=writing;
    assign l2_addr=refilling?{address[16:4],fill_offset}:address;
    assign l2_data=write_data;
    assign l2_rsp_ready=(state==WAIT_L2);
    always @(posedge clk) begin
        if (rst || flush) begin
            state<=IDLE; valid_bits<=0; hits<=0; misses<=0; bypasses<=0;
            address<=0; write_data<=0; writing<=0; refilling<=0; fill_offset<=0; rsp_data<=0;
        end else case(state)
            IDLE: if (req_valid) begin
                address<=req_addr; write_data<=req_data; writing<=req_write; fill_offset<=0;
                if (req_write) begin
                    valid_bits[req_addr[9:4]]<=0;
                    refilling<=0; state<=SEND;
                end else if (!enable) begin
                    bypasses<=bypasses+1; refilling<=0; state<=SEND;
                end else if (valid_bits[req_addr[9:4]] && tags[req_addr[9:4]]==req_addr[16:10]) begin
                    hits<=hits+1; rsp_data<=data[req_addr[9:0]]; state<=RESP;
                end else begin
                    misses<=misses+1; refilling<=1; state<=SEND;
                end
            end
            SEND: if (l2_ready) state<=WAIT_L2;
            WAIT_L2: if (l2_rsp_valid) begin
                if (refilling) begin
                    data[{line_index,fill_offset}]<=l2_rsp_data;
                    if (fill_offset==address[3:0]) rsp_data<=l2_rsp_data;
                    if (fill_offset==15) begin
                        tags[line_index]<=address[16:10]; valid_bits[line_index]<=1; state<=RESP;
                    end else begin fill_offset<=fill_offset+1; state<=SEND; end
                end else begin rsp_data<=l2_rsp_data; state<=RESP; end
            end
            RESP: if (rsp_ready) state<=IDLE;
            default: state<=IDLE;
        endcase
    end
endmodule
