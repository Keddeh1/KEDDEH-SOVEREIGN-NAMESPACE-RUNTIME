import {McpServer} from '@modelcontextprotocol/sdk/server/mcp.js';
import {StdioServerTransport} from '@modelcontextprotocol/sdk/server/stdio.js';
import {z} from 'zod';import {BrainkMediaClient} from '../sdk/index.mjs';
const client=new BrainkMediaClient({endpoint:process.env.BRAINK_MEDIA_ENDPOINT||'https://keddeh-systems-runtime.aboudy65097.chatgpt.site/api/media/host',token:process.env.BRAINK_MEDIA_AGENT_TOKEN});
const server=new McpServer({name:'braink-media-console',version:'0.1.0'});
const result=v=>({content:[{type:'text',text:JSON.stringify(v)}]});
function tool(name,description,schema,handler){server.tool(name,description,schema,async args=>{try{return result(await handler(args));}catch(error){return {...result({state:'failed',error:error.message}),isError:true};}});}
tool('media_status','Observe storage/account configuration; no invented provider activity.',{},()=>client.status());
tool('media_library','Read saved originals, revisions, derived outputs and job observations.',{},()=>client.library());
tool('media_scripts','Read saved narration and on-screen scripts.',{},()=>client.scripts());
tool('media_save_script','Save a script for review; does not claim generated speech or publication.',{title:z.string().min(1).max(100),assetId:z.string().uuid().optional(),narration:z.string().max(40000),onScreen:z.string().max(10000).optional(),notes:z.string().max(10000).optional()},v=>client.saveScript(v));
tool('media_queue_processing','Queue native FFmpeg processing under existing BRAINK governance. Completion requires stored output observations.',{assetId:z.string().uuid().optional(),profiles:z.array(z.enum(['shorts','long','podcast','voiceover','animate'])).min(1),title:z.string().max(100).optional(),voiceScript:z.string().max(20000).optional(),transcribe:z.boolean().default(false),autoQueueYouTube:z.boolean().default(false),rightsConfirmed:z.literal(true)},v=>client.queueProcessing(v));
tool('media_cancel_job','Cancel only an unclaimed queued job.',{id:z.string().uuid()},v=>client.cancelJob(v.id));
// Public posting is intentionally absent from this MCP surface: use the owner release review.
await server.connect(new StdioServerTransport());
