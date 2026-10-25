`timescale 1ns/1ps
module pool2x2(input wire signed [7:0] a,b,c,d, output wire signed [7:0] maximum);
    wire signed [7:0] ab=(a>b)?a:b;
    wire signed [7:0] cd=(c>d)?c:d;
    assign maximum=(ab>cd)?ab:cd;
endmodule
