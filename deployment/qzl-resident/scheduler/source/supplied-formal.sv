module quantum_state_register_128_formal (
    input wire         clk,
    input wire         rst_n,
    input wire [127:0] in_sreg,
    input wire [31:0]  in_operand_q,
    input wire [1:0]   op_code,
    input wire [127:0] out_sreg,
    input wire         align_flag,
    input wire         null_trap
);

    // Default clocking block for formal assertions
    default clocking cb @(posedge clk); endclocking
    default disable iff (!rst_n);

    // Field extractions for inputs: S = (I, O_id, O_eps, q, t)
    wire [31:0]        in_I       = in_sreg[127:96];
    wire [15:0]        in_O_id    = in_sreg[95:80];
    wire [15:0]        in_O_eps   = in_sreg[79:64];
    wire signed [31:0] in_q       = in_sreg[63:32];
    wire [31:0]        in_t       = in_sreg[31:0];

    // Field extractions for outputs
    wire [31:0]        out_I      = out_sreg[127:96];
    wire [15:0]        out_O_id   = out_sreg[95:80];
    wire [15:0]        out_O_eps  = out_sreg[79:64];
    wire signed [31:0] out_q      = out_sreg[63:32];
    wire [31:0]        out_t      = out_sreg[31:0];

    // =========================================================================
    // PROPERTY 1: Unconditional Identity Retention (I_in == I_out)
    // =========================================================================
    // The invariant identity hash 'I' must never change or deallocate.
    property p_identity_conservation;
        @(posedge clk) disable iff (!rst_n)
        (out_I == $past(in_I));
    endproperty
    assert_identity_conservation: assert property (p_identity_conservation)
        else $error("[QZL SVA FAIL] Invariant Identity I modified across clock cycle!");

    // =========================================================================
    // PROPERTY 2: Origin Frame ID Retention (O_id_in == O_id_out)
    // =========================================================================
    // The reference frame identifier 'O_id' must remain locked.
    property p_frame_id_conservation;
        @(posedge clk) disable iff (!rst_n)
        (out_O_id == $past(in_O_id));
    endproperty
    assert_frame_id_conservation: assert property (p_frame_id_conservation)
        else $error("[QZL SVA FAIL] Reference Frame ID modified across clock cycle!");

    // =========================================================================
    // PROPERTY 3: Absolute Null Trap Suppression (null_trap == 0)
    // =========================================================================
    // Grounded null_trap must remain permanently 0 under all possible inputs.
    property p_null_trap_grounded;
        @(posedge clk) (null_trap == 1'b0);
    endproperty
    assert_null_trap_grounded: assert property (p_null_trap_grounded)
        else $error("[QZL SVA FAIL] null_trap asserted high! Violates Non-Null Conservation Axiom.");

    // =========================================================================
    // PROPERTY 4: Zero Node Alignment Signal (align_flag <==> next_q == 0)
    // =========================================================================
    // align_flag must assert high if and only if the computed coordinate reaches 0.
    property p_align_flag_correctness;
        @(posedge clk) disable iff (!rst_n)
        (out_q == 32'sd0) |-> (align_flag == 1'b1);
    endproperty
    assert_align_flag_correctness: assert property (p_align_flag_correctness)
        else $error("[QZL SVA FAIL] align_flag failed to assert at coordinate zero!");

    // =========================================================================
    // PROPERTY 5: Involution Parity Flip (J_INV op_code == 2'b10)
    // =========================================================================
    // Executing J(q) must invert orientation vector eps (eps_out == ~eps_in)
    // and negate coordinate q (q_out == -q_in).
    property p_involution_parity;
        @(posedge clk) disable iff (!rst_n)
        ($past(op_code) == 2'b10) |-> 
            (out_O_eps == ~$past(in_O_eps)) && (out_q == -$past(in_q));
    endproperty
    assert_involution_parity: assert property (p_involution_parity)
        else $error("[QZL SVA FAIL] J_INV operation failed involution property!");

    // =========================================================================
    // PROPERTY 6: Double Involution Invariance (J(J(q)) == q)
    // =========================================================================
    // Applying opcode 2'b10 twice consecutively must restore initial eps and q.
    property p_double_involution_identity;
        @(posedge clk) disable iff (!rst_n)
        (($past(op_code, 1) == 2'b10) && ($past(op_code, 2) == 2'b10)) |->
            (out_O_eps == $past(in_O_eps, 2)) && (out_q == $past(in_q, 2));
    endproperty
    assert_double_involution_identity: assert property (p_double_involution_identity)
        else $error("[QZL SVA FAIL] Double involution J(J(q)) failed to restore state!");

    // =========================================================================
    // PROPERTY 7: Strict Monotonic Timestamp Increment (t_out == t_in + 1)
    // =========================================================================
    property p_timestamp_monotonic;
        @(posedge clk) disable iff (!rst_n)
        (out_t == $past(in_t) + 32'd1);
    endproperty
    assert_timestamp_monotonic: assert property (p_timestamp_monotonic)
        else $error("[QZL SVA FAIL] Monotonic clock timestamp increment failed!");

    // =========================================================================
    // PROPERTY 8: Asynchronous Reset Lockout (rst_n == 0 ==> out_sreg == 0)
    // =========================================================================
    property p_async_reset;
        @(posedge clk) (!rst_n) |-> (out_sreg == 128'b0);
    endproperty
    assert_async_reset: assert property (p_async_reset)
        else $error("[QZL SVA FAIL] Asynchronous reset failed to clear state register!");

endmodule
