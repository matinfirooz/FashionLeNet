`timescale 1ns/1ps
// Exactly ten valid samples per transaction; ties select the lowest class index.
module argmax10(
    input wire clk,rst,start,valid,
    input wire signed [7:0] value,
    output reg done,
    output reg [3:0] prediction
);
    reg signed [7:0] best;
    reg [3:0] index,best_index;
    always @(posedge clk) begin
        if (rst) begin done<=0; prediction<=0; best<=-128; index<=0; best_index<=0; end
        else begin
            done<=0;
            if (start) begin best<=-128; index<=0; best_index<=0; end
            else if (valid) begin
                if (value>best) begin best<=value; best_index<=index; end
                if (index==9) begin
                    prediction <= (value>best)?index:best_index;
                    done<=1; index<=0;
                end else index<=index+1;
            end
        end
    end
endmodule
