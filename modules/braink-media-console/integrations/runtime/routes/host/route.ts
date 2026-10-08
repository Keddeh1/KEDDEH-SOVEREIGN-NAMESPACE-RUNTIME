import {env} from 'cloudflare:workers';
import {mediaService} from '@/lib/media-service.mjs';
import {cloudAgentDispatch} from '@/lib/cloud-agent-controls';
export async function GET(request:Request){
 if(!env.BRAINK_MEDIA_AGENT_TOKEN||request.headers.get('Authorization')!=='Bearer '+env.BRAINK_MEDIA_AGENT_TOKEN)return Response.json({error:'UNAUTHORIZED'},{status:401});
 return mediaService(request,env,args=>cloudAgentDispatch(args,{source:'BRAINK_MEDIA_HOST',scope:'OWNER_MEDIA',actor:'owner-media'}));
}
export const POST=GET;export const PUT=GET;export const HEAD=GET;
