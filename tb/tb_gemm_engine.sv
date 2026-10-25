`timescale 1ns/1ps
module tb_gemm_engine;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,start=0,sparse=0;wire busy,done,qv,qw,qr,rv,rr;
    wire[16:0] qa;wire[7:0] qd,rd;wire[31:0] cycles,attempts,execs;
    integer i,oc,y,x,ic,ky,kx,acc,expected,mag,mode,base_cycles,expected_exec;
    gemm_engine #(.ROWS(3),.COLS(4)) dut(.clk(clk),.rst(rst),.start(start),.sparse_en(sparse),
        .in_base(17'd0),.out_base(17'd256),.weight_base(17'd128),.bias_base(17'd200),
        .in_h(16'd4),.in_w(16'd5),.out_h(16'd3),.out_w(16'd4),.in_channels(16'd2),.out_channels(16'd7),.kernel(16'd2),
        .shift(6'd3),.relu(1'b0),.busy(busy),.done(done),.cycles(cycles),.mac_attempted(attempts),.mac_executed(execs),
        .req_valid(qv),.req_write(qw),.req_ready(qr),.req_addr(qa),.req_data(qd),.rsp_valid(rv),.rsp_ready(rr),.rsp_data(rd));
    backing_store #(.DEPTH(1024),.LATENCY(2)) l2(.clk(clk),.rst(rst),.host_we(1'b0),.host_addr(17'd0),.host_data(8'd0),
        .req_valid(qv),.req_write(qw),.req_ready(qr),.req_addr(qa),.req_data(qd),.rsp_valid(rv),.rsp_ready(rr),.rsp_data(rd));
    initial begin
        for(i=0;i<1024;i=i+1)l2.memory[i]=0;
        for(i=0;i<40;i=i+1)l2.memory[i]=i%4==0?0:(i*7)%15-7;
        for(i=0;i<56;i=i+1)l2.memory[128+i]=i%3==0?0:(i*11)%17-8;
        for(oc=0;oc<7;oc=oc+1)begin
            acc=oc*9-25;
            for(i=0;i<4;i=i+1)l2.memory[200+oc*4+i]=(acc>>(8*i))&255;
        end
        repeat(2)@(negedge clk);rst=0;
        for(mode=0;mode<2;mode=mode+1)begin
            sparse=mode;start=1;@(negedge clk);start=0;wait(done);@(negedge clk);
            expected_exec=0;
            for(oc=0;oc<7;oc=oc+1)for(y=0;y<3;y=y+1)for(x=0;x<4;x=x+1)begin
                acc=oc*9-25;
                for(ic=0;ic<2;ic=ic+1)for(ky=0;ky<2;ky=ky+1)for(kx=0;kx<2;kx=kx+1)begin
                    acc=acc+$signed(l2.memory[ic*20+(y+ky)*5+x+kx])*$signed(l2.memory[128+oc*8+ic*4+ky*2+kx]);
                    if(!mode||(l2.memory[ic*20+(y+ky)*5+x+kx]!=0&&l2.memory[128+oc*8+ic*4+ky*2+kx]!=0))expected_exec=expected_exec+1;
                end
                mag=(acc<0?-acc:acc)+4;expected=acc<0?-(mag>>3):(mag>>3);
                if(expected>127)expected=127;if(expected< -128)expected=-128;
                if($signed(l2.memory[256+oc*12+y*4+x])!==expected)$fatal(1,"GEMM output mismatch");
            end
            if(attempts!=672||execs!=expected_exec)$fatal(1,"GEMM counter mismatch %0d %0d",attempts,execs);
            if(mode==0)base_cycles=cycles;else if(cycles!=base_cycles)$fatal(1,"gating changed schedule");
        end
        $display("PASS tb_gemm_engine: multi-channel implicit im2col, rectangular/tail tiles, biases, sparse equality");$finish;
    end
    initial begin #2000000;$fatal(1,"timeout");end
endmodule
