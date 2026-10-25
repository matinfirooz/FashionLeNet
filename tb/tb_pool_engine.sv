`timescale 1ns/1ps
module tb_pool_engine;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,start=0;wire busy,done,qv,qw,qr,rv,rr;wire[16:0] qa;wire[7:0] qd,rd;
    integer i,ch,y,x,dy,dx,expected;
    pool_engine dut(.clk(clk),.rst(rst),.start(start),.in_base(17'd0),.out_base(17'd128),
        .height(16'd4),.width(16'd6),.channels(16'd2),.busy(busy),.done(done),
        .req_valid(qv),.req_write(qw),.req_ready(qr),.req_addr(qa),.req_data(qd),.rsp_valid(rv),.rsp_ready(rr),.rsp_data(rd));
    backing_store #(.DEPTH(256),.LATENCY(3)) l2(.clk(clk),.rst(rst),.host_we(1'b0),.host_addr(17'd0),.host_data(8'd0),
        .req_valid(qv),.req_write(qw),.req_ready(qr),.req_addr(qa),.req_data(qd),.rsp_valid(rv),.rsp_ready(rr),.rsp_data(rd));
    initial begin
        for(i=0;i<256;i=i+1)l2.memory[i]=(i*37)%256;
        repeat(2)@(negedge clk);rst=0;start=1;@(negedge clk);start=0;wait(done);@(negedge clk);
        for(ch=0;ch<2;ch=ch+1)for(y=0;y<2;y=y+1)for(x=0;x<3;x=x+1)begin
            expected=-128;
            for(dy=0;dy<2;dy=dy+1)for(dx=0;dx<2;dx=dx+1)
                if($signed(l2.memory[ch*24+(2*y+dy)*6+2*x+dx])>expected)expected=$signed(l2.memory[ch*24+(2*y+dy)*6+2*x+dx]);
            if($signed(l2.memory[128+ch*6+y*3+x])!==expected)$fatal(1,"pool engine mismatch");
        end
        $display("PASS tb_pool_engine: channels, signed pooling, memory latency");$finish;
    end
    initial begin #100000;$fatal(1,"timeout");end
endmodule
