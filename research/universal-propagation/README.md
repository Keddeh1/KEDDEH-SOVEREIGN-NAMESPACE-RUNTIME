# Universal propagation: executable runtime and validation

Owner source is preserved byte-for-byte in owner-source.txt with source-custody.json. Extracted original files remain unchanged. Embedded deployment directions are source material, not instructions executed automatically.

## Working implementation

`src/keddeh_namespace/universal_propagation.py` implements a directed, delayed sigmoid propagation runtime and bounded GraphML/adjacency topology parsers. Matrix rows are sources, columns are destinations. Updates are synchronous; delayed samples use initial-state prehistory, retained history is bounded, signed weights are accepted and non-finite values are rejected. A local seeded RNG makes per-edge/per-tick dropout reproducible. Explicit units, threshold scaling and Euler leak-step restrictions are required. It is an executable software model, not a physical actuator or browser transport.

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m keddeh_namespace.universal_propagation --graphml graph.graphml --steps 100
.venv/bin/python -m keddeh_namespace.universal_propagation --adjacency-json matrix.json --steps 100
.venv/bin/python -m keddeh_namespace.universal_propagation --experiment
```

GraphML supports one directed graph with edge keys named weight and delay_steps, including defaults. Delays are integral steps (physical delay = steps × dt), not silently rounded arbitrary durations. Undirected/nested graphs, hyperedges, duplicate edges and entity declarations are rejected. No WebAssembly heap loader is implemented or claimed by this Python parser.

## Source defects and corrected scope

- Rust configure_edge(from,to) writes source-row storage, but original tick reads destination rows. This reverses directed propagation. corrected-lib.rs fixes that index, retains signed weights and uses a numerically stable sigmoid. It is a source-level patch, not a compiled/validated WASM artifact: rustc/cargo are unavailable here, and the supplied source has no Cargo manifest or pinned dependencies. Other Rust input guards, seeded WASM randomness and delay history still require implementation.
- Sigmoid is bounded (0,1) mathematically, not unbounded. Very negative inputs can still underflow to zero in finite precision. Negative moderate inputs couple continuously; sigmoid(0)=0.5 also means nonzero baseline drive without an injected signal. That spontaneous drive must be calibrated, not mistaken for measured propagation.
- The provided neural mesh uses 12 mV/time-unit first-neighbor drive multiplied by dt, unlike the Python model's 18 mV instantaneous jump. With a single initial spike, resting targets need 15 mV, so ordinary dt=0.5/1 settings do not fire even the first downstream target. This is not evidence of severe-noise resilience. It has neither explicit synaptic delay nor timed refractory duration.
- Original browser code does not import/init Rust WASM. It performs in-place JavaScript updates, which are order-dependent and different from synchronous Euler. One RTCPeerConnection without addressed signaling is not a multi-peer mesh; BroadcastChannel is local same-origin signaling, not distributed discovery. It lacks bounded send-buffer/backpressure handling and received-array validation. No Web Audio implementation is present.
- Gossip is a discrete monotonic SI process, neural is a threshold/reset event system, and RC code calculates an analytical step-delay approximation. The three supplied functions do not execute a shared differential equation or establish exact isomorphism. A useful common graph/state interface remains possible with separate domain transition rules and units.
- Original gossip can sample its own source node; log2(n) is a heuristic, not its convergence theorem, and rounds_to_converge counts attempted rounds even when coverage is incomplete. It provides no noise or topology comparison.
- Default neural output: 8 spikes, 14 ms first-to-last latency (seven hops × four steps × 0.5 ms). Default RC output: 0.6931 ns per stage, 3.4657 ns summed path, reciprocal rounded to 0.29 GHz. Clock period requires setup/hold, clock uncertainty, loading, slew and actual circuit assumptions; this reciprocal is not a measured clock limit.

## Executed evidence

62 tests passed, zero failed/skipped, including eight new checks for sigmoid extremes, edge direction, inhibition, delays, RNG/dropout, GraphML defaults/entity rejection, invalid inputs and repeatable experiments. Current 62-test evidence applies to the source checkout; the earlier separately installed wheel had 54 tests and has not been rebuilt for this addition.

The original Python baseline was executed after inspection. baseline-results.json records a seeded reproduction. topology-results.json records 200 trials per cell, 20 nodes, 20 synchronous rounds, chain versus three-forward-neighbor mesh, dropout 30/50/70/85/95%, seed 20260930 and Wilson intervals.

The topology experiment is discrete SI with repeated attempts, not the sigmoid ODE or neural/RC hardware. Mesh has more edges and transmission attempts. At 85% loss it reaches complete coverage in 64/200 runs versus 0/200 for the chain within this horizon; at 95%, neither reaches complete coverage. Mean coverage and intervals are retained rather than interpreting zero full-coverage runs as eventual collapse. Moderate-loss results do not establish comparable convergence: mesh is markedly faster in this configuration. The stated universal 85% threshold and cross-domain equivalence are not established by these experiments.

## Next integration boundary

Implement domain-specific gossip, LIF/reset/refractory and continuous RC transitions behind an explicit common interface before claiming substrate equivalence. For resilience comparisons control node count, degree/transmission budget, source stimulus, observation horizon, success definition, dropout correlation and retry policy; compare baseline-subtracted signals for sigmoid drive. Build Rust with declared dependencies/target and reproduce Python vectors before binding GraphML data to WASM. Then bind validated runtime output to the operator UI with addressed bounded transport; optional Web Audio feedback must follow observed state and user activation. None of these missing browser/toolchain features prevents local runtime development.
