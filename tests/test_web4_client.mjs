import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const sent=[];
const host={host_id:'h',instance_id:'i',source_digest:'s',pipeline_generation:2,services:[{name:'http',generation:7,pid:123}]};
const context={window:{dispatchEvent(){}},crypto:{randomUUID:()=> 'request-1'},CustomEvent:class{},AbortSignal,
 fetch:async(path,options)=>{const body=JSON.parse(options.body);sent.push(body);return {ok:true,json:async()=>body.action==='pipeline'?{generation:3}:body.operation==='status'?host:{structuredContent:{status:'COMPLETED'}}};}};
vm.runInNewContext(fs.readFileSync(new URL('../src/keddeh_namespace/web4_client.js',import.meta.url),'utf8'),context);
await context.window.KEDDEH_WEB4.service('restart','http');
assert.equal(sent.at(-1).action,'estate');assert.equal(sent.at(-1).tool,'host_actuator');
const command=sent.at(-1).arguments;
assert.equal(command.operation,'restart');
assert.equal(command.expected_generation,7);assert.equal(command.expected_pid,123);
assert.equal(command.pipeline_generation,2,'do not replace descriptor fence with newer gate generation');
assert.equal(command.instance_id,'i');assert.equal(command.request_id,'request-1');
await assert.rejects(()=>context.window.KEDDEH_WEB4.service('start','unknown'),/Unknown owned/);
console.log('WEB4 client descriptor binding and stale-generation preservation: passed');
