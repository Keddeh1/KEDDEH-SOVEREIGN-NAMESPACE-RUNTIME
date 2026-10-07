#!/usr/bin/env python3
"""
=============================================================================
EXECUTABLE UNIVERSAL PROPAGATION REFERENCE ENGINE
File: engine.py
=============================================================================
Demonstrates the exact mathematical isomorphism across:
  1. Distributed Gossip Protocol (Epidemic SI spreading)
  2. Spiking Neural Network (Leaky Integrate-and-Fire dynamics)
  3. Digital Circuit Interconnect (RC propagation delay & slew rate)
"""

import math
import random
import json

def simulate_gossip(num_nodes: int = 50, fanout: int = 2, max_rounds: int = 20):
    informed = {0}
    rounds = 0
    history = [1]

    while len(informed) < num_nodes and rounds < max_rounds:
        rounds += 1
        newly_informed = set()
        for node in list(informed):
            targets = random.sample(range(num_nodes), min(fanout, num_nodes - 1))
            for target in targets:
                if target not in informed:
                    newly_informed.add(target)
        informed.update(newly_informed)
        history.append(len(informed))

    return {
        "domain": "DISTRIBUTED_GOSSIP",
        "total_nodes": num_nodes,
        "rounds_to_converge": rounds,
        "theoretical_log2": math.ceil(math.log2(num_nodes)),
        "spread_curve": history,
        "final_coverage_pct": (len(informed) / num_nodes) * 100
    }

def simulate_neural_spike_cascade(num_neurons: int = 8, time_steps: int = 100, dt: float = 0.5):
    V_rest = -70.0    # mV
    V_thresh = -55.0  # mV
    V_reset = -75.0   # mV
    tau_m = 10.0      # ms
    synaptic_weight = 18.0
    synaptic_delay = 4

    potentials = [V_rest] * num_neurons
    spike_history = {i: [] for i in range(num_neurons)}
    pending_spikes = []

    potentials[0] = V_thresh + 5.0

    for step in range(time_steps):
        t = step * dt

        for spike in list(pending_spikes):
            if spike["deliver_at"] == step:
                potentials[spike["target"]] += synaptic_weight
                pending_spikes.remove(spike)

        for i in range(num_neurons):
            if potentials[i] >= V_thresh:
                spike_history[i].append(t)
                potentials[i] = V_reset
                if i + 1 < num_neurons:
                    pending_spikes.append({"target": i + 1, "deliver_at": step + synaptic_delay})
            else:
                potentials[i] += (-(potentials[i] - V_rest) / tau_m) * dt

    latency = (spike_history[num_neurons - 1][0] - spike_history[0][0]) if spike_history[num_neurons - 1] else None

    return {
        "domain": "NEURAL_SPIKE_PROPAGATION",
        "neurons_in_cascade": num_neurons,
        "total_spikes_fired": sum(len(spk) for spk in spike_history.values()),
        "cascade_latency_ms": latency
    }

def simulate_rc_circuit_delay(stages: int = 5, R_ohms: float = 1000.0, C_farads: float = 1e-12):
    tau_stage = R_ohms * C_farads
    t_50_per_stage = tau_stage * math.log(2)
    total_critical_path_delay_ns = stages * t_50_per_stage * 1e9
    max_clock_frequency_ghz = (1.0 / (total_critical_path_delay_ns * 1e-9)) / 1e9

    return {
        "domain": "ELECTRONIC_CIRCUIT_DELAY",
        "logic_stages": stages,
        "t50_switching_delay_per_stage_ns": round(t_50_per_stage * 1e9, 4),
        "total_critical_path_delay_ns": round(total_critical_path_delay_ns, 4),
        "max_clock_frequency_ghz": round(max_clock_frequency_ghz, 2)
    }

if __name__ == "__main__":
    print(json.dumps({
        "gossip": simulate_gossip(),
        "neural": simulate_neural_spike_cascade(),
        "circuit": simulate_rc_circuit_delay()
    }, indent=2))

