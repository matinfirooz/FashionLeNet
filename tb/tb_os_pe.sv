`timescale 1ns/1ps
module tb_os_pe;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,clear=0,step=0,sparse_en=0,av=0,bv=0;
    reg signed [7:0] a=0,b=0;
    wire signed [7:0] ao,bo;
    wire aov,bov,attempted,executed;
    wire signed [31:0] acc;
    integer i,expected=0,act_count=0,exe_count=0,mode;
    os_pe dut(.clk(clk),.rst(rst),.clear(clear),.step(step),.sparse_en(sparse_en),
        .a_in(a),.b_in(b),.a_valid(av),.b_valid(bv),.a_out(ao),.b_out(bo),
        .a_out_valid(aov),.b_out_valid(bov),.accumulator(acc),.attempted(attempted),.executed(executed));
    initial begin
        $dumpfile("build/os_pe.vcd");$dumpvars(0,tb_os_pe);
        repeat(2) @(negedge clk);rst=0;
        for(mode=0;mode<2;mode=mode+1) begin
            clear=1;@(negedge clk);clear=0;expected=0;sparse_en=mode;
            for(i=0;i<400;i=i+1) begin
                a=(i%7==0)?0:((i*31)%256)-128;
                b=(i%5==0)?0:((i*17)%256)-128;
                if(i==1) begin a=-128;b=-128;end
                av=(i%11!=0);bv=(i%13!=0);step=(i%3!=0);
                #1;
                if(attempted !== (step&&av&&bv)) $fatal(1,"attempted mismatch");
                if(executed !== (step&&av&&bv&&(!mode||(a!=0&&b!=0)))) $fatal(1,"executed mismatch");
                if(step&&av&&bv) expected=expected+$signed(a)*$signed(b);
                @(posedge clk);#1;
                if(acc!==expected) $fatal(1,"PE accumulator %d != %d",acc,expected);
                if(step && (ao!==a || bo!==b || aov!==av || bov!==bv)) $fatal(1,"pipeline mismatch");
                @(negedge clk);
            end
        end
        clear=1;@(negedge clk);if(acc!==0)$fatal(1,"clear failed");
        $display("PASS tb_os_pe: 800 transactions, signed extremes, sparse/dense, stalls, clear");$finish;
    end
endmodule
