`timescale 1ns/1ps
module os_array #(parameter integer ROWS=5, COLS=5)(
    input wire clk, rst, clear, step, sparse_en,
    input wire [ROWS*8-1:0] a_west,
    input wire [COLS*8-1:0] b_north,
    input wire [ROWS-1:0] a_valid,
    input wire [COLS-1:0] b_valid,
    output wire [ROWS*COLS*32-1:0] sums,
    output reg [31:0] attempted_count, executed_count
);
    wire signed [7:0] a [0:ROWS-1][0:COLS];
    wire signed [7:0] b [0:ROWS][0:COLS-1];
    wire av [0:ROWS-1][0:COLS];
    wire bv [0:ROWS][0:COLS-1];
    wire [ROWS*COLS-1:0] attempt, execute;
    genvar r,c;
    generate
        for (r=0;r<ROWS;r=r+1) begin: row_inputs
            assign a[r][0]=a_west[8*r+:8]; assign av[r][0]=a_valid[r];
        end
        for (c=0;c<COLS;c=c+1) begin: col_inputs
            assign b[0][c]=b_north[8*c+:8]; assign bv[0][c]=b_valid[c];
        end
        for (r=0;r<ROWS;r=r+1) begin: row
            for (c=0;c<COLS;c=c+1) begin: col
                os_pe pe(.clk(clk),.rst(rst),.clear(clear),.step(step),.sparse_en(sparse_en),
                    .a_in(a[r][c]),.b_in(b[r][c]),.a_valid(av[r][c]),.b_valid(bv[r][c]),
                    .a_out(a[r][c+1]),.b_out(b[r+1][c]),
                    .a_out_valid(av[r][c+1]),.b_out_valid(bv[r+1][c]),
                    .accumulator(sums[32*(r*COLS+c)+:32]),
                    .attempted(attempt[r*COLS+c]),.executed(execute[r*COLS+c]));
            end
        end
    endgenerate
    integer j;
    always @* begin
        attempted_count=0; executed_count=0;
        for (j=0;j<ROWS*COLS;j=j+1) begin
            attempted_count=attempted_count+attempt[j];
            executed_count=executed_count+execute[j];
        end
    end
endmodule
