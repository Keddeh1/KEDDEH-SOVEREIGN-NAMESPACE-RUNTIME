module formal(output reg witness_intmin, output reg witness_double, output reg witness_zero);
  (* gclk *) reg clk;
  (* anyseq *) reg rst_n;
  (* anyseq *) reg [127:0] in_sreg;
  (* anyseq *) reg [31:0] operand;
  (* anyseq *) reg [1:0] opcode;
  wire [127:0] out_sreg;
  wire align_flag, null_trap;
  quantum_state_register_128 dut(clk,rst_n,in_sreg,operand,opcode,out_sreg,align_flag,null_trap);
  reg past_valid = 0;
  reg past2_valid = 0;
  reg [31:0] expected_q;
  always @* begin
    case(opcode)
      0: expected_q = in_sreg[63:32] + operand;
      1: expected_q = in_sreg[63:32] - operand;
      2: expected_q = -in_sreg[63:32];
      3: expected_q = in_sreg[63:32] + operand + 32'd1;
    endcase
  end
  always @(posedge clk) begin
    past_valid <= 1;
    past2_valid <= past_valid;
    // Establish reset at the initial sampled cycle; future reset/input values are arbitrary.
    if (!past_valid) assume(!rst_n);
    if (past_valid) begin
      assert(null_trap == 0);
      assert(align_flag == (out_sreg[63:32] == 0));
      if (!rst_n) assert(out_sreg == 0);
      if (rst_n && $past(rst_n)) begin
        assert(out_sreg[127:96] == $past(in_sreg[127:96]));
        assert(out_sreg[95:80] == $past(in_sreg[95:80]));
        assert(out_sreg[63:32] == $past(expected_q));
        assert(out_sreg[31:0] == $past(in_sreg[31:0]) + 32'd1);
        if ($past(opcode) == 2) begin
          assert(out_sreg[79:64] == ~$past(in_sreg[79:64]));
          if ($past(in_sreg[63:32]) == 32'h80000000)
            assert(out_sreg[63:32] == 32'h80000000);
        end else assert(out_sreg[79:64] == $past(in_sreg[79:64]));
        // Composition requires the second input to contain the first result.
        if (past2_valid && $past(rst_n,2) && $past(opcode) == 2 && $past(opcode,2) == 2
          && $past(in_sreg[79:32]) == $past(out_sreg[79:32])) begin
          assert(out_sreg[79:32] == $past(in_sreg[79:32],2));
        end
      end
    end
  end
always @(posedge clk) begin
 witness_intmin <= past_valid && rst_n && $past(rst_n) && $past(opcode)==2 && $past(in_sreg[63:32])==32'h80000000;
witness_double <= past2_valid && rst_n && $past(rst_n) && $past(rst_n,2) && $past(opcode)==2 && $past(opcode,2)==2 && $past(in_sreg[79:32])==$past(out_sreg[79:32]);
witness_zero <= past_valid && rst_n && $past(rst_n) && out_sreg[63:32]==0;
end
endmodule
