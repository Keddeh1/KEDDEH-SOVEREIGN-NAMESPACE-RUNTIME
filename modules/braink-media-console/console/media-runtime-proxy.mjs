const endpoint='https://keddeh-systems-runtime.aboudy65097.chatgpt.site/api/media/website';
export async function mediaProxy(request,env,fetcher=fetch){
 const url=new URL(request.url);if(!url.pathname.startsWith('/api/media'))return null;
 const user=request.headers.get('oai-authenticated-user-id'),email=request.headers.get('oai-authenticated-user-email');
 if(!user||!email)return Response.json({error:'Sign in with your owner account to use the media library.'},{status:401});
 if(!env.BRAINK_OWNER_EMAIL||email.trim().toLowerCase()!==env.BRAINK_OWNER_EMAIL.trim().toLowerCase())return Response.json({error:'This media workspace is restricted to its owner.'},{status:403});
 if(request.method!=='GET'&&request.method!=='HEAD'){
  const origin=request.headers.get('Origin');if(request.headers.get('Sec-Fetch-Site')==='cross-site'||origin&&origin!==url.origin)return Response.json({error:'Cross-origin writes are not permitted.'},{status:403});
 }
 if(!env.BRAINK_CI_WEBSITE_TOKEN)return Response.json({error:'The BRAINK media connection is not configured.'},{status:503});
 try{const target=new URL(endpoint);target.searchParams.set('route',url.pathname.replace('/api/media','')||'/');for(const [k,v]of url.searchParams)if(k!=='route')target.searchParams.append(k,v);
 const headers=new Headers({'Authorization':'Bearer '+env.BRAINK_CI_WEBSITE_TOKEN,'X-Media-Actor':user});for(const k of ['content-type','content-length','range','x-upload-name'])if(request.headers.has(k))headers.set(k,request.headers.get(k));
 const response=await fetcher(target,{method:request.method,headers,body:['GET','HEAD'].includes(request.method)?undefined:request.body,redirect:'manual',signal:AbortSignal.timeout(120000)});
 const output=new Headers(response.headers);output.set('Cache-Control','private,no-store');return new Response(response.body,{status:response.status,headers:output});
 }catch(error){console.error('BRAINK_MEDIA_TRANSPORT',error?.name);return Response.json({error:'BRAINK could not be reached. Your local editing selection is preserved; retry when the connection returns.'},{status:503});}
}
