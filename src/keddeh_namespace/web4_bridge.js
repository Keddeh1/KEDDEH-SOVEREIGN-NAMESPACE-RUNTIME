/* Bridges the preserved KEX terminal to actual local cloud processes. */
(() => {
  const original = window.runCommand;
  const request = (path, body) => window.KEDDEH_WEB4.request(path, body);
  window.runCommand = async function(line) {
    const parts = line.trim().split(/\s+/);
    if (parts[0] !== 'cloud') return original(line);
    try {
      let result;
      switch (parts[1]) {
        case 'auth': window.KEDDEH_WEB4.authenticate(); print('Cloud credential held in this tab memory only.'); return;
        case 'status': result = await request('/api/web4/status'); break;
        case 'mesh':
          if (parts.length !== 3 || !['discover','status'].includes(parts[2])) {
            print('cloud mesh discover | cloud mesh status'); return;
          }
          result = await request('/api/web4/control', {
            action:'estate',tool:parts[2] === 'discover' ? 'mesh_discover' : 'mesh_status',arguments:{}
          });
          break;
        case 'boot': case 'observer': case 'workbook': result = await request('/api/web4/control', {action:parts[1]}); break;
        case 'restart': result = await request('/api/web4/control', {action:'restart',name:parts[2]}); break;
        case 'commit': result = await request('/api/web4/control', {action:'commit',node_id:Number(parts[2]),nonce:Number(parts[3]),tenant_id:parts[4]}); break;
        case 'enact': case 'propagate': result = await request('/api/web4/control',{action:'propagate',actuate:parts[1]==='enact',adjacency:[[0,1],[0,0]],initial:[1,0],steps:100}); break;
        default: print('cloud auth | status | mesh discover | mesh status | boot | observer | workbook | restart node-PORT | commit NODE NONCE TENANT | propagate | enact'); return;
      }
      print(JSON.stringify(result, null, 2));
      await addLedger('CLOUD_PROCESS_READBACK', {command:parts[1]==='mesh'?`mesh ${parts[2]}`:parts[1],scope:'backend HTTP observation; mesh calls are read-only estate discovery, not Field admission'});
    } catch (error) {print(`cloud error: ${error.message}`);}
  };
  print('WEB4 cloud process bridge loaded. Type cloud auth, then cloud status.');
})();
