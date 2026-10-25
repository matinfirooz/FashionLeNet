`timescale 1ns/1ps
module tb_requantize;
    reg signed[31:0] value;reg[5:0] shift;reg relu;
    wire signed[7:0] result;
    reg signed[63:0] reference_value,mag;
    integer i,s,r;
    requantize dut(.value(value),.shift(shift),.relu(relu),.result(result));
    task check;
    begin
        reference_value=value;mag=reference_value<0?-reference_value:reference_value;
        if(shift!=0)mag=(mag+(64'd1<<(shift-1)))>>shift;
        reference_value=value<0?-mag:mag;
        if(relu&&reference_value<0)reference_value=0;
        if(reference_value>127)reference_value=127;
        if(reference_value< -128)reference_value=-128;
        #1;if($signed(result)!==reference_value)$fatal(1,"requant %d shift%0d relu%0d",value,shift,relu);
    end endtask
    initial begin
        for(r=0;r<2;r=r+1)for(s=0;s<=31;s=s+1)begin
            relu=r;shift=s;
            for(i=-400;i<=400;i=i+1)begin value=i;check();end
            value=32'sh80000000;check();value=32'sh7fffffff;check();
        end
        $display("PASS tb_requantize: 51392 exhaustive small/edge cases, all shifts");$finish;
    end
endmodule
