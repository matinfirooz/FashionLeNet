`timescale 1ns/1ps
module tb_read_cache;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,flush=0,enable=1,qv=0,qw=0,rr=0;
    reg[16:0] qa=0;reg[7:0] qd=0;
    wire qr,rv,lv,lw,lr,lrv,lrr;wire[16:0] la;wire[7:0] rd,ld,lrd;
    wire[31:0] hits,misses,bypasses;integer i;
    read_cache dut(.clk(clk),.rst(rst),.flush(flush),.enable(enable),
        .req_valid(qv),.req_write(qw),.req_ready(qr),.req_addr(qa),.req_data(qd),.rsp_valid(rv),.rsp_ready(rr),.rsp_data(rd),
        .l2_valid(lv),.l2_write(lw),.l2_ready(lr),.l2_addr(la),.l2_data(ld),.l2_rsp_valid(lrv),.l2_rsp_ready(lrr),.l2_rsp_data(lrd),
        .hits(hits),.misses(misses),.bypasses(bypasses));
    backing_store l2(.clk(clk),.rst(rst),.host_we(1'b0),.host_addr(17'd0),.host_data(8'd0),
        .req_valid(lv),.req_write(lw),.req_ready(lr),.req_addr(la),.req_data(ld),.rsp_valid(lrv),.rsp_ready(lrr),.rsp_data(lrd));
    task transact(input integer wr,addr,value,expected);
        reg[7:0] held;
        begin
            @(negedge clk);qv=1;qw=wr;qa=addr;qd=value;
            while(!qr)@(negedge clk);
            @(negedge clk);qv=0;
            while(!rv)@(negedge clk);
            if(!wr&&rd!==expected[7:0])$fatal(1,"cache addr %h got %h expected %h",addr,rd,expected);
            held=rd;repeat(2)begin @(negedge clk);if(!rv||rd!==held)$fatal(1,"cache response changed");end
            rr=1;@(negedge clk);rr=0;
        end
    endtask
    initial begin
        for(i=0;i<81920;i=i+1)l2.memory[i]=i%256;
        repeat(2)@(negedge clk);rst=0;
        transact(0,'h80,0,'h80);transact(0,'h81,0,'h81);
        transact(0,'h480,0,'h80);transact(0,'h80,0,'h80);
        transact(1,'h80,7,0);transact(0,'h80,0,7);
        enable=0;transact(0,'h81,0,'h81);
        if(hits!=1||misses!=4||bypasses!=1)$fatal(1,"cache counters h%0d m%0d b%0d",hits,misses,bypasses);
        flush=1;@(negedge clk);flush=0;
        if(hits||misses||bypasses||dut.valid_bits)$fatal(1,"flush");
        $display("PASS tb_read_cache: hit, miss, conflict, full refill, write invalidation, bypass, stalls");$finish;
    end
    initial begin #200000;$fatal(1,"timeout");end
endmodule
