// Recursive dual-homed domain transport for the supplied KEX workstation.
import http from 'node:http';
import fs from 'node:fs';
import {spawn} from 'node:child_process';
const token=fs.readFileSync('/state/token','utf8').trim();
const config=()=>JSON.parse(fs.readFileSync('/state/config.json','utf8'));
const persist='/state/phase.json';
let state=fs.existsSync(persist)?JSON.parse(fs.readFileSync(persist,'utf8')):{domain:config().domain,epoch:0,theta:[0,0,0],omega:[.297,.297,.297],elapsed:0,children:{},mode:'FLYWHEEL',anchor:null};
function save(){const file=persist+'.new';const fd=fs.openSync(file,'w',0o600);fs.writeFileSync(fd,JSON.stringify(state));fs.fsyncSync(fd);fs.closeSync(fd);fs.renameSync(file,persist);const dir=fs.openSync('/state','r');fs.fsyncSync(dir);fs.closeSync(dir);}
let stopping=false;
const owners=[19100,19101,19102].map(port=>{const child=spawn(process.execPath,['--max-old-space-size=32','/code/owner.mjs'],{env:{...process.env,PORT:String(port)},stdio:'ignore'});child.on('exit',()=>{if(!stopping)process.exit(1);});return child;});
let parentPhase=null;let reanchor=state.elapsed;
function step(){ // Deterministic deployment of the owner's wrapped Kuramoto equations.
 const dt=.01,old=state.theta.slice(),kv=parentPhase===null?0:.4*(1-Math.exp(-Math.max(0,state.elapsed-reanchor)/2));
 for(let i=0;i<3;i++){let sum=0;for(let j=0;j<3;j++)if(i!==j)sum+=Math.sin(old[j]-old[i]);
  state.theta[i]=(old[i]+(state.omega[i]+.2*sum/2+kv*Math.sin((parentPhase??old[i])-old[i]))*dt)%(2*Math.PI);
  state.omega[i]+=-.5*(state.omega[i]-.297)*dt;}
 state.elapsed+=dt;
}
const headers={Authorization:'Bearer '+token,'Content-Type':'application/json'};
let busy=false;
async function tick(){if(busy)return;busy=true;try{
 const workstations=await Promise.all([19100,19101,19102].map(port=>fetch(`http://127.0.0.1:${port}/api/telemetry`,{signal:AbortSignal.timeout(1000)}).then(r=>r.json())));const telemetry=workstations[0];state.workstation=telemetry;state.workstations=workstations;
 const cfg=config();
 if(cfg.upstream){try{const res=await fetch(cfg.upstream+'/bridge',{method:'POST',headers,body:JSON.stringify({domain:state.domain,epoch:state.epoch,theta:state.theta,omega:state.omega,workstation:telemetry}),signal:AbortSignal.timeout(1200)});if(!res.ok)throw Error('bridge rejected');const parent=await res.json();if(parentPhase===null)reanchor=state.elapsed;parentPhase=parent.phase;state.anchor={domain:parent.domain,epoch:parent.epoch};state.mode='SOFT_PHASE_CAPTURE';}catch{parentPhase=null;state.mode='FLYWHEEL';state.anchor=null;}}
 else{parentPhase=null;state.mode='GENESIS';}
 for(let n=0;n<100;n++)step();state.epoch++;state.phase=Math.atan2(state.theta.reduce((s,v)=>s+Math.sin(v),0),state.theta.reduce((s,v)=>s+Math.cos(v),0));save();
 }catch{state.mode='WORKSTATION_UNAVAILABLE';save();}finally{busy=false;}}
const server=http.createServer(async(req,res)=>{
 const send=(status,data)=>{res.writeHead(status,{'Content-Type':'application/json'});res.end(JSON.stringify(data));};
 if(req.headers.authorization!==headers.Authorization)return send(401,{error:'unauthorized'});
 if(req.method==='GET'&&req.url==='/state')return send(200,{...state,networkNamespace:fs.readlinkSync('/proc/self/ns/net'),ownerAlive:owners.every(p=>p.exitCode===null),ownerPids:owners.map(p=>p.pid)});
 if(req.method==='POST'&&req.url==='/bridge'){
  let raw='';try{for await(const chunk of req){raw+=chunk;if(raw.length>32768)throw Error('oversize');}const child=JSON.parse(raw);if(typeof child.domain!=='string'||!/^domain-[0-7]$/.test(child.domain)||!Number.isSafeInteger(child.epoch))throw Error('invalid child');state.children[child.domain]=child;save();return send(200,{domain:state.domain,epoch:state.epoch,phase:state.phase??0});}catch{return send(400,{error:'invalid bridge payload'});}}
 send(404,{error:'not_found'});
});
server.listen(19000,'0.0.0.0');const timer=setInterval(tick,1000);tick();
function stop(){stopping=true;clearInterval(timer);for(const child of owners)child.kill('SIGTERM');server.close(()=>process.exit(0));setTimeout(()=>process.exit(0),1500).unref();}
process.on('SIGTERM',stop);process.on('SIGINT',stop);
