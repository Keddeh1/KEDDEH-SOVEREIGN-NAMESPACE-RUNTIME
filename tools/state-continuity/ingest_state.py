"""Ingest exact owner state carriers without substituting their source semantics.

The full bytes remain authoritative source state. The searchable projection is an
explicit derivative: it does not replace source operators or execute prose as Python.
"""
import argparse,hashlib,json,pathlib
from continuity import ContinuityVFS

def ingest(root, source, identity):
    raw=pathlib.Path(source).read_bytes();text=raw.decode('utf-8')
    c=ContinuityVFS(root);before=c.observe(identity)
    if before.status not in ('ABSENT','AVAILABLE'):
        raise ValueError('source carrier requires explicit recovery before mutation')
    event=c.vfs.write(identity,raw,expected_version=before.version or 0)
    readback=c.observe(identity)
    if readback.status!='AVAILABLE' or readback.payload!=raw:
        raise ValueError('source state readback differs')
    # Explicit source-local lexical projection, with byte ranges into exact original.
    terms=['S = (I, O, q, t)','Non-Null','identity','rehydrat','null_trap','SHIFT_ADD',
           'FI-01','R01','density matrix','729','POSIX','0.297','MOCK']
    links=[]
    for term in terms:
        token=term.encode();offset=0
        while True:
            at=raw.lower().find(token.lower(),offset)
            if at<0:break
            links.append({'term':term,'startByte':at,'endByte':at+len(token),'sourceDigest':event['digest']})
            offset=at+len(token)
    projection={'schema':'keddeh.source-local-state.v1','identity':identity,
                'origin':{'anchor':'owner-supplied-state','orientation':'retained'},
                'q':0,'active':True,'t':event['sequence'],
                'sourceDigest':event['digest'],'sourceBytes':len(raw),'links':links,
                'boundary':'Exact source carrier is retained; links are lexical projection only, not substituted algebra or inferred operational success.'}
    projection_identity=identity+'/projection'
    prior=c.observe(projection_identity)
    pe=c.vfs.write(projection_identity,json.dumps(projection,ensure_ascii=False,sort_keys=True).encode(),expected_version=prior.version or 0)
    return {'identity':identity,'source':event,'projection':pe,'readback':'byte-exact',
            'state':'AVAILABLE','coordinateZeroDoesNotDeactivate':True,'linkCount':len(links)}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('source');p.add_argument('identity');a=p.parse_args()
    print(json.dumps(ingest(a.root,a.source,a.identity),indent=2))
