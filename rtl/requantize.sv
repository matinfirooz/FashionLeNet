`timescale 1ns/1ps
// Magnitude arithmetic is 33 bits, including abs(INT32_MIN).
module requantize(
    input wire signed [31:0] value,
    input wire [5:0] shift,
    input wire relu,
    output reg signed [7:0] result
);
    reg signed [32:0] extended_value, rounded;
    reg [32:0] magnitude;
    always @* begin
        extended_value={value[31],value};
        magnitude = (extended_value<0) ? -extended_value : extended_value;
        if (shift != 0) magnitude=(magnitude+(33'd1<<(shift-1)))>>shift;
        rounded=(extended_value<0) ? -$signed(magnitude) : $signed(magnitude);
        if (relu && rounded<0) result=0;
        else if (rounded>127) result=127;
        else if (rounded < -128) result=-128;
        else result=rounded[7:0];
    end
endmodule
