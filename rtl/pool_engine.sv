`timescale 1ns/1ps
module pool_engine(
    input wire clk,rst,start,
    input wire [16:0] in_base,out_base,
    input wire [15:0] height,width,channels,
    output reg busy,done,
    output wire req_valid,req_write,
    input wire req_ready,
    output wire [16:0] req_addr,
    output wire [7:0] req_data,
    input wire rsp_valid,
    output wire rsp_ready,
    input wire [7:0] rsp_data
);
    localparam IDLE=0,READ_REQ=1,READ_WAIT=2,WRITE_REQ=3,WRITE_WAIT=4;
    reg [2:0] state;
    integer ch,y,x,sample_index;
    reg signed [7:0] samples [0:3];
    wire signed [7:0] maximum;
    pool2x2 compare(.a(samples[0]),.b(samples[1]),.c(samples[2]),.d(samples[3]),.maximum(maximum));
    assign req_valid=(state==READ_REQ)||(state==WRITE_REQ);
    assign req_write=(state==WRITE_REQ);
    assign req_addr=(state==WRITE_REQ)?(out_base+ch*(height/2)*(width/2)+y*(width/2)+x):
                    (in_base+ch*height*width+(2*y+sample_index/2)*width+2*x+sample_index%2);
    assign req_data=maximum;
    assign rsp_ready=(state==READ_WAIT)||(state==WRITE_WAIT);
    always @(posedge clk) begin
        if (rst) begin state<=IDLE; busy<=0; done<=0; ch<=0; y<=0; x<=0; sample_index<=0; end
        else begin
            done<=0;
            case(state)
                IDLE: if (start) begin ch<=0; y<=0; x<=0; sample_index<=0; busy<=1; state<=READ_REQ; end
                READ_REQ: if (req_ready) state<=READ_WAIT;
                READ_WAIT: if (rsp_valid) begin
                    samples[sample_index]<=rsp_data;
                    if (sample_index==3) state<=WRITE_REQ;
                    else begin sample_index<=sample_index+1; state<=READ_REQ; end
                end
                WRITE_REQ: if (req_ready) state<=WRITE_WAIT;
                WRITE_WAIT: if (rsp_valid) begin
                    sample_index<=0;
                    if (x+1<width/2) begin x<=x+1; state<=READ_REQ; end
                    else if (y+1<height/2) begin x<=0; y<=y+1; state<=READ_REQ; end
                    else if (ch+1<channels) begin x<=0; y<=0; ch<=ch+1; state<=READ_REQ; end
                    else begin busy<=0; done<=1; state<=IDLE; end
                end
                default: state<=IDLE;
            endcase
        end
    end
endmodule
