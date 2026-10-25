`timescale 1ns/1ps
// INT8 x INT8 -> INT32 output-stationary accumulator. Every pipeline shares step.
module os_pe (
    input wire clk, rst, clear, step, sparse_en,
    input wire signed [7:0] a_in, b_in,
    input wire a_valid, b_valid,
    output reg signed [7:0] a_out, b_out,
    output reg a_out_valid, b_out_valid,
    output reg signed [31:0] accumulator,
    output wire attempted, executed
);
    assign attempted = step && a_valid && b_valid && !clear;
    assign executed = attempted && (!sparse_en || ((a_in != 0) && (b_in != 0)));
    // Operand isolation avoids presenting changing operands to an unused multiplier.
    wire signed [7:0] mul_a = executed ? a_in : 8'sd0;
    wire signed [7:0] mul_b = executed ? b_in : 8'sd0;
    wire signed [15:0] product = mul_a * mul_b;
    always @(posedge clk) begin
        if (rst || clear) begin
            a_out <= 0; b_out <= 0; a_out_valid <= 0; b_out_valid <= 0;
            accumulator <= 0;
        end else if (step) begin
            a_out <= a_in; b_out <= b_in;
            a_out_valid <= a_valid; b_out_valid <= b_valid;
            if (executed) accumulator <= accumulator + {{16{product[15]}},product};
        end
    end
endmodule
