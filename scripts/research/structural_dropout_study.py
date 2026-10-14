#!/usr/bin/env python3
"""Reproducible SI reachability experiment; not LIF/RC or original trial replication."""
import argparse
import json
import math
from pathlib import Path
import random
import statistics
from keddeh_namespace.universal_propagation import Topology

def trial(topology, dropout, seed, budget=None):
    rng=random.Random(seed);informed={0};attempts=0;history=[1]
    for round_ in range(1,51):
        fresh=set()
        for edge in topology.edges:
            if edge.source not in informed or edge.target in informed or edge.target in fresh:continue
            if budget is not None and attempts>=budget:break
            attempts+=1
            if rng.random()>=dropout:fresh.add(edge.target)
        informed.update(fresh);history.append(len(informed))
        if len(informed)==len(topology.nodes):break
    return {'coverage':len(informed)/len(topology.nodes),'converged':len(informed)==len(topology.nodes),
            'rounds':round_,'attempts':attempts,'history':history}

def run(trials):
    n=8
    graphs={'chain':Topology.adjacency([[int(j==i+1) for j in range(n)] for i in range(n)]),
            'mesh':Topology.adjacency([[int(i!=j) for j in range(n)] for i in range(n)])}
    summaries=[];raw=[]
    for arm,budget in [('equal_rounds',None),('equal_rounds_and_attempt_budget',50)]:
        for drop in (.3,.7,.85,.95):
            for name,graph in graphs.items():
                rows=[trial(graph,drop,seed,budget) for seed in range(trials)]
                hits=sum(row['converged'] for row in rows);p=hits/trials;z=1.96;den=1+z*z/trials
                center=(p+z*z/(2*trials))/den
                half=z*math.sqrt(p*(1-p)/trials+z*z/(4*trials**2))/den
                summaries.append({'arm':arm,'topology':name,'dropout':drop,'trials':trials,'edges':len(graph.edges),
                                  'final_mean_coverage':statistics.mean(r['coverage'] for r in rows),
                                  'convergence_fraction':p,'convergence_wilson_95':[center-half,center+half],
                                  'mean_attempts':statistics.mean(r['attempts'] for r in rows),
                                  'mean_rounds':statistics.mean(r['rounds'] for r in rows)})
                raw.append({'arm':arm,'topology':name,'dropout':drop,'trials':rows})
    return {'schema':'keddeh.structural-dropout-study.v1','nodes':8,'max_rounds':50,'seeds':[0,trials-1],
            'model':'Synchronous epidemic SI; informed state retained; dropout independently resampled per attempted edge per round',
            'source_parser':'qualified directed Topology.adjacency; new experiment, not the original unlocated dataset',
            'scope':'software structural reachability; does not establish LIF/RC equivalence or physical substrate performance',
            'summaries':summaries,'raw':raw}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);ap.add_argument('--trials',type=int,default=1000);args=ap.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    result=run(args.trials)
    (out/'raw.json').write_text(json.dumps(result,indent=2)+'\n')
    public={k:v for k,v in result.items() if k!='raw'}
    (out/'summary.json').write_text(json.dumps(public,indent=2)+'\n')
    print(json.dumps(public,indent=2))
