`timescale 1ns/1ps
module tb_os_array;
    localparam R=3,C=4,K=9;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,clear=0,step=0,sparse=0;
    reg[R*8-1:0] a=0;reg[C*8-1:0] b=0;
    reg[R-1:0] av=0;reg[C-1:0] bv=0;
    wire[R*8-1:0] sa;wire[C*8-1:0] sb;
    wire[R-1:0] sav;wire[C-1:0] sbv;
    wire[R*C*32-1:0] sums;wire[31:0] ac,ec;
    integer aa[0:R-1][0:K-1],bb[0:K-1][0:C-1];
    integer i,j,k,t,expected,mode,counta,counte,expected_e;
    skew_buffer #(.LANES(R)) as(.clk(clk),.rst(rst),.clear(clear),.advance(step),.data_in(a),.valid_in(av),.data_out(sa),.valid_out(sav));
    skew_buffer #(.LANES(C)) bs(.clk(clk),.rst(rst),.clear(clear),.advance(step),.data_in(b),.valid_in(bv),.data_out(sb),.valid_out(sbv));
    os_array #(.ROWS(R),.COLS(C)) dut(.clk(clk),.rst(rst),.clear(clear),.step(step),.sparse_en(sparse),
        .a_west(sa),.b_north(sb),.a_valid(sav),.b_valid(sbv),.sums(sums),.attempted_count(ac),.executed_count(ec));
    initial begin
        for(i=0;i<R;i=i+1)for(k=0;k<K;k=k+1)aa[i][k]=(i+k)%3==0?0:(i*11+k*7)%23-11;
        for(k=0;k<K;k=k+1)for(j=0;j<C;j=j+1)bb[k][j]=(j+k)%4==0?0:(j*17+k*3)%19-9;
        repeat(2)@(negedge clk);rst=0;
        for(mode=0;mode<2;mode=mode+1)begin
            clear=1;step=0;@(negedge clk);clear=0;sparse=mode;counta=0;counte=0;
            for(t=0;t<K+R+C-2;t=t+1)begin
                a=0;b=0;av=0;bv=0;
                if(t<K)begin
                    // Mask final row and final column to test partial tiles.
                    for(i=0;i<R-1;i=i+1)begin a[8*i+:8]=aa[i][t];av[i]=1;end
                    for(j=0;j<C-1;j=j+1)begin b[8*j+:8]=bb[t][j];bv[j]=1;end
                end
                step=0;@(negedge clk);step=1;#1;counta=counta+ac;counte=counte+ec;
                @(negedge clk);
            end
            step=0;
            for(i=0;i<R;i=i+1)for(j=0;j<C;j=j+1)begin
                expected=0;
                if(i<R-1&&j<C-1)for(k=0;k<K;k=k+1)expected=expected+aa[i][k]*bb[k][j];
                if($signed(sums[32*(i*C+j)+:32])!==expected)$fatal(1,"array [%d,%d] mismatch",i,j);
            end
            expected_e=0;
            for(i=0;i<R-1;i=i+1)for(j=0;j<C-1;j=j+1)for(k=0;k<K;k=k+1)
                if(!mode||(aa[i][k]!=0&&bb[k][j]!=0))expected_e=expected_e+1;
            if(counta!=(R-1)*(C-1)*K||counte!=expected_e)$fatal(1,"array counters");
        end
        $display("PASS tb_os_array: exact GEMM, signed, masked tails, stall/flush, dense/sparse");$finish;
    end
endmodule
