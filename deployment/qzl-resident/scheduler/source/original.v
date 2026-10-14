module quantum_state_register_128 (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [127:0] in_sreg,      // [127:96]=I, [95:80]=O_id, [79:64]=O_eps, [63:32]=q, [31:0]=t
    input  wire [31:0]  in_operand_q, // Operation operand for coordinate
    input  wire [1:0]   op_code,      // 2'b00: ADD, 2'b01: SUB, 2 me: J_INV, 2'b11: SHIFT_ADD
    output reg  [127:0] out_sreg,     // Updated state register output
    output wire        align_flag,   // Asserted when q == 0 (Node Alignment)
    output wire        null_trap     // STRICTLY 0 (Suppresses CPU Null Trap)
);

    // Unpack fields from input state register
    wire [31:0] in_I = in_sreg[127:96];
    wire [15:0] in_O_id = in_sreg[95:80];
    wire [15:0] in_O_eps = in_sreg[79:64];
    wire signed [31:0] in_q = in_sreg[63:32];
    wire [31:0] in_t = in_sreg[31:0];

    // Internal calculation registers
    reg signed [31:0] next_q;
    reg [15:0] next_eps;

    always @(*) begin
        case (op_code)
            2'b00: begin // ADD: Direct coordinate addition
                next_q   = in_q + in_operand_q;
                next_eps = in_O_eps;
            end
            2'b01: begin // SUB: Direct coordinate subtraction
                next_q   = in_q - in_operand_q;
                next_eps = in_O_eps;
            end
            2'b10: begin // J_INV: Orientation Involution J(q) = -q
                next_q   = -in_q;
                next_eps = ~in_O_eps; // Invert orientation vector
            end
            2'b11: begin // SHIFT_ADD (u (+) v = u + v + 1)
                next_q   = in_q + in_operand_q + 32'sd1;
                next_eps = in_O_eps;
            end
            default: begin
                next_q   = in_q;
                next_eps = in_O_eps;
            end
        endcase
    end

    // Sequential Register Update
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_sreg <= 128'b0;
        end else begin
            // Preserve Identity (I) and Frame ID unconditionally!
            out_sreg[127:96] <= in_I;
            out_sreg[95:80]  <= in_O_id;
            out_sreg[79:64]  <= next_eps;
            out_sreg[63:32]  <= next_q;
            out_sreg[31:0]   <= in_t + 32'd1; // Monotonic timestamp increment
        end
    end

    // Non-Null Conservation Gate Logic
    assign align_flag = (next_q == 32'sd0);
    assign null_trap  = 1'b0; // Explicitly prevents NULL hardware exception

endmodule
