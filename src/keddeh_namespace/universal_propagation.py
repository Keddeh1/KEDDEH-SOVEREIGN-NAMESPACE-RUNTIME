"""Directed delayed propagation and explicitly scoped topology experiments.

Units are caller-defined but consistent: decay/time, weight state/time,
threshold and scale in state units. History before t=0 is initial state.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import random
import xml.etree.ElementTree as ET


def finite(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError('values must be finite')
    return value


def sigmoid(z):
    z = finite(z)
    if z >= 0:
        return 1 / (1 + math.exp(-z))
    exp_z = math.exp(z)
    return exp_z / (1 + exp_z)


@dataclass(frozen=True)
class Edge:
    source: int
    target: int
    weight: float
    delay_steps: int = 0


@dataclass(frozen=True)
class Topology:
    nodes: tuple[str, ...]
    edges: tuple[Edge, ...]

    def __post_init__(self):
        if not self.nodes or len(self.nodes) > 1000 or len(set(self.nodes)) != len(self.nodes):
            raise ValueError('1..1000 unique nodes required')
        if len(self.edges) > 100000:
            raise ValueError('edge limit exceeded')
        pairs = set()
        for edge in self.edges:
            if not (0 <= edge.source < len(self.nodes) and 0 <= edge.target < len(self.nodes)):
                raise ValueError('edge index out of bounds')
            finite(edge.weight)
            if not isinstance(edge.delay_steps, int) or isinstance(edge.delay_steps, bool) or not 0 <= edge.delay_steps <= 10000:
                raise ValueError('bounded nonnegative integer delay required')
            if (edge.source, edge.target) in pairs:
                raise ValueError('duplicate edge')
            pairs.add((edge.source, edge.target))

    @classmethod
    def adjacency(cls, matrix):
        """Rows are sources; columns are destinations, including signed weights."""
        n = len(matrix)
        if not 1 <= n <= 1000 or any(len(row) != n for row in matrix):
            raise ValueError('bounded square adjacency matrix required')
        edges = tuple(Edge(i, j, finite(w)) for i, row in enumerate(matrix) for j, w in enumerate(row) if finite(w) != 0)
        return cls(tuple(str(i) for i in range(n)), edges)

    @classmethod
    def graphml(cls, path):
        raw = Path(path).read_bytes()
        if len(raw) > 2_000_000 or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
            raise ValueError('GraphML input too large or contains declarations')
        root = ET.fromstring(raw)
        ns = '{http://graphml.graphdrawing.org/xmlns}'
        graphs = root.findall(ns + 'graph')
        if len(graphs) != 1 or graphs[0].get('edgedefault') != 'directed':
            raise ValueError('one directed GraphML graph required')
        graph = graphs[0]
        if graph.findall('.//' + ns + 'graph') or graph.findall(ns + 'hyperedge'):
            raise ValueError('nested graphs and hyperedges unsupported')
        nodes = tuple(node.attrib['id'] for node in graph.findall(ns + 'node'))
        indices = {node: i for i, node in enumerate(nodes)}
        keys = {}
        for key in root.findall(ns + 'key'):
            name = key.get('attr.name')
            default = key.find(ns + 'default')
            if name in ('weight', 'delay_steps') and key.get('for') in ('edge', 'all'):
                keys[key.attrib['id']] = (name, default.text if default is not None else None)
        edges = []
        for element in graph.findall(ns + 'edge'):
            if element.get('directed') in ('false', '0'):
                raise ValueError('undirected edge unsupported')
            values = {name: default for name, default in keys.values() if default is not None}
            for datum in element.findall(ns + 'data'):
                if datum.get('key') in keys:
                    values[keys[datum.attrib['key']][0]] = datum.text
            try:
                edges.append(Edge(indices[element.attrib['source']], indices[element.attrib['target']], finite(values.get('weight', 1)), int(values.get('delay_steps', 0))))
            except (KeyError, TypeError) as exc:
                raise ValueError('invalid edge reference/data') from exc
        return cls(nodes, tuple(edges))


class PropagationRuntime:
    """Synchronous explicit Euler; dropout resampled per edge per tick."""
    def __init__(self, topology, *, dt=0.1, decay=1.0, threshold=0.0, scale=1.0, initial=None, dropout=0.0, seed=0):
        self.topology = topology
        self.dt, self.decay, self.threshold, self.scale, self.dropout = map(finite, (dt, decay, threshold, scale, dropout))
        if self.dt <= 0 or self.decay < 0 or self.dt * self.decay > 1 or self.scale <= 0 or not 0 <= self.dropout <= 1:
            raise ValueError('invalid parameters or non-monotone Euler leak step')
        self.states = [finite(v) for v in (initial if initial is not None else [0] * len(topology.nodes))]
        if len(self.states) != len(topology.nodes):
            raise ValueError('initial state length mismatch')
        self.initial = tuple(self.states)
        self.history = [tuple(self.states)]
        self.max_delay = max((e.delay_steps for e in topology.edges), default=0)
        self.rng = random.Random(seed)
        self.steps = 0

    def tick(self):
        incoming = [0.0] * len(self.states)
        for edge in self.topology.edges:
            if self.rng.random() < self.dropout:
                continue
            past = self.history[-1 - edge.delay_steps] if edge.delay_steps < len(self.history) else self.initial
            incoming[edge.target] += edge.weight * sigmoid((past[edge.source] - self.threshold) / self.scale)
        next_states = [finite(x + self.dt * (-self.decay * x + current)) for x, current in zip(self.states, incoming)]
        self.states = next_states
        self.history.append(tuple(next_states))
        self.history = self.history[-(self.max_delay + 1):]
        self.steps += 1
        return tuple(next_states)


def topology_experiment(*, nodes=20, rounds=20, trials=200, seed=20260930):
    """SI attempts to every outgoing neighbor per round; NOT the ODE or LIF.

