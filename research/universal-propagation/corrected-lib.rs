// =============================================================================
// HIGH-PERFORMANCE RUST GRAPH ACCELERATOR CORE
// File: src/lib.rs
// =============================================================================

use wasm_bindgen::prelude::*;
use rand::prelude::*;

#[wasm_bindgen]
pub struct RustGraphAccelerator {
    num_nodes: usize,
    states: Vec<f64>,
    weights: Vec<f64>, // Flattened adjacency matrix [i * num_nodes + j]
    thresholds: Vec<f64>,
    decay_factors: Vec<f64>,
}

#[wasm_bindgen]
impl RustGraphAccelerator {
    #[wasm_bindgen(constructor)]
    pub fn new(num_nodes: usize, default_decay: f64, default_threshold: f64) -> Self {
        Self {
            num_nodes,
            states: vec![0.0; num_nodes],
            weights: vec![0.0; num_nodes * num_nodes],
            thresholds: vec![default_threshold; num_nodes],
            decay_factors: vec![default_decay; num_nodes],
        }
    }

    pub fn set_node_state(&mut self, idx: usize, val: f64) {
        if idx < self.num_nodes {
            self.states[idx] = val;
        }
    }

    pub fn get_node_state(&self, idx: usize) -> f64 {
        if idx < self.num_nodes {
            self.states[idx]
        } else {
            0.0
        }
    }

    pub fn configure_edge(&mut self, from: usize, to: usize, weight: f64) {
        if from < self.num_nodes && to < self.num_nodes {
            let index = from * self.num_nodes + to;
            self.weights[index] = weight;
        }
    }

    /// Evaluates a single discrete time-step over the graph boundary via Euler integration
    pub fn tick(&mut self, dt: f64) {
        let mut next_states = self.states.clone();

        for i in 0..self.num_nodes {
            let mut coupling_sum = 0.0;
            // configure_edge uses source-row, destination-column storage.

            for j in 0..self.num_nodes {
                let weight = self.weights[j * self.num_nodes + i];
                if weight != 0.0 {
                    let activation_input = self.states[j] - self.thresholds[i];
                    
                    // Bounded continuous logistic sigmoid; stable exponent branches.
                    let sigma = if activation_input >= 0.0 {
                        1.0 / (1.0 + (-activation_input).exp())
                    } else {
                        let e = activation_input.exp();
                        e / (1.0 + e)
                    };
                    coupling_sum += weight * sigma;
                }
            }

            // dx_i/dt = -\gamma_i * x_i + Coupling
            let change = -self.decay_factors[i] * self.states[i] + coupling_sum;
            next_states[i] += change * dt;
        }
        self.states = next_states;
    }
}

// =============================================================================
// RESILIENT NEURAL MESH ACCELERATOR
// =============================================================================

#[wasm_bindgen]
pub struct ResilientNeuralMesh {
    num_neurons: usize,
    potentials: Vec<f64>,
    weights: Vec<f64>,
    v_thresh: f64,
    v_rest: f64,
    tau_m: f64,
    failure_rate: f64,
}

#[wasm_bindgen]
impl ResilientNeuralMesh {
    #[wasm_bindgen(constructor)]
    pub fn new(num_neurons: usize, failure_rate: f64) -> Self {
        let mut weights = vec![0.0; num_neurons * num_neurons];

        // Construct redundant mesh structure: each neuron connects to next 3 neighbors
        for i in 0..num_neurons {
            for offset in 1..=3 {
                if i + offset < num_neurons {
                    let index = i * num_neurons + (i + offset);
                    weights[index] = 12.0 / (offset as f64);
                }
            }
        }

        Self {
            num_neurons,
            potentials: vec![-70.0; num_neurons],
            weights,
            v_thresh: -55.0,
            v_rest: -70.0,
            tau_m: 10.0,
            failure_rate,
        }
    }

    pub fn stimulate_node(&mut self, idx: usize, voltage: f64) {
        if idx < self.num_neurons {
            self.potentials[idx] = voltage;
        }
    }

    pub fn get_potential(&self, idx: usize) -> f64 {
        if idx < self.num_neurons {
            self.potentials[idx]
        } else {
            -70.0
        }
    }

    /// Evaluates a single system step while introducing stochastic synaptic dropouts
    pub fn tick(&mut self, dt: f64) -> usize {
        let mut rng = thread_rng();
        let mut spikes_fired = 0;
        let mut incoming_currents = vec![0.0; self.num_neurons];

        for i in 0..self.num_neurons {
            if self.potentials[i] >= self.v_thresh {
                spikes_fired += 1;
                self.potentials[i] = -75.0; // Post-spike reset potential

                let row_offset = i * self.num_neurons;
                for j in 0..self.num_neurons {
                    let weight = self.weights[row_offset + j];
                    if weight > 0.0 && rng.gen::<f64>() >= self.failure_rate {
                        incoming_currents[j] += weight;
                    }
                }
            }
        }

        for i in 0..self.num_neurons {
            if self.potentials[i] > -75.0 {
                let leak = -(self.potentials[i] - self.v_rest) / self.tau_m;
                self.potentials[i] += (leak + incoming_currents[i]) * dt;
            } else {
                // Recovery from refractory period
                self.potentials[i] += 5.0 * dt;
            }
        }

        spikes_fired
    }
}

