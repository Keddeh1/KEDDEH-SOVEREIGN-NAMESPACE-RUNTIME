import {env} from 'cloudflare:workers';
import {mediaService} from '@/lib/media-service.mjs';
import {cloudAgentDispatch} from '@/lib/cloud-agent-controls';
export async function GET(request:Request){
 if(!env.BRAINK_CI_WEBSITE_TOKEN||request.headers.get('Authorization')!=='Bearer '+env.BRAINK_CI_WEBSITE_TOKEN)return Response.json({error:'UNAUTHORIZED'},{status:401});
 return mediaService(request,env,args=>cloudAgentDispatch(args,{source:'AUTHENTICATED_WEBSITE',scope:'OWNER_MEDIA',actor:'owner-media'}));
}
export const POST=GET;export const PUT=GET;export const HEAD=GET;
