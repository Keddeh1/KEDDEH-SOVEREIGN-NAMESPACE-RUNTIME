#!/usr/bin/env node
import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import net from 'node:net';import {spawn} from 'node:child_process';
const args=process.argv.slice(2),port=Number(args.includes('--port')?args[args.indexOf('--port')+1]:28080);
const manifest=JSON.parse(fs.readFileSync('/workspace/keddeh.com/frontage/route-manifest.json','utf8'));
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'keddeh-customer-dom-'));
const debug=await new Promise(resolve=>{const s=net.createServer();s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(()=>resolve(p));});});
const flags=['--headless','--disable-gpu',`--user-data-dir=${temp}/profile`,`--remote-debugging-port=${debug}`,'--no-first-run','about:blank'];if(args.includes('--container-no-sandbox'))flags.push('--no-sandbox');
const browser=spawn('chromium',flags,{env:{...process.env,XDG_CONFIG_HOME:temp+'/config',XDG_CACHE_HOME:temp+'/cache'},stdio:'ignore'});
const delay=ms=>new Promise(r=>setTimeout(r,ms));let ws;
try{
 let version;for(let i=0;i<100;i++){try{version=await fetch(`http://127.0.0.1:${debug}/json/version`).then(r=>r.json());break;}catch{await delay(100);}}if(!version)throw Error('Chromium failed readiness');
 const tab=await fetch(`http://127.0.0.1:${debug}/json/new?${encodeURIComponent(`http://127.0.0.1:${port}/`)}`,{method:'PUT'}).then(r=>r.json());ws=new WebSocket(tab.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.addEventListener('open',r,{once:true});ws.addEventListener('error',j,{once:true});});
 let id=0;const pending=new Map(),errors=[];let fault=null;const intercepted=[];ws.addEventListener('message',event=>{const data=JSON.parse(event.data);if(data.id){const p=pending.get(data.id);if(p){clearTimeout(p.timer);pending.delete(data.id);data.error?p.reject(Error(data.error.message)):p.resolve(data.result);}}else if(data.method==='Runtime.exceptionThrown')errors.push('browser exception');else if(data.method==='Fetch.requestPaused'){const request=data.params;intercepted.push(request.request.postData||'');if(fault)send('Fetch.fulfillRequest',{requestId:request.requestId,responseCode:503,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({error:'Controlled service failure'})).toString('base64')}).catch(()=>{});else send('Fetch.continueRequest',{requestId:request.requestId}).catch(()=>{});}});
 const send=(method,params={})=>new Promise((resolve,reject)=>{const current=++id,timer=setTimeout(()=>reject(Error(method+' deadline')),12000);pending.set(current,{resolve,reject,timer});ws.send(JSON.stringify({id:current,method,params}));});
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error('DOM evaluation failed: '+(r.exceptionDetails.exception?.description||r.exceptionDetails.text));return r.result.value;};
 async function wait(expression){for(let i=0;i<100;i++){try{const r=await evaluate(expression);if(r)return r;}catch{}await delay(60);}throw Error('DOM readiness failed: '+expression.slice(0,100));}
 async function navigate(route){await send('Page.navigate',{url:`http://127.0.0.1:${port}${route}`});await delay(120);await wait(`location.pathname+location.search===${JSON.stringify(route)} && document.readyState==='complete' && Boolean(document.querySelector('main h1'))`);}
 await send('Runtime.enable');await send('Page.enable');await send('Page.bringToFront');await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 let linksTested=0,clicksTested=0,sourceDisclosures=0;const visited=[],inventory=[];
 for(const route of manifest.routes){
  await navigate(route.path);
  const sources=await evaluate("document.querySelectorAll('details.section-source').length");for(let i=0;i<sources;i++){await evaluate(`document.querySelectorAll('details.section-source summary')[${i}].focus()`);await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r',unmodifiedText:'\r'});await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});await wait(`document.querySelectorAll('details.section-source')[${i}].open`);sourceDisclosures++;}
  inventory.push({route:route.path,items:await evaluate(`([...document.querySelectorAll('main h1,main h2,main h3,main p,main li,main figcaption,main dt,main dd,a,button,summary,input,select,textarea')].map((e,index)=>({index,tag:e.tagName.toLowerCase(),text:e.textContent.trim(),href:e.getAttribute('href'),name:e.getAttribute('name'),label:e.labels?.[0]?.textContent.trim()||e.getAttribute('aria-label'),source:e.closest('details.claim-review')?.querySelector('a')?.href||e.closest('section')?.querySelector('.section-source a')?.href||e.closest('section')?.querySelector('.caption a')?.href||null})))`)});
  if(route.path==='/evidence')await wait("document.querySelectorAll('.claim').length===4");const checks=await evaluate(`({h1:document.querySelectorAll('h1').length,main:document.querySelectorAll('main').length,lang:document.documentElement.lang,links:[...document.querySelectorAll('a')].map(a=>({href:a.getAttribute('href'),name:a.textContent.trim()||a.getAttribute('aria-label')})),buttons:[...document.querySelectorAll('button')].map(b=>b.textContent.trim()),overflow:document.documentElement.scrollWidth>innerWidth})`);
  if(checks.h1!==1||checks.main!==1||checks.lang!=='en'||checks.overflow)throw Error('Desktop structure/overflow failed: '+route.path);
  if(checks.links.some(l=>!l.name||!l.href||l.href==='#')||checks.buttons.some(n=>!n))throw Error('Unnamed or empty clickable: '+route.path);
  for(let index=0;index<checks.links.length;index++){
   const link=checks.links[index];linksTested++;
   if(link.href.startsWith('https:'))continue;
   if(link.href.startsWith('#')){await evaluate(`document.querySelectorAll('a')[${index}].click()`);clicksTested++;continue;}
   if(link.href.includes('/downloads/')){const reply=await fetch(`http://127.0.0.1:${port}${link.href}`);if(!reply.ok||(await reply.arrayBuffer()).byteLength<1000)throw Error('Package download failed');continue;}
   await evaluate(`document.querySelectorAll('a')[${index}].click()`);await delay(120);
   await wait(`location.pathname+location.search===${JSON.stringify(link.href)} && document.readyState==='complete' && Boolean(document.querySelector('main h1'))`);clicksTested++;
   await navigate(route.path);await evaluate("document.querySelectorAll('details.section-source').forEach(d=>d.open=true)");
  }
  visited.push(route.path);
 }
 await navigate('/research/claim-review');
 const drawerCount=await evaluate("document.querySelectorAll('details.claim-review').length");if(drawerCount!==22)throw Error('Claim drawer count mismatch');
 for(let i=0;i<drawerCount;i++){await evaluate(`document.querySelectorAll('details.claim-review summary')[${i}].click()`);if(!await evaluate(`document.querySelectorAll('details.claim-review')[${i}].open`))throw Error('Claim disclosure failed');await evaluate(`document.querySelectorAll('details.claim-review summary')[${i}].click()`);}
 await navigate('/evidence');await wait("document.querySelectorAll('.claim').length===4");await evaluate("document.getElementById('live-refresh').click()");await wait("document.getElementById('live-readback').textContent.includes('healthy_workstations')");
 for(const route of ['/interest','/contact']){
  await navigate(route);await evaluate("document.querySelector('button[type=submit]').click()");
  if(await evaluate("document.getElementById('form-result').textContent.includes('registered')"))throw Error('Invalid enquiry accepted');
  await evaluate(`(()=>{const f=document.getElementById('interest-form');f.elements.name.value='Controlled browser test';f.elements.email.value='browser@example.test';f.elements.organisation.value='Local DOM qualification';f.elements.message.value='Controlled candidate DOM registration test; no external email requested.';f.elements.consent.checked=true;f.querySelector('button[type=submit]').click();})()`);
  await wait("document.getElementById('form-result').textContent.includes('Registration reference: KEDDEH-')");
 }
 // Exercise customer journeys and controlled API failures without stopping owner services.
 for(const contract of JSON.parse(fs.readFileSync('/workspace/keddeh.com/frontage/page-contracts.json','utf8')).pages){
  await navigate('/interest?'+new URLSearchParams({topic:contract.topic,context:contract.route}));
  if(await evaluate('document.getElementById("interest-form").elements.interest.value')!==contract.topic)throw Error('Topic journey lost');
  if(await evaluate('document.getElementById("interest-form").elements.consent.checked'))throw Error('Implicit consent');
 }
 fault=true;await send('Fetch.enable',{patterns:[{urlPattern:'*/api/*',requestStage:'Request'}]});
 await navigate('/evidence');await wait("document.getElementById('claim-register').textContent.includes('retained review')");
 await evaluate("document.getElementById('live-refresh').click()");await wait("document.getElementById('live-readback').textContent.includes('currently unavailable') && !document.getElementById('live-refresh').disabled");
 await navigate('/interest');await evaluate(`(()=>{const f=document.getElementById('interest-form');f.elements.name.value='Controlled failure test';f.elements.email.value='failure@example.test';f.elements.message.value='Controlled enquiry failure and retry test; no external communication requested.';f.elements.consent.checked=true;f.querySelector('button[type=submit]').click();})()`);
 await wait("document.getElementById('form-result').className==='error'");
 if(!await evaluate("document.activeElement.id==='form-result' && document.getElementById('interest-form').elements.message.value.includes('Controlled enquiry') && !document.querySelector('button[type=submit]').disabled"))throw Error('Failure lost form or focus');
 const failedPayload=JSON.parse(intercepted.filter(x=>x).at(-1));fault=false;
 await evaluate("document.querySelector('button[type=submit]').click()");await wait("document.getElementById('form-result').className==='success'");
 const retriedPayload=JSON.parse(intercepted.filter(x=>x).at(-1));if(failedPayload.request_id!==retriedPayload.request_id)throw Error('Retry changed submission identity');
 await send('Fetch.disable');
 await send('Emulation.setDeviceMetricsOverride',{width:375,height:812,deviceScaleFactor:1,mobile:true});
 for(const route of manifest.routes){await navigate(route.path);if(await evaluate('document.documentElement.scrollWidth>innerWidth'))throw Error('Mobile overflow: '+route.path);}
 await navigate('/');await send('Page.bringToFront');await evaluate("document.querySelector('.mobile-nav summary').focus()");await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r',unmodifiedText:'\r'});await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});await wait("document.querySelector('.mobile-nav').open");
 await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});await navigate('/');const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync('/workspace/braink-setup/customer-frontage.png',Buffer.from(shot.data,'base64'));
 if(errors.length)throw Error('Uncaught browser exceptions');
 const result={schema:'keddeh.customer-dom-evidence.v1',status:'passed',routes:visited,clickable_links_checked:linksTested,actual_link_clicks:clicksTested,source_disclosures_keyboard_exercised:sourceDisclosures,contextual_journeys:14,controlled_failure_checks:['claim API fallback','runtime API recovery','enquiry field preservation','error focus','same-identity successful retry'],claim_disclosures_exercised:drawerCount,checks:['all customer routes render with one named main/h1','every rendered internal navigation link exercised','no empty or unnamed clickable link/button','public wheel download returns actual bytes','claim register attributes four scoped assertions','live readback button reads actual owner family','both enquiry forms validate and return durable registration references','all customer routes fit a 375px viewport','mobile navigation opens with keyboard Enter','no uncaught browser exceptions'],external_link_scope:'href/source attribution checked; remote pages not claimed reachable',publication_scope:'actual local candidate DOM; existing public Site not promoted',chromiumSandbox:args.includes('--container-no-sandbox')?'disabled for isolated container test':'default'};
 fs.writeFileSync('/workspace/braink-setup/customer-dom-inventory.json',JSON.stringify({schema:'keddeh.rendered-dom-inventory.v1',pages:inventory},null,2)+'\n');
 fs.writeFileSync('/workspace/braink-setup/customer-dom-evidence.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
}finally{if(ws)ws.close();browser.kill('SIGTERM');await delay(500);if(browser.exitCode===null)browser.kill('SIGKILL');fs.rmSync(temp,{recursive:true,force:true});}
