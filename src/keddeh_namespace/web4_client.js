/* Shared, memory-only owner session for preserved WEB4 carriers. */
(() => {
  let token = '';
  window.KEDDEH_WEB4 = Object.freeze({
    authenticate() {
      token = window.prompt('Enter the local runtime token from the private state/token file') || '';
      return Boolean(token);
    },
    clearSession() { token = ''; },
    async service(operation, name) {
      const host=await this.request('/api/web4/control',{action:'host',operation:'status'});
      if(operation==='status')return name ? host.services.find(row=>row.name===name) : host;
      const service=host.services.find(row=>row.name===name);
      if(!service)throw new Error('Unknown owned runtime service');
      const response=await this.request('/api/web4/control',{action:'estate',tool:'host_actuator',arguments:{operation,name,
        host_id:host.host_id,instance_id:host.instance_id,source_digest:host.source_digest,
        request_id:crypto.randomUUID(),expected_generation:service.generation,expected_pid:service.pid,
        pipeline_generation:host.pipeline_generation}});
      return response.structuredContent;
    },
    async request(path, body) {
      if (!['/api/web4/status', '/api/web4/control', '/api/web4/generation'].includes(path)) throw new Error('Unsupported cloud route');
      if (body && !['pipeline','projection','agreement'].includes(body.action)) {
        const gate = await this.request('/api/web4/control', {action:'pipeline'});
        body = {...body, pipeline_generation:body.pipeline_generation ?? gate.generation, projection_context:{space:'owner',agreement_version:'1.0'}};
      }
      const response = await fetch(path, {
        method: body ? 'POST' : 'GET',
        headers: {'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json'},
        body: body ? JSON.stringify(body) : undefined,
        signal: AbortSignal.timeout(60000)
      });
      const value = await response.json();
      if (!response.ok) throw new Error(value.error || `HTTP ${response.status}`);
      window.dispatchEvent(new CustomEvent('keddeh:web4-readback', {detail:value}));
      return value;
    }
  });
})();
