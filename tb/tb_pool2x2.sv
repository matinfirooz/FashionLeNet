`timescale 1ns/1ps
module tb_pool2x2;
    reg signed[7:0] a,b,c,d;wire signed[7:0] maximum;
    integer i,expected;
    pool2x2 dut(.a(a),.b(b),.c(c),.d(d),.maximum(maximum));
    initial begin
        for(i=0;i<512;i=i+1)begin
            a=i;b=i*17;c=i*33;d=i*67;
            expected=$signed(a);if($signed(b)>expected)expected=$signed(b);
            if($signed(c)>expected)expected=$signed(c);if($signed(d)>expected)expected=$signed(d);
            #1;if($signed(maximum)!==expected)$fatal(1,"pool signed compare");
        end
        $display("PASS tb_pool2x2");$finish;
    end
endmodule
