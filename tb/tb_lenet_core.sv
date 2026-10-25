`timescale 1ns/1ps
module tb_lenet_core;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,start=0;wire busy,done,qv,qw,qr,rv,rr;wire[16:0] qa;wire[7:0] qd,rd;
    wire[3:0] prediction,stage;wire[31:0] cycles,attempts,execs;integer i;
    lenet_core #(.INPUT_SIZE(28),.C1(1),.C2(2),.C3(3),.F1(4),.ROWS(2),.COLS(3)) dut(
        .clk(clk),.rst(rst),.start(start),.sparse_en(1'b1),.busy(busy),.done(done),.prediction(prediction),
        .cycles(cycles),.mac_attempted(attempts),.mac_executed(execs),
        .req_valid(qv),.req_write(qw),.req_ready(qr),.req_addr(qa),.req_data(qd),
        .rsp_valid(rv),.rsp_ready(rr),.rsp_data(rd),.debug_stage(stage));
    backing_store #(.LATENCY(1)) l2(.clk(clk),.rst(rst),.host_we(1'b0),.host_addr(17'd0),.host_data(8'd0),
        .req_valid(qv),.req_write(qw),.req_ready(qr),.req_addr(qa),.req_data(qd),.rsp_valid(rv),.rsp_ready(rr),.rsp_data(rd));
    initial begin
        for(i=0;i<81920;i=i+1)l2.memory[i]=0;
        repeat(2)@(negedge clk);rst=0;start=1;@(negedge clk);start=0;wait(done);@(negedge clk);
        if(prediction!=0||execs!=0||attempts!=17748)$fatal(1,"core result/counters %d %d %d",prediction,execs,attempts);
        $display("PASS tb_lenet_core: five layers, pools, config widths, all-zero tie inference");$finish;
    end
    initial begin #10000000;$fatal(1,"timeout");end
endmodule