Mesh has extra edges/attempts: this is a redundancy experiment, not a
communication-budget-matched comparison. Persistent retry permits recovery.
"""
    if nodes < 2 or rounds < 1 or trials < 1:
        raise ValueError('invalid experiment dimensions')
    results = []
    for drop in (0.3, 0.5, 0.7, 0.85, 0.95):
        for kind, reach in (('chain', 1), ('forward_mesh', 3)):
            success = 0
            coverage = []
            for trial in range(trials):
                rng = random.Random(seed + trial)
                informed = {0}
                for _ in range(rounds):
                    new = set()
                    for source in sorted(informed):
                        for target in range(source + 1, min(nodes, source + reach + 1)):
                            if rng.random() >= drop:
                                new.add(target)
                    informed.update(new)
                success += len(informed) == nodes
                coverage.append(len(informed) / nodes)
            # Wilson interval for finite-horizon full-coverage probability.
            p, z = success / trials, 1.96
            denominator = 1 + z*z/trials
            center = (p + z*z/(2*trials)) / denominator
            half = z * math.sqrt(p*(1-p)/trials + z*z/(4*trials*trials)) / denominator
            results.append({'topology': kind, 'dropout': drop, 'trials': trials, 'full_coverage_runs': success, 'full_coverage_probability': p, 'wilson_95_interval': [center-half, center+half], 'mean_coverage': sum(coverage)/trials})
    return {'model': 'discrete SI with per-attempt dropout and retries', 'nodes': nodes, 'rounds': rounds, 'seed': seed, 'limitations': ['mesh has more edges and transmission attempts', 'finite horizon; not eventual-convergence proof', 'not LIF, RC or physical hardware measurements'], 'results': results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--graphml')
    parser.add_argument('--adjacency-json')
    parser.add_argument('--steps', type=int, default=100)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--experiment', action='store_true')
    args = parser.parse_args()
    if args.experiment:
        print(json.dumps(topology_experiment(), indent=2)); return
    if bool(args.graphml) == bool(args.adjacency_json) or not 1 <= args.steps <= 10000:
        parser.error('provide one topology and 1..10000 steps')
    topology = Topology.graphml(args.graphml) if args.graphml else Topology.adjacency(json.loads(Path(args.adjacency_json).read_text()))
    runtime = PropagationRuntime(topology, seed=args.seed, initial=[1] + [0]*(len(topology.nodes)-1))
    for _ in range(args.steps): runtime.tick()
    print(json.dumps({'nodes': topology.nodes, 'steps': runtime.steps, 'states': runtime.states, 'scope': 'local delayed sigmoid model; no external actuation'}, indent=2))

if __name__ == '__main__':
    main()
