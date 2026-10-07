"""Compile a complete custody inventory deterministically; no live DNS mutation."""
import argparse
import hashlib
import ipaddress
import json
import re
import dns.name
import dns.rdata
import dns.rdataclass
import dns.rdatatype
import dns.zone
from .envelope import canonical_bytes


def zone_name(value):
    if type(value) is not str or not re.fullmatch(r'[A-Za-z0-9.-]+',value):
        raise ValueError('invalid zone name')
    name=dns.name.from_text(value)
    if len(name.labels)<3 or any(not label for label in name.labels[:-1]): raise ValueError('fully qualified zone required')
    return name.to_text().lower()


def validate_nodes(config,zone):
    nodes=config.get('nodes')
    if type(nodes) is not list or len(nodes)!=2: raise ValueError('two nodes required')
    result=[]
    for role,node in zip(('primary','secondary'),nodes):
        if type(node) is not dict or not {'role','name','public_ip'}.issubset(node): raise ValueError('complete node fields required')
        if node.get('role')!=role: raise ValueError('node role/order mismatch')
        name=zone_name(node['name'])
        if not name.endswith('.'+zone): raise ValueError('in-bailiwick node name required')
        address=ipaddress.ip_address(node['public_ip'])
        if address.is_multicast or address.is_unspecified: raise ValueError('unicast node address required')
        if config.get('production') is True and not address.is_global: raise ValueError('stable public addresses required')
        result.append((name,str(address)))
    if len({n for n,_ in result})!=2 or len({a for _,a in result})!=2: raise ValueError('distinct node names and addresses required')
    return result


def compile_zone(inventory,config):
    if type(inventory) is not dict or set(inventory)!={'zone','captured_at','authority','records'}:
        raise ValueError('complete inventory metadata required')
    zone=zone_name(inventory['zone'])
    if zone_name(config['zone'])!=zone: raise ValueError('zone mismatch')
    if type(inventory['authority']) is not str or not inventory['authority'].strip(): raise ValueError('source authority required')
    from datetime import datetime
    timestamp=datetime.fromisoformat(inventory['captured_at'].replace('Z','+00:00'))
    if timestamp.utcoffset() is None: raise ValueError('timestamp timezone required')
    preservation=hashlib.sha256(canonical_bytes(inventory)).hexdigest()
    if config.get('preservation_sha256')!=preservation: raise ValueError('preservation hash mismatch or missing')
    records=inventory['records']
    if type(records) is not list or not records: raise ValueError('nonempty complete inventory required')
    lines=[];seen=set();soa_count=0
    for record in records:
        if type(record) is not dict or set(record)!={'host','ttl','type','value'}: raise ValueError('invalid record fields')
        host=record['host'];kind=record['type'];value=record['value'];ttl=record['ttl']
        if type(host) is not str or type(kind) is not str or type(value) is not str or '\n' in value or '\r' in value:
            raise ValueError('invalid record text')
        if type(ttl) is not int or not 0<=ttl<=2147483647: raise ValueError('invalid TTL')
        origin=dns.name.from_text(zone)
        owner=dns.name.from_text(host,origin=origin)
        if not owner.is_subdomain(origin): raise ValueError('record escapes inventory zone')
        typ=dns.rdatatype.from_text(kind)
        if typ in (dns.rdatatype.AXFR,dns.rdatatype.IXFR,dns.rdatatype.ANY): raise ValueError('non-zone record type')
        dns.rdata.from_text(dns.rdataclass.IN,typ,value,origin=origin)
        if kind.upper()=='SOA':
            if owner!=origin: raise ValueError('SOA must be apex')
            soa_count+=1
        line=f'{owner.to_text()} {ttl} IN {kind.upper()} {value}'
        if line in seen: raise ValueError('duplicate inventory record')
        seen.add(line);lines.append(line)
    if soa_count!=1: raise ValueError('exactly one preserved SOA required')
    text='$ORIGIN '+zone+'\n'+'\n'.join(sorted(lines))+'\n'
    dns.zone.from_text(text,origin=zone,relativize=False,check_origin=True)
    if config.get('production') is True: validate_nodes(config,zone)
    # This compiler imports preserved hosted-zone records exactly. Authority NS/SOA
    # changes are a separately reviewed generation; never infer them from labels.
    return text,{'zone':zone,'preservation_sha256':preservation,
                 'zone_sha256':hashlib.sha256(text.encode()).hexdigest(),
                 'records':len(records),'status':'compiled_preserved_inventory'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inventory');parser.add_argument('config');parser.add_argument('output')
    parser.add_argument('--authority-generation',action='store_true',help='explicit staged NS/SOA change; no live mutation')
    args=parser.parse_args()
    try:
        with open(args.inventory) as stream: inventory=json.load(stream)
        with open(args.config) as stream: config=json.load(stream)
        text,receipt=(prepare_authority_generation(inventory,config) if args.authority_generation else compile_zone(inventory,config))
        with open(args.output,'x') as stream: stream.write(text)
    except (OSError,ValueError,KeyError,TypeError,dns.exception.DNSException) as exc:
        parser.exit(1,f'Compilation rejected: {exc}\n')
    print(json.dumps(receipt,sort_keys=True))




def prepare_authority_generation(inventory,config):
    """Explicit staged authority change; retains every non-authority record.

    This produces a reviewed desired zone, never mutates hosted DNS or delegation.
    """
    import copy
    import dns.serial
    baseline,receipt=compile_zone(inventory,config)
    zone=zone_name(inventory['zone']);nodes=validate_nodes(config,zone)
    serial=config.get('soa_serial')
    if type(serial) is not int or not 0<=serial<2**32: raise ValueError('explicit uint32 authority SOA serial required')
    origin=dns.name.from_text(zone)
    desired=copy.deepcopy(inventory);retained=[];removed=[]
    for record in inventory['records']:
        owner=dns.name.from_text(record['host'],origin=origin);kind=record['type'].upper()
        if kind=='SOA':
            soa=dns.rdata.from_text(dns.rdataclass.IN,dns.rdatatype.SOA,record['value'],origin=origin)
            if not dns.serial.Serial(serial)>dns.serial.Serial(soa.serial): raise ValueError('authority SOA serial must advance')
            value=f'{nodes[0][0]} {soa.rname.to_text()} {serial} {soa.refresh} {soa.retry} {soa.expire} {soa.minimum}'
            retained.append(dict(record,value=value));removed.append(record)
        elif (kind=='NS' and owner==origin) or (kind in ('A','AAAA') and owner.to_text().lower() in {n for n,_ in nodes}):
            removed.append(record)
        else: retained.append(record)
    for name,address in nodes:
        retained.append(dict(host='@',ttl=1800,type='NS',value=name))
        retained.append(dict(host=name,ttl=1800,type='A' if ipaddress.ip_address(address).version==4 else 'AAAA',value=address))
    desired['records']=retained
    staged_config=dict(config,preservation_sha256=hashlib.sha256(canonical_bytes(desired)).hexdigest())
    text,staged_receipt=compile_zone(desired,staged_config)
    return text,{'schema':'keddeh.authority-generation.v1','original_preservation_sha256':receipt['preservation_sha256'],
                 'staged_inventory_sha256':staged_receipt['preservation_sha256'],'zone_sha256':staged_receipt['zone_sha256'],
                 'changed_authority_records':removed,'status':'staged_authority_change_not_delegated'}


if __name__ == '__main__': main()
