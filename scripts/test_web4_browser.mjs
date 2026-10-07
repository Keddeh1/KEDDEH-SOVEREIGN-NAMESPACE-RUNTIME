#!/usr/bin/env node
// Actual preserved terminal, authenticated cloud commands and two-tab mesh.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import net from 'node:net';
import {spawn} from 'node:child_process';
const args=process.argv.slice(2);
const root=args.includes('--root')?args[args.indexOf('--root')+1]:'/workspace/braink-setup/web4-runtime';
const cfg=JSON.parse(fs.readFileSync(path.join(root,'launch.json'),'utf8'));
const token=fs.readFileSync(path.join(root,'state/token'),'utf8');
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'keddeh-web4-browser-'));
const debugPort=await new Promise(resolve=>{const server=net.createServer();server.listen(0,'127.0.0.1',()=>{const port=server.address().port;server.close(()=>resolve(port));});});
const flags=['--headless','--disable-gpu',`--user-data-dir=${temp}/profile`,`--remote-debugging-port=${debugPort}`,'--remote-debugging-address=127.0.0.1','--no-first-run','--no-default-browser-check','about:blank'];
if(args.includes('--container-no-sandbox'))flags.push('--no-sandbox');
const browser=spawn('chromium',flags,{env:{...process.env,XDG_CONFIG_HOME:`${temp}/config`,XDG_CACHE_HOME:`${temp}/cache`},stdio:['ignore','ignore','ignore']});
const connections=[];
class CDP {
 constructor(ws){this.ws=ws;this.next=0;this.pending=new Map();this.onEvent=()=>{};ws.addEventListener('message',event=>{const data=JSON.parse(event.data);if(data.id){const entry=this.pending.get(data.id);if(entry){this.pending.delete(data.id);clearTimeout(entry.timer);data.error?entry.reject(new Error(data.error.message)):entry.resolve(data.result);}}else this.onEvent(data);});}
 send(method,params={}){const id=++this.next;return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{this.pending.delete(id);reject(new Error('CDP deadline: '+method));},10000);this.pending.set(id,{resolve,reject,timer});this.ws.send(JSON.stringify({id,method,params}));});}
 async evaluate(expression){const result=await this.send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw new Error('Browser execution failed');return result.result.value;}
 close(){this.ws.close();for(const entry of this.pending.values()){clearTimeout(entry.timer);entry.reject(new Error('CDP closed'));}this.pending.clear();}
}
async function poll(fn,limit=10000){const until=Date.now()+limit;while(Date.now()<until){try{const result=await fn();if(result)return result;}catch{}await delay(100);}throw new Error('Browser readiness/readback deadline');}
async function tab(route="/terminal"){const page=await fetch(`http://127.0.0.1:${debugPort}/json/new?${encodeURIComponent(`http://127.0.0.1:${cfg.ports.gateway}${route}`)}`,{method:'PUT'}).then(r=>r.json());const ws=new WebSocket(page.webSocketDebuggerUrl);await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true});});const cdp=new CDP(ws);connections.push(cdp);await cdp.send('Page.enable');await cdp.send('Runtime.enable');await poll(()=>cdp.evaluate("Boolean(window.KEDDEH_WEB4 && document.getElementById('keddeh-web4-panel'))"));return cdp;}
try{
 await poll(async()=>{const result=await fetch(`http://127.0.0.1:${debugPort}/json/version`);return result.ok;});
 const first=await tab();
 first.onEvent=event=>{if(event.method==='Page.javascriptDialogOpening'){const match=event.params.message==='Enter the local runtime token from the private state/token file';first.send('Page.handleJavaScriptDialog',{accept:match||event.params.message.includes('Accept these owner-local service permissions?'),promptText:match?token:''}).catch(()=>{});}};
 await first.evaluate("runCommand('cloud auth')");
 await first.evaluate("runCommand('cloud status')");
 if(!await first.evaluate('/"healthy_nodes":\\s*10/.test(document.getElementById("terminal").textContent)'))throw new Error('Cloud status did not show ten backend nodes');
 await first.evaluate("[...document.querySelectorAll('#keddeh-web4-panel button')].find(b=>b.textContent==='Accept service agreement').click()");
 await poll(()=>first.evaluate("document.getElementById('keddeh-web4-output').textContent.includes('\"accepted\": true')"));
 await first.evaluate("runCommand('cloud commit 3 65537 WEB4_BROWSER')");
 if(!await first.evaluate('document.getElementById("terminal").textContent.includes("ACTOR_COMMITTED")'))throw new Error('Browser did not actuate real R36 commit');
 await first.evaluate("runCommand('cloud enact')");
 if(!await first.evaluate('document.getElementById("terminal").textContent.includes("WEB4_PROPAGATION") || document.getElementById("terminal").textContent.includes("clamp state to")'))throw new Error('Browser propagation actuation missing');
 const second=await tab();
 await poll(()=>first.evaluate('Object.keys(state.mesh.peers).length>=1'));
 await first.evaluate("runCommand('mesh broadcast WEB4_BROWSER_PROBE')");
 await poll(()=>second.evaluate('state.mesh.messages.some(message=>message.body==="WEB4_BROWSER_PROBE")'));
 for(const route of ['/carrier','/research']) {
   const carrier=await tab(route);
   carrier.onEvent=event=>{if(event.method==='Page.javascriptDialogOpening')carrier.send('Page.handleJavaScriptDialog',{accept:true,promptText:token}).catch(()=>{});};
   await carrier.evaluate('window.KEDDEH_WEB4.authenticate()');
   const readback=await carrier.evaluate('window.KEDDEH_WEB4.request("/api/web4/status")');
   if(readback.healthy_nodes!==10)throw new Error('Carrier cloud binding failed: '+route);
 }
 console.log(JSON.stringify({status:'passed',checks:['preserved terminal boots in Chromium','authenticated cloud status reads ten actual nodes','browser command commits an actual R36 register','browser propagation command actuates actual R36 registers','two real tabs discover peers and deliver owner terminal mesh message','HTML carrier and resident research UI each read actual cloud state through shared panel'],scope:'headless browser and same-origin local cloud runtime',chromiumSandbox:args.includes('--container-no-sandbox')?'disabled for container test only; no browser isolation claim':'default'},null,2));
}finally{
 for(const cdp of connections)cdp.close();
 browser.kill('SIGTERM');
 await Promise.race([new Promise(resolve=>browser.once('exit',resolve)),delay(3000)]);
 if(browser.exitCode===null)browser.kill('SIGKILL');
 fs.rmSync(temp,{recursive:true,force:true});
}
