/* Adds measured backend controls without replacing the owner's carrier UI. */
(() => {
  const panel = document.createElement('details');
  panel.id = 'keddeh-web4-panel';
  panel.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:2147483000;background:#101c2e;color:#e6edf6;border:1px solid #5284a5;border-radius:8px;padding:12px;max-width:480px;font:13px monospace';
  const title = document.createElement('summary'); title.textContent = 'Cloud runtime'; panel.append(title);
  const controls = document.createElement('div'); controls.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap;margin-top:12px'; panel.append(controls);
  const output = document.createElement('pre');output.id='keddeh-web4-output';output.setAttribute('role','status');output.setAttribute('aria-live','polite');output.style.cssText='white-space:pre-wrap;overflow:auto;max-height:240px';output.textContent='Connect to read live cloud processes.';
  function button(label, task) {const element=document.createElement('button');element.textContent=label;element.style.cssText='padding:6px;color:#eef;background:#243b56;border:1px solid #658ca8;border-radius:4px';element.onclick=async()=>{element.disabled=true;try{const result=await task();if(result!==undefined)output.textContent=JSON.stringify(result,null,2);}catch(error){output.textContent=error.message;}finally{element.disabled=false;}};controls.append(element);}
  button('Connect',()=>({connected:window.KEDDEH_WEB4.authenticate(),scope:'local cloud workspace'}));
  button('Live status',()=>window.KEDDEH_WEB4.request('/api/web4/status'));
  button('Receipt',()=>window.KEDDEH_WEB4.request('/api/web4/generation'));
  button('Boot host',()=>window.KEDDEH_WEB4.request('/api/web4/control',{action:'boot'}));
  button('VFS subscription',()=>window.KEDDEH_WEB4.request('/api/web4/control',{action:'vfs'}));
  button('Domain mesh',()=>window.KEDDEH_WEB4.request('/api/web4/control',{action:'domains'}));
  button('KEDDEH console',()=>window.KEDDEH_WEB4.request('/api/web4/control',{action:'hci'}));
  button('Bilateral status',()=>window.KEDDEH_WEB4.request('/api/web4/control',{action:'bilateral'}));
  button('Run bilateral',()=>window.KEDDEH_WEB4.request('/api/web4/control',{action:'bilateral',enabled:true}));
  button('Pause bilateral',()=>window.KEDDEH_WEB4.request('/api/web4/control',{action:'bilateral',enabled:false}));
  button('Observer',()=>window.KEDDEH_WEB4.request('/api/web4/control',{action:'observer'}));
  button('Diagnostics',()=>window.KEDDEH_WEB4.request('/api/web4/control',{action:'workbook'}));
  button('Propagate',()=>window.KEDDEH_WEB4.request('/api/web4/control',{action:'propagate',adjacency:[[0,1],[0,0]],initial:[1,0],steps:100}));
  button('Actuate registers',()=>window.KEDDEH_WEB4.request('/api/web4/control',{action:'propagate',adjacency:[[0,1],[0,0]],initial:[1,0],steps:100,actuate:true}));
  panel.append(output);document.body.append(panel);
  window.addEventListener('keddeh:web4-readback',event=>{output.textContent=JSON.stringify(event.detail,null,2);});
})();
