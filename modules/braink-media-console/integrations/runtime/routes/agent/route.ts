import {env} from 'cloudflare:workers';
import {mediaTick,mediaVerify} from '@/lib/media-service.mjs';
import {cloudAgentDispatch} from '@/lib/cloud-agent-controls';
export async function POST(request:Request){
 if(!env.BRAINK_MEDIA_AGENT_TOKEN||request.headers.get('Authorization')!=='Bearer '+env.BRAINK_MEDIA_AGENT_TOKEN)return Response.json({error:'UNAUTHORIZED'},{status:401});
 const input=await request.json().catch(()=>({}));
 if(input.op==='verify')return mediaVerify(env,args=>cloudAgentDispatch(args,{source:'BRAINK_MEDIA_AGENT',scope:'OWNER_MEDIA',actor:'owner-media'}));
 return Response.json(await mediaTick(env,args=>cloudAgentDispatch(args,{source:'BRAINK_MEDIA_AGENT',scope:'OWNER_MEDIA',actor:'owner-media'})));
}
