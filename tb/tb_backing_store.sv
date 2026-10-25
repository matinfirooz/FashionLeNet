`timescale 1ns/1ps
module tb_backing_store;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,hw=0,qv=0,qw=0,rr=0;reg[16:0] ha=0,qa=0;reg[7:0] hd=0,qd=0;
    wire qr,rv;wire[7:0] rd;integer n;
    backing_store #(.DEPTH(256),.LATENCY(4)) dut(.clk(clk),.rst(rst),.host_we(hw),.host_addr(ha),.host_data(hd),
        .req_valid(qv),.req_write(qw),.req_ready(qr),.req_addr(qa),.req_data(qd),.rsp_valid(rv),.rsp_ready(rr),.rsp_data(rd));
    initial begin
        repeat(2)@(negedge clk);rst=0;hw=1;ha=33;hd=8'ha5;@(negedge clk);hw=0;
        qv=1;qa=33;@(posedge clk);#1;if(rv)$fatal(1,"early memory response");
        @(negedge clk);qv=0;
        for(n=1;n<=4;n=n+1)begin
            @(posedge clk);#1;
            if(n<4&&rv)$fatal(1,"L2 early response");
            if(n==4&&(!rv||rd!==8'ha5))$fatal(1,"L2 latency/data");
        end
        repeat(3)begin @(negedge clk);if(!rv||rd!==8'ha5||qr)$fatal(1,"response hold");end
        rr=1;@(negedge clk);rr=0;
        qw=1;qv=1;qd=8'h42;@(negedge clk);qv=0;
        wait(rv);@(negedge clk);rr=1;@(negedge clk);rr=0;
        if(dut.memory[33]!==8'h42)$fatal(1,"write failed");
        $display("PASS tb_backing_store: exact latency, host load, write, held response");$finish;
    end
    initial begin #10000;$fatal(1,"timeout");end
endmodule
