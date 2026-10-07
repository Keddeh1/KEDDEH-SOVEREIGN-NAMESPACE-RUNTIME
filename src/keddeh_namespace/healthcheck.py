"""Direct DNS UDP/TCP readback; never infer authoritative health from a PID."""
import argparse
import json
import hashlib
import dns.dnssec
import dns.name
import dns.flags
import dns.message
import dns.query
import dns.rcode
import dns.rdatatype
import dns.tsigkeyring
import dns.zone


def authority_probe(address,zone,*,port=53,timeout=3,pinned_dnskey_sha256=None):
    serials=[]
    for transport in (dns.query.udp,dns.query.tcp):
        request=dns.message.make_query(zone,'SOA');request.flags &= ~dns.flags.RD
        response=transport(request,address,port=port,timeout=timeout)
        if response.rcode()!=dns.rcode.NOERROR or not response.flags&dns.flags.AA or response.flags&dns.flags.TC:
            raise ValueError('non-authoritative or incomplete SOA response')
        records=[record for rrset in response.answer if rrset.rdtype==dns.rdatatype.SOA for record in rrset]
        if len(records)!=1: raise ValueError('missing/ambiguous SOA readback')
        serials.append(records[0].serial)
    if len(set(serials))!=1: raise ValueError('UDP/TCP serial divergence')
    # Query a name outside the hosted zone and demand explicit refusal.
    request=dns.message.make_query('recursion-test.invalid.','A')
    response=dns.query.udp(request,address,port=port,timeout=timeout)
    if response.rcode()!=dns.rcode.REFUSED or response.flags&dns.flags.RA:
        raise ValueError('external recursion refusal not demonstrated')
    request=dns.message.make_query(zone,'AXFR');request.flags &= ~dns.flags.RD
    response=dns.query.tcp(request,address,port=port,timeout=timeout)
    if response.rcode() not in (dns.rcode.REFUSED,dns.rcode.NOTAUTH) or response.answer:
        raise ValueError('unauthenticated AXFR denial not demonstrated')
    result={'address':address,'port':port,'soa_serial':serials[0],
            'authoritative_udp_tcp':'passed','recursion_refused':'passed','unauthenticated_axfr':'denied'}
    if pinned_dnskey_sha256 is not None:
        request=dns.message.make_query(zone,'DNSKEY',want_dnssec=True)
        response=dns.query.tcp(request,address,port=port,timeout=timeout)
        keys=[rr for rr in response.answer if rr.rdtype==dns.rdatatype.DNSKEY]
        if response.rcode()!=dns.rcode.NOERROR or not response.flags&dns.flags.AA or len(keys)!=1:
            raise ValueError('authoritative DNSKEY missing')
        key_digest=hashlib.sha256('\n'.join(sorted(key.to_text() for key in keys[0])).encode()).hexdigest()
        if key_digest!=pinned_dnskey_sha256: raise ValueError('DNSKEY does not match trusted generation pin')
        request=dns.message.make_query(zone,'SOA',want_dnssec=True)
        response=dns.query.tcp(request,address,port=port,timeout=timeout)
        soa=[rr for rr in response.answer if rr.rdtype==dns.rdatatype.SOA]
        signatures=[rr for rr in response.answer if rr.rdtype==dns.rdatatype.RRSIG and rr.covers==dns.rdatatype.SOA]
        if len(soa)!=1 or len(signatures)!=1: raise ValueError('signed SOA missing')
        dns.dnssec.validate(soa[0],signatures[0],{dns.name.from_text(zone):keys[0]})
        result.update(dnskey_sha256=key_digest,dnssec_soa='verified_against_generation_pin')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('zone');parser.add_argument('addresses',nargs=2)
    parser.add_argument('--port',type=int,default=53)
    args=parser.parse_args()
    try:
        nodes=[authority_probe(address,args.zone,port=args.port) for address in args.addresses]
        if nodes[0]['soa_serial']!=nodes[1]['soa_serial']: raise ValueError('node serials diverge')
    except (ValueError,dns.exception.DNSException,OSError) as exc: parser.exit(1,f'Authority rejected: {exc}\n')
    print(json.dumps({'nodes':nodes,'status':'partial_authority_checks_passed',
                      'remaining':['DNSSEC trust-chain verification','TSIG transfer','unauthenticated AXFR refusal','independent failure domains']},sort_keys=True))


if __name__ == '__main__': main()
