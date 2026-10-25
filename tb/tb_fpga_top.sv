`timescale 1ns/1ps
`include "model_config.svh"
module tb_fpga_top;
    parameter integer ROWS=5,COLS=5,L2_LATENCY=4;
    localparam H1=`INPUT_SIZE-4,P1=H1/2,H2=P1-4,P2=H2/2;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,start=0,sparse=0,cache=0,hw=0;
    reg[16:0] ha=0;reg[7:0] hd=0;
    wire hr,busy,done;wire[3:0] prediction,stage;
    wire[31:0] cycles,attempts,execs,hits,misses,bypasses;
    reg[7:0] image[0:81919],logits[0:9];
    reg[7:0] e1[0:`C1*H1*H1-1],ep1[0:`C1*P1*P1-1],e2[0:`C2*H2*H2-1],ep2[0:`C2*P2*P2-1];
    reg[7:0] e3[0:`C3-1],e4[0:`F1-1],e5[0:9];
    reg signed[31:0] a1[0:`C1*H1*H1-1],a2[0:`C2*H2*H2-1],a3[0:`C3-1],a4[0:`F1-1],a5[0:9];
    integer i,sparse_arg,cache_arg,fd,prior_stage=0,stage_checks=0,acc_checks=0,offset;
    reg signed[31:0] expected_acc;
    string bundle,report;
    fpga_top #(.INPUT_SIZE(`INPUT_SIZE),.C1(`C1),.C2(`C2),.C3(`C3),.F1(`F1),
        .ROWS(ROWS),.COLS(COLS),.L2_LATENCY(L2_LATENCY)) dut(
        .clk(clk),.rst(rst),.start(start),.sparse_en(sparse),.cache_en(cache),
        .host_we(hw),.host_addr(ha),.host_data(hd),.host_ready(hr),.busy(busy),.done(done),.prediction(prediction),
        .cycles(cycles),.mac_attempted(attempts),.mac_executed(execs),.cache_hits(hits),.cache_misses(misses),
        .cache_bypasses(bypasses),.debug_stage(stage));
    always @(posedge clk) begin
        if(!rst && busy && dut.core.gemm.req_valid && dut.core.gemm.req_write && dut.core.gemm.req_ready)begin
            offset=dut.core.gemm.req_addr-((stage==6)?65536:73728);
            case(stage)
                1:expected_acc=a1[offset];3:expected_acc=a2[offset];5:expected_acc=a3[offset];
                6:expected_acc=a4[offset];7:expected_acc=a5[offset];
                default:$fatal(1,"unexpected write stage %d",stage);
            endcase
            if(dut.core.gemm.biased_sum!==expected_acc)
                $fatal(1,"INT32 mismatch stage%0d offset%0d: %0d != %0d",stage,offset,dut.core.gemm.biased_sum,expected_acc);
            acc_checks=acc_checks+1;
        end
    end
    task check_stage(input integer st);
        integer j,base,count;reg[7:0] expected;
        begin
            base=(st==2||st==4||st==6)?65536:73728;
            case(st)
                1:count=`C1*H1*H1;2:count=`C1*P1*P1;3:count=`C2*H2*H2;4:count=`C2*P2*P2;
                5:count=`C3;6:count=`F1;7:count=10;
                default:count=0;
            endcase
            for(j=0;j<count;j=j+1)begin
                case(st)
                    1:expected=e1[j];2:expected=ep1[j];3:expected=e2[j];4:expected=ep2[j];
                    5:expected=e3[j];6:expected=e4[j];7:expected=e5[j];default:expected=0;
                endcase
                if(dut.l2.memory[base+j]!==expected)
                    $fatal(1,"INT8 stage%0d offset%0d: %0d != %0d",st,j,$signed(dut.l2.memory[base+j]),$signed(expected));
            end
            stage_checks=stage_checks+1;
            $display("stage %0d: %0d INT8 outputs match",st,count);
        end
    endtask
    always @(negedge clk) begin
        if(!rst)begin
            if(prior_stage!=0 && prior_stage!=stage)check_stage(prior_stage);
            prior_stage=stage;
        end
    end
    initial begin
        if(!$value$plusargs("BUNDLE=%s",bundle))bundle="examples/demo";
        if(!$value$plusargs("REPORT=%s",report))report="build/full_result.json";
        if(!$value$plusargs("SPARSE=%d",sparse_arg))sparse_arg=1;
        if(!$value$plusargs("CACHE=%d",cache_arg))cache_arg=1;
        sparse=sparse_arg;cache=cache_arg;
        $readmemh({bundle,"/memory.hex"},image);
        $readmemh({bundle,"/expected_logits.hex"},logits);
        $readmemh({bundle,"/expected_conv1.hex"},e1);$readmemh({bundle,"/expected_pool1.hex"},ep1);
        $readmemh({bundle,"/expected_conv2.hex"},e2);$readmemh({bundle,"/expected_pool2.hex"},ep2);
        $readmemh({bundle,"/expected_conv3.hex"},e3);$readmemh({bundle,"/expected_fc1.hex"},e4);$readmemh({bundle,"/expected_fc2.hex"},e5);
        $readmemh({bundle,"/expected_conv1_acc.hex"},a1);$readmemh({bundle,"/expected_conv2_acc.hex"},a2);
        $readmemh({bundle,"/expected_conv3_acc.hex"},a3);$readmemh({bundle,"/expected_fc1_acc.hex"},a4);$readmemh({bundle,"/expected_fc2_acc.hex"},a5);
        repeat(3)@(negedge clk);rst=0;
        for(i=0;i<81920;i=i+1)begin
            if(!hr)$fatal(1,"host not ready while idle");hw=1;ha=i;hd=image[i];@(negedge clk);
        end
        hw=0;start=1;@(negedge clk);start=0;
        wait(done);@(negedge clk);#1;
        if(prediction!==`EXPECTED_CLASS)$fatal(1,"prediction mismatch %d",prediction);
        if(attempts!==`EXPECTED_MACS)$fatal(1,"dense MAC count mismatch %d",attempts);
        if(!sparse && execs!==attempts)$fatal(1,"dense executed count");
        if(stage_checks!=7)$fatal(1,"incomplete stage checks %d",stage_checks);
        for(i=0;i<10;i=i+1)if(dut.l2.memory[73728+i]!==logits[i])$fatal(1,"logit mismatch");
        fd=$fopen(report,"w");if(!fd)$fatal(1,"cannot create report");
        $fwrite(fd,"{\"status\":\"PASS\",\"bundle\":\"%s\",\"rows\":%0d,\"cols\":%0d,\"sparse\":%0d,\"cache\":%0d,\"l2_latency\":%0d,\"cycles\":%0d,\"mac_attempted\":%0d,\"mac_executed\":%0d,\"cache_hits\":%0d,\"cache_misses\":%0d,\"cache_bypasses\":%0d,\"prediction\":%0d,\"stage_checks\":%0d,\"int32_checks\":%0d}\n",
            bundle,ROWS,COLS,sparse,cache,L2_LATENCY,cycles,attempts,execs,hits,misses,bypasses,prediction,stage_checks,acc_checks);
        $fclose(fd);
        $display("PASS tb_fpga_top: cycles=%0d, executed=%0d/%0d, class=%0d, INT32 checks=%0d",cycles,execs,attempts,prediction,acc_checks);$finish;
    end
    initial begin #400000000;$fatal(1,"full inference timeout");end
endmodule
