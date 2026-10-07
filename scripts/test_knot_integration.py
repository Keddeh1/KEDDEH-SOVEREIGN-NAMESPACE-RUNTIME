#!/usr/bin/env python3
"""Optional Docker integration test: isolated fixture authority, automatic cleanup."""
import base64
import hashlib
import ipaddress
import json
import os
import secrets
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
import dns.message
import dns.query
import dns.rdatatype
from keddeh_namespace.compile_zones import compile_zone
from keddeh_namespace.envelope import canonical_bytes
from keddeh_namespace.healthcheck import authority_probe
from keddeh_namespace.render_knot_config import render

IMAGE='cznic/knot@sha256:6a196ea3300d764bbed0ab48e41d5d91ce6ed093e299be8896589b13f00b8079'


def run(*args):
    result=subprocess.run(['docker',*args],capture_output=True,text=True)
    if result.returncode: raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def main():
    network='keddeh-test-'+uuid.uuid4().hex[:10]
    names=[];created=False
    existing=json.loads(run('network','inspect',*run('network','ls','-q').split()))
    occupied=[ipaddress.ip_network(c['Subnet']) for n in existing for c in (n.get('IPAM',{}).get('Config') or []) if c.get('Subnet')]
    subnet=next((ipaddress.ip_network(f'172.{i}.0.0/16') for i in range(18,32)
                 if not any(ipaddress.ip_network(f'172.{i}.0.0/16').overlaps(n) for n in occupied if n.version==4)),None)
    if subnet is None: raise RuntimeError('no unused private test subnet')
    with tempfile.TemporaryDirectory(prefix='keddeh-knot-') as temporary:
        root=Path(temporary);root.chmod(0o755)
        primary=str(subnet.network_address+2);secondary=str(subnet.network_address+3)
        config={'zone':'example.test','production':False,'nodes':[{'role':'primary','name':'ns1.example.test','public_ip':primary},
                                                                 {'role':'secondary','name':'ns2.example.test','public_ip':secondary}]}
        inventory={'zone':'example.test','captured_at':'2026-10-07T00:00:00Z','authority':'fixture','records':[
            {'host':'@','ttl':60,'type':'SOA','value':'ns1.example.test. admin.example.test. 1 60 10 3600 60'},
            {'host':'@','ttl':60,'type':'NS','value':'ns1.example.test.'},{'host':'@','ttl':60,'type':'NS','value':'ns2.example.test.'},
            {'host':'ns1','ttl':60,'type':'A','value':primary},{'host':'ns2','ttl':60,'type':'A','value':secondary},
            {'host':'@','ttl':60,'type':'MX','value':'1 smtp.google.com.'}]}
        config['preservation_sha256']=hashlib.sha256(canonical_bytes(inventory)).hexdigest()
        zone,_=compile_zone(inventory,config)
        key='key:\n  - id: transfer-key\n    algorithm: hmac-sha256\n    secret: '+base64.b64encode(secrets.token_bytes(32)).decode()+'\n'
        try:
            run('network','create','--subnet',str(subnet),network);created=True
            for role,address in [('primary',primary),('secondary',secondary)]:
                directory=root/role;directory.mkdir();(directory/'run').mkdir()
                (directory/'zone.zone').write_text(zone)
                (directory/'transfer.conf').write_text(key);(directory/'transfer.conf').chmod(0o600)
                (directory/'knot.conf').write_text(render(config,role,zone_file='/state/zone.zone',key_include='/state/transfer.conf',port=15353))
                run('run','--rm','--user',f'{os.getuid()}:{os.getgid()}','--entrypoint','knotc','-v',f'{directory}:/state',IMAGE,'-c','/state/knot.conf','conf-check')
                name=network+'-'+role
                run('run','-d','--name',name,'--user',f'{os.getuid()}:{os.getgid()}','--cap-drop=ALL','--read-only',
                    '--tmpfs','/tmp:rw,noexec,nosuid,size=64m','--cpus','1','--memory','256m','--pids-limit','64',
                    '--security-opt','no-new-privileges','--network',network,'--ip',address,
                    '-p','127.0.0.1::15353/tcp','-p','127.0.0.1::15353/udp','-v',f'{directory}:/state',
                    '--entrypoint','knotd',IMAGE,'-c','/state/knot.conf')
                names.append(name)
            def ports(name):
                info=json.loads(run('inspect',name))[0]
                mapping=info['NetworkSettings']['Ports']
                return int(mapping['15353/tcp'][0]['HostPort']),int(mapping['15353/udp'][0]['HostPort'])
            # Docker may allocate different TCP/UDP host ports; direct protocols use their own bindings.
            for attempt in range(40):
                try:
                    tcp,udp=ports(names[0])
                    response=dns.query.tcp(dns.message.make_query('example.test','DNSKEY',want_dnssec=True),'127.0.0.1',port=tcp,timeout=1)
                    keys=next(rr for rr in response.answer if rr.rdtype==dns.rdatatype.DNSKEY)
                    pin=hashlib.sha256('\n'.join(sorted(k.to_text() for k in keys)).encode()).hexdigest()
                    break
                except (OSError,StopIteration,dns.exception.DNSException): time.sleep(0.2)
            else: raise RuntimeError('primary DNSSEC readiness failed')
            # Use Docker-published UDP port for UDP and TCP port for TCP separately.
            results=[]
            for name in names:
                tcp,udp=ports(name)
                for attempt in range(40):
                    try:
                        # Standard probe assumes common port; internal Docker network has the same port.
                        # Invoke a client using the node network namespace for that direct check below.
                        soa_tcp=dns.query.tcp(dns.message.make_query('example.test','SOA',want_dnssec=True),'127.0.0.1',port=tcp,timeout=1)
                        soa_udp=dns.query.udp(dns.message.make_query('example.test','SOA'),'127.0.0.1',port=udp,timeout=1)
                        from dns import flags,rcode,dnssec,name as dnsname
                        soa=next(rr for rr in soa_tcp.answer if rr.rdtype==dns.rdatatype.SOA)
                        signature=next(rr for rr in soa_tcp.answer if rr.rdtype==dns.rdatatype.RRSIG and rr.covers==dns.rdatatype.SOA)
                        assert soa_tcp.flags&flags.AA and soa_udp.flags&flags.AA
                        assert soa_udp.answer[0][0].serial==soa[0].serial
                        dnssec.validate(soa,signature,{dnsname.from_text('example.test'):keys})
                        recursive=dns.query.udp(dns.message.make_query('outside.invalid','A'),'127.0.0.1',port=udp,timeout=1)
                        assert recursive.rcode()==rcode.REFUSED and not recursive.flags&flags.RA
                        axfr=dns.query.tcp(dns.message.make_query('example.test','AXFR'),'127.0.0.1',port=tcp,timeout=1)
                        assert axfr.rcode() in (rcode.REFUSED,rcode.NOTAUTH) and not axfr.answer
                        results.append({'role':'primary' if name==names[0] else 'secondary','soa_serial':soa[0].serial,
                                        'udp_tcp_aa':'passed','dnssec_signature':'passed','recursion':'refused','unauthenticated_axfr':'denied'})
                        break
                    except (AssertionError,StopIteration,OSError,dns.exception.DNSException): time.sleep(0.2)
                else: raise RuntimeError('authority node readiness failed')
            if results[0]['soa_serial']!=results[1]['soa_serial']: raise RuntimeError('serial divergence')
            logs=run('logs',names[1])
            if 'key transfer-key.' not in logs or 'IXFR, incoming' not in logs: raise RuntimeError('authenticated transfer not observed')
            print(json.dumps({'image':IMAGE,'nodes':results,'tsig_transfer':'observed',
                              'scope':'local fixture containers; not independent production domains or registrar DS validation'},indent=2))
        finally:
            for name in names: subprocess.run(['docker','rm','-f',name],capture_output=True)
            if created: subprocess.run(['docker','network','rm',network],capture_output=True)


if __name__=='__main__': main()
