import {readFile} from 'node:fs/promises';
export class BrainkMediaClient {
 constructor({endpoint,token,fetcher=fetch,timeoutMs=120000}) {const u=new URL(endpoint);if(u.protocol!=='https:'&&!['localhost','127.0.0.1'].includes(u.hostname))throw Error('HTTPS required');if(!token)throw Error('Owner-scoped credential required');this.endpoint=u;this.token=token;this.fetcher=fetcher;this.timeoutMs=timeoutMs;}
 async request(route,{method='GET',body,headers={}}={}){const u=new URL(this.endpoint);const [path,query]=route.split('?');u.searchParams.set('route',path);for(const [k,v]of new URLSearchParams(query))u.searchParams.set(k,v);const response=await this.fetcher(u,{method,headers:{Authorization:'Bearer '+this.token,...headers},body,redirect:'error',signal:AbortSignal.timeout(this.timeoutMs)});if(!response.ok){let error;try{error=(await response.json()).error;}catch{}throw Error(error||`BRAINK returned HTTP ${response.status}`);}return response;}
 async get(route){return (await this.request(route)).json();}
 async post(route,value){return (await this.request(route,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value)})).json();}
 status(){return this.get('/status');} library(){return this.get('/library');} scripts(){return this.get('/scripts');}
 saveScript(value){return this.post('/scripts',value);} saveEdit(value){return this.post('/edits',value);}
 queueProcessing(value){return this.post('/processing/queue',value);} queueYouTube(value){return this.post('/jobs',value);}
 runYouTubeQueue(){return this.post('/agent/run',{});} cancelJob(id){return this.post('/jobs/cancel',{id});}
 async uploadBytes(bytes,{name,mime,kind}){if(!bytes.byteLength)throw Error('Empty source');const session=await this.post('/upload/start',{name,mime,kind,bytes:bytes.byteLength});for(let offset=0,part=1;offset<bytes.byteLength;offset+=session.chunkSize,part++)await this.request(`/upload/part?id=${encodeURIComponent(session.id)}&part=${part}`,{method:'PUT',headers:{'Content-Type':'application/octet-stream'},body:bytes.subarray(offset,offset+session.chunkSize)});return this.post('/upload/complete',{id:session.id});}
 async uploadFile(path,metadata){return this.uploadBytes(await readFile(path),metadata);}
}
