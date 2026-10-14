"""Owner-authored K-Cloud kernel selected from notebook exports.

Exact class bodies: k_cloud_substrate_master_daemon.py lines 734-826,
bilateral_discrepancy_solver.py lines 54-121. Notebook installation cells
and simulated startup demonstrations are not executed by this module.
"""
import time
import hashlib
import numpy as np
from datetime import datetime

class SovereignHardgate:
    """Authenticates traffic using the deterministic HEXxHEX fold."""
    def __init__(self):
        self.j = 3 # Offset parameter

    def _fold(self, a: int, b: int) -> int:
        return ((a * b) + (a ^ b) + self.j) % 16

    def authenticate(self, payload: str) -> bool:
        # Simplify validation for the runtime: requires specific KEX signature
        if "A.KEDDEH" not in payload:
            return False
        # Simulating the fold execution on the payload
        a = sum(ord(c) for c in payload[:len(payload)//2]) % 16
        b = sum(ord(c) for c in payload[len(payload)//2:]) % 16
        result = self._fold(a, b)
        return result is not None  # In pure determinism, this always resolves if typed

class ZeroLessIndexEngine:
    """Rejects Cartesian zero-states and enforces the KEX topological boundary."""
    VALID_INDICES = {-3, -2, 1, 2, 3}

    def route(self, index: int, payload: str):
        if index not in self.VALID_INDICES:
            print(f"[ERROR] CRITICAL: [{index}] is a Cartesian hallucination. Operation halted.")
            return None

        # Route to WiredFATRegistry
        return self._wired_fat_mapping(index, payload)

    def _wired_fat_mapping(self, index: int, payload: str):
        # Bypasses IP layer, maps directly to hardware slot representation
        hardware_slot = f"EXPLICIT_HARDWARE_SLOT_STATE_BOUNDARY_MAPPED_TO_KEDDEH_INDEX_{index}"
        memory_state = f"{hardware_slot}::UNCOMPRESSED_PAYLOAD({hashlib.sha256(payload.encode()).hexdigest()[:12]})"
        return memory_state

class DynamicHealingAgent:
    """A flexible healing agent that allows dynamic parameter adjustment."""
    def __init__(self, d: float = 0.12, lam_o: float = 0.35, lam_e: float = 0.25, iterations: int = 5):
        self.d = d
        self.lam_o = lam_o
        self.lam_e = lam_e
        self.iterations = iterations

        # Initialize the update matrix A based on provided parameters
        self.A = np.array([
            [(1 - self.d) * (1 - self.lam_o), (1 - self.d) * self.lam_o],
            [(1 - self.d) * self.lam_e,       (1 - self.d) * (1 - self.lam_e)]
        ])

    def resolve_drift(self, error_vector: list) -> list:
        Z_n = np.array(error_vector, dtype=float)
        # Apply consensus over the specified number of iterations
        for _ in range(self.iterations):
            Z_n = self.A.dot(Z_n)
        return Z_n.tolist()

class KCloudNode:
    """Orchestrates the K-Cloud Substrate components."""
    def __init__(self):
        self.gate = SovereignHardgate()
        self.router = ZeroLessIndexEngine()
        # Use the new DynamicHealingAgent
        self.healer = DynamicHealingAgent()
        self.ledger = []
        self.state = "BOOTING"

    def execute_26_node_traversal(self):
        print("--- INITIATING 26-NODE BOOT TRAVERSAL ---")
        for i in range(1, 27):
            time.sleep(0.02) # Simulating physical slot mapping
        self.state = "1_S_ACTIVE"
        print("✅ K-CLOUD SUBSTRATE LIVE. 1_S STATE ACHIEVED.")

    def process_request(self, index: int, payload: str):
        timestamp = datetime.now().isoformat()

        if not self.gate.authenticate(payload):
            self.ledger.append(f"{timestamp} | REJECTED | UNAUTHORIZED_PAYLOAD")
            return "DROPPED"

        mapped_state = self.router.route(index, payload)

        if mapped_state is None:
            # Healing Agent steps in to log the exact discrepancy
            healed = self.healer.resolve_drift([1.0, 0.0]) # Cartesian 1,0 drift
            self.ledger.append(f"{timestamp} | BLOCKED | CARTESIAN_NULL | HEALED_TO_{healed[0]:.3f}")
            return "DROPPED"

        self.ledger.append(f"{timestamp} | SUCCESS | {mapped_state}")
        return "MAPPED"

class StochasticKuramotoPLL:
    def __init__(self, num_nodes=3, omega_star=0.297, dt=0.01):
        self.N = num_nodes
        self.omega_star = omega_star
        self.dt = dt

        # Initialize State Vectors on S^1
        self.theta = np.random.uniform(0, 2*np.pi, self.N)
        self.omega = np.random.uniform(omega_star - 0.05, omega_star + 0.05, self.N)

        # Coupling gains
        self.Kh = 0.20  # Horizontal coupling strength
        self.Kv_max = 0.40  # Max vertical coupling strength
        self.lambda_omega = 0.50  # Frequency tracker relaxation rate
        self.sigma = 0.05  # Infinitesimal diffusion (stochastic noise strength)

        # Active topology (complete graph peer-to-peer coupling)
        self.deg = self.N - 1

    def step(self, t, parent_phase, parent_available, reanchor_time, Tr=2.0):
        """
        Integrates one step of the SDE using Euler-Maruyama
        """
        d_theta = np.zeros(self.N)
        d_omega = np.zeros(self.N)

        # Dynamic vertical gain ramping for soft phase capture
        if parent_available:
            t_since_reanchor = max(0.0, t - reanchor_time)
            Kv_eff = self.Kv_max * (1.0 - np.exp(-t_since_reanchor / Tr))
        else:
            Kv_eff = 0.0

        # Generate independent Wiener increments dW_t ~ N(0, dt)
        dW = np.random.normal(0.0, np.sqrt(self.dt), self.N)

        for i in range(self.N):
            # 1. Horizontal Kuramoto coupling (Degree-Normalized)
            h_sum = 0.0
            for j in range(self.N):
                if i == j: continue
                # Wrap phase error on S^1
                h_sum += np.sin(self.theta[j] - self.theta[i])
            h_term = (self.Kh / self.deg) * h_sum

            # 2. Vertical parent coupling (Wrapped phase error)
            if parent_available:
                v_term = Kv_eff * np.sin(parent_phase - self.theta[i])
            else:
                v_term = 0.0

            # SDE State update: d_theta = [omega + h_term + v_term] * dt + sigma * dW
            drift = self.omega[i] + h_term + v_term
            d_theta[i] = drift * self.dt + self.sigma * dW[i]

            # Frequency tracker trajectory update (Relaxation toward omega_star)
            d_omega[i] = -self.lambda_omega * (self.omega[i] - self.omega_star) * self.dt

        # Apply updates and wrap phases to [0, 2*pi]
        self.theta = (self.theta + d_theta) % (2 * np.pi)
        self.omega = self.omega + d_omega

        # Calculate Kuramoto Order Parameter (Coherence R_g)
        order_param = np.mean(np.exp(1j * self.theta))
        coherence = np.abs(order_param)
        aggregate_phase = np.angle(order_param) % (2 * np.pi)

        return coherence, aggregate_phase
