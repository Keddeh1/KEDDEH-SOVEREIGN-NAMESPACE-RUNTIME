/* Existing memory-only owner session; no credential is copied into HTML payloads. */
(() => {
  let token = '';
  const admitted = path => (
    ['/api/web4/status', '/api/web4/control', '/api/web4/generation',
     '/api/ai-py/binding/status', '/api/ai-py/execute'].includes(path) ||
    /^\/api\/ai-py\/receipts\/[A-Za-z0-9][A-Za-z0-9_-]{7,79}$/.test(path)
  );
  async function request(path, body) {
    if (!admitted(path)) throw new Error('Unsupported owner route');
    const response = await fetch(path, {
      method: body === undefined ? 'GET' : 'POST',
      headers: {'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json'},
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const value = await response.json();
    if (!response.ok) throw new Error(value.error || `HTTP ${response.status}`);
    window.dispatchEvent(new CustomEvent('keddeh:web4-readback', {detail:value}));
    return value;
  }
  window.KEDDEH_WEB4 = Object.freeze({
    authenticate() {
      token = window.prompt('Enter the local runtime token from the private state/token file') || '';
      return Boolean(token);
    },
    request,
    aiPy: Object.freeze({
      status() {return request('/api/ai-py/binding/status');},
      execute(envelope) {return request('/api/ai-py/execute', envelope);},
      receipt(requestId) {
        if (!/^[A-Za-z0-9][A-Za-z0-9_-]{7,79}$/.test(requestId)) throw new Error('Invalid AI.PY receipt ID');
        return request('/api/ai-py/receipts/' + requestId);
      }
    })
  });
})();
