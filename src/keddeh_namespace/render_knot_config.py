"""Role-bound Knot 3.4 configuration; key values are supplied through external includes."""
import argparse
import ipaddress
import json
from pathlib import PurePosixPath
from .compile_zones import validate_nodes,zone_name


def render(config,role,*,zone_file='/state/zone.zone',key_include='/secrets/transfer.conf',storage='/state',port=53):
    zone=zone_name(config['zone']);nodes=validate_nodes(config,zone)
    if role not in ('primary','secondary'): raise ValueError('invalid authority role')
    if type(port) is not int or not 1<=port<=65535: raise ValueError('invalid port')
    if config.get('production') is True and port!=53: raise ValueError('production authority requires port 53')
    for path in (zone_file,key_include,storage):
        if type(path) is not str or not PurePosixPath(path).is_absolute() or '..' in PurePosixPath(path).parts or any(c in path for c in '\n\r'):
            raise ValueError('canonical absolute configuration paths required')
    local=nodes[0 if role=='primary' else 1][1];remote=nodes[1 if role=='primary' else 0][1]
    # JSON quoting is valid for these YAML scalar values, preventing config injection.
    quote=json.dumps
    sections=[f'include: {quote(key_include)}',
      'server:\n  listen: '+quote(f'{local}@{port}')+'\n  rundir: '+quote(storage+'/run'),
      'database:\n  storage: '+quote(storage),
      'log:\n  - target: stdout\n    any: info',
      'remote:\n  - id: peer\n    address: '+quote(f'{remote}@{port}')+'\n    key: transfer-key',
      'acl:\n  - id: peer-transfer\n    address: '+quote(remote)+'\n    key: transfer-key\n    action: '+('transfer' if role=='primary' else 'notify'),
      'policy:\n  - id: namespace-signing\n    algorithm: ecdsap256sha256\n    ksk-lifetime: 0\n    zsk-lifetime: 30d',
      'zone:\n  - domain: '+quote(zone)+'\n    file: '+quote(zone_file)+'\n    acl: peer-transfer\n    journal-content: all\n    zonefile-load: difference'+
      ('\n    notify: peer\n    dnssec-signing: on\n    dnssec-policy: namespace-signing' if role=='primary' else '\n    master: peer')]
    return '\n\n'.join(sections)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config');parser.add_argument('role',choices=('primary','secondary'));parser.add_argument('output')
    parser.add_argument('--port',type=int,default=53)
    args=parser.parse_args()
    try:
        with open(args.config) as stream: config=json.load(stream)
        text=render(config,args.role,port=args.port)
        with open(args.output,'x') as stream: stream.write(text)
    except (ValueError,OSError,KeyError,TypeError) as exc: parser.exit(1,f'Render rejected: {exc}\n')


if __name__=='__main__': main()
