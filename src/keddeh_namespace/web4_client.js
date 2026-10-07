/* Shared, memory-only owner session for preserved WEB4 carriers. */
(() => {
  let token = '';
  window.KEDDEH_WEB4 = Object.freeze({
    authenticate() {
      token = window.prompt('Enter the local runtime token from the private state/token file') || '';
      return Boolean(token);
    },
    async request(path, body) {
      if (!['/api/web4/status', '/api/web4/control', '/api/web4/generation'].includes(path)) throw new Error('Unsupported cloud route');
      const response = await fetch(path, {
        method: body ? 'POST' : 'GET',
        headers: {'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json'},
        body: body ? JSON.stringify(body) : undefined
      });
      const value = await response.json();
      if (!response.ok) throw new Error(value.error || `HTTP ${response.status}`);
      window.dispatchEvent(new CustomEvent('keddeh:web4-readback', {detail:value}));
      return value;
    }
  });
})();
