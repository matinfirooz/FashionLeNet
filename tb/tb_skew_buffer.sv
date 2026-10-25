`timescale 1ns/1ps
module tb_skew_buffer;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,clear=0,advance=0;
    reg [39:0] din=0;reg[4:0] vin=0;
    wire[39:0] dout;wire[4:0] vout;
    integer history[0:4][0:4];reg valhistory[0:4][0:4];
    integer i,j,t,expected;
    skew_buffer dut(.clk(clk),.rst(rst),.clear(clear),.advance(advance),.data_in(din),.valid_in(vin),.data_out(dout),.valid_out(vout));
    initial begin
        for(i=0;i<5;i=i+1)for(j=0;j<5;j=j+1)begin history[i][j]=0;valhistory[i][j]=0;end
        repeat(2)@(negedge clk);rst=0;
        for(t=0;t<80;t=t+1)begin
            advance=(t%4!=0);
            for(i=0;i<5;i=i+1)begin din[8*i+:8]=(t*7+i)%256;vin[i]=(t%3!=0);end
            #1;
            for(i=0;i<5;i=i+1)begin
                expected=(i==0)?din[0+:8]:history[i][i-1];
                if(dout[8*i+:8]!==expected[7:0])$fatal(1,"skew lane %d",i);
                if(vout[i]!==((i==0)?vin[0]:valhistory[i][i-1]))$fatal(1,"skew valid");
            end
            @(posedge clk);#1;
            if(advance)for(i=1;i<5;i=i+1)begin
                for(j=4;j>0;j=j-1)begin history[i][j]=history[i][j-1];valhistory[i][j]=valhistory[i][j-1];end
                history[i][0]=din[8*i+:8];valhistory[i][0]=vin[i];
            end
            @(negedge clk);
        end
        clear=1;@(negedge clk);clear=0;#1;if(vout[4:1]!==0)$fatal(1,"skew clear");
        $display("PASS tb_skew_buffer: token delays survive stalls");$finish;
    end
endmodule
