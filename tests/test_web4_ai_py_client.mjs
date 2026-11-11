import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import test from 'node:test';

const source = readFileSync(new URL('../src/keddeh_namespace/web4_client.js', import.meta.url),'utf8');
function fixture(response = {ok: true,status:200,json:async()=>({state:'RECORDED'})}){
  const requests=[], events=[];
  const win={prompt:()=> 'private-local-token',dispatchEvent:e=>events.push(e)};
  class CustomEvent {constructor(name,data){this.name=name;this.detail=data.detail;}}
  runInNewContext(source,{window:win,CustomEvent,fetch:async(path,init)=>{requests.push({path,init});return response;}});
  return {win,requests,events};
}
test('AI.PY route uses original owner authentication, not new credentials',async()=>{
  const f=fixture();
  assert.equal(f.win.KEDDEH_WEB4.authenticate(),true);
  const result=await f.win.KEDDEH_WEB4.aiPy.status();
  assert.equal(result.state,'RECORDED');
  assert.equal(f.requests[0].path,'/api/ai-py/binding/status');
  assert.equal(f.requests[0].init.method,'GET');
  assert.equal(f.requests[0].init.headers.Authorization,'Bearer private-local-token');
  assert.equal(f.win.KEDDEH_WEB4.token,undefined);
});
test('execution envelope uses bounded POST and 202 uncertain stays uncertain',async()=>{
  const f=fixture({ok:true,status:202,json:async()=>({state:'OUTCOME_UNCERTAIN',requestId:'test-request-01'})});
  const req={schema:'braink.ai-py.execution-request.v1',requestId:'test-request-01',operation:'mesh_discover',arguments:{}};
  const result=await f.win.KEDDEH_WEB4.aiPy.execute(req);
  assert.equal(result.state,'OUTCOME_UNCERTAIN');
  assert.equal(f.requests[0].path,'/api/ai-py/execute');
  assert.equal(f.requests[0].init.method,'POST');
  assert.equal(JSON.parse(f.requests[0].init.body).requestId,req.requestId);
});
test('receipt URL forbids traversal and mutation of route',async()=>{
  const f=fixture();
  await f.win.KEDDEH_WEB4.aiPy.receipt('test-request-01');
  assert.equal(f.requests[0].path,'/api/ai-py/receipts/test-request-01');
  assert.equal(f.requests[0].init.method,'GET');
  assert.throws(()=>f.win.KEDDEH_WEB4.aiPy.receipt('../etc'),/Invalid AI.PY receipt ID/);
  assert.equal(f.requests.length,1);
  await assert.rejects(f.win.KEDDEH_WEB4.request('/api/root/unsafe'),/Unsupported owner route/);
});
test('unbound or unauthorized gateway response does not become success',async()=>{
  const f=fixture({ok:false,status:503,json:async()=>({error:'NO_PYTHON_HOST_BINDING'})});
  await assert.rejects(f.win.KEDDEH_WEB4.aiPy.status(),/NO_PYTHON_HOST_BINDING/);
  assert.equal(f.events.length,0);
});
