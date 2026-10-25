`timescale 1ns/1ps
// Lane i is delayed by i *advance pulses*, not i wall-clock cycles.
module skew_buffer #(parameter integer LANES=5)(
    input wire clk, rst, clear, advance,
    input wire [LANES*8-1:0] data_in,
    input wire [LANES-1:0] valid_in,
    output wire [LANES*8-1:0] data_out,
    output wire [LANES-1:0] valid_out
);
    genvar lane;
    generate for (lane=0;lane<LANES;lane=lane+1) begin: lanes
        if (lane==0) begin: direct_lane
            assign data_out[8*lane+:8]=data_in[8*lane+:8];
            assign valid_out[lane]=valid_in[lane];
        end else begin: delayed_lane
            reg [8*lane-1:0] data_delay;
            reg [lane-1:0] valid_delay;
            always @(posedge clk) begin
                if (rst || clear) begin data_delay<=0; valid_delay<=0; end
                else if (advance) begin
                    data_delay <= (data_delay << 8) | data_in[8*lane+:8];
                    valid_delay <= (valid_delay << 1) | valid_in[lane];
                end
            end
            assign data_out[8*lane+:8]=data_delay[8*(lane-1)+:8];
            assign valid_out[lane]=valid_delay[lane-1];
        end
    end endgenerate
endmodule
