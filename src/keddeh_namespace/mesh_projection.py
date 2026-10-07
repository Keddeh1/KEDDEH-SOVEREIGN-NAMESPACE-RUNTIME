"""Join actual WEB4 readback to explicitly supplied geometry; never invent positions."""
from datetime import datetime, timezone
import math


def project_mesh(readback, geometry):
    if readback.get('schema') != 'keddeh.web4.readback.v1':
        raise ValueError('WEB4 readback required')
    def number(value):
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError('finite numeric geometry required')
        return value
    origin = {k: number(geometry['origin'][k]) for k in ('x', 'y', 'z')}
    phase = number(geometry['substratePhase'])
    records = readback['nodes']
    if len(records) > 512 or len({r['port'] for r in records}) != len(records):
        raise ValueError('bounded unique runtime node identities required')
    mapping = geometry['nodes']
    if len(mapping) != len(records) or {str(r['port']) for r in records} != set(mapping):
        raise ValueError('geometry must account for every runtime node exactly once')
    output = []
    for record in records:
        key = str(record['port'])
        shape = mapping[key]
        radius = number(shape['loopRadius'])
        if radius <= 0:
            raise ValueError('positive loop radius required')
        route = shape['serviceUrl']
        if not isinstance(route, str) or not route.startswith('/') or route.startswith('//') or any(c in route for c in '\\?#\r\n'):
            raise ValueError('explicit local service route required')
        output.append(dict(id='web4:node:'+key, label=str(record.get('domain') or 'Workstation '+key),
                           **{k:number(shape[k]) for k in ('x','y','z')}, loopRadius=radius,
                           serviceUrl=route, health='observed-healthy' if record.get('ok') is True else 'unavailable',
                           stateHash=record.get('state_hash'), computeCycles=record.get('compute_cycles')))
    return dict(schema='keddeh.mesh.projection.v1', origin=origin, substratePhase=phase,
                observedAt=datetime.now(timezone.utc).isoformat(), nodes=output,
                geometrySource=geometry['source'], scope='WEB4 readback joined to declared geometry; no inferred evolution')
