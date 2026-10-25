`timescale 1ns/1ps
module tb_argmax10;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,start=0,valid=0;reg signed[7:0] value=0;
    wire done;wire[3:0] prediction;integer i;
    argmax10 dut(.clk(clk),.rst(rst),.start(start),.valid(valid),.value(value),.done(done),.prediction(prediction));
    initial begin
        repeat(2)@(negedge clk);rst=0;start=1;@(negedge clk);start=0;
        for(i=0;i<10;i=i+1)begin
            valid=0;@(negedge clk);valid=1;value=(i==3||i==7)?50:-50;@(negedge clk);
        end
        valid=0;if(!done||prediction!=3)$fatal(1,"tie/bubble argmax");
        start=1;@(negedge clk);start=0;
        for(i=0;i<10;i=i+1)begin valid=1;value=-128;@(negedge clk);end
        valid=0;if(!done||prediction!=0)$fatal(1,"all INT8_MIN tie");
        $display("PASS tb_argmax10");$finish;
    end
endmodule
