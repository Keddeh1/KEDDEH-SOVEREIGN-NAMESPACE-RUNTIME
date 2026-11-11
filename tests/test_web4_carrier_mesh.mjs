import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const sourceRoot = new URL('../src/keddeh_namespace/', import.meta.url);
const bridge = fs.readFileSync(new URL('web4_bridge.js', sourceRoot), 'utf8');
const panel = fs.readFileSync(new URL('web4_panel.js', sourceRoot), 'utf8');

function normalized(value) {
  return JSON.parse(JSON.stringify(value));
}

function terminalFixture(request = async () => ({scope: 'source-bound mesh discovery; no Field admission'})) {
  const calls = [], prints = [], ledger = [], originals = [];
  const window = {
    runCommand: async line => originals.push(line),
    KEDDEH_WEB4: {
      authenticate: () => true,
      request: async (path, body) => {
        calls.push(normalized({path, body}));
        return request(path, body);
      }
    }
  };
  vm.runInNewContext(bridge, {
    window,
    print: text => prints.push(text),
    addLedger: async (...args) => ledger.push(normalized(args))
  }, {filename: 'web4_bridge.js'});
  return {window, calls, prints, ledger, originals};
}

function panelFixture(request = async () => ({scope: 'read-only topology'})) {
  const buttons = [], calls = [], elements = [];
  const document = {
    body: {append: element => elements.push(element)},
    createElement: tag => {
      const element = {
        tag, style: {}, children: [],
        append(...children) {this.children.push(...children);}
      };
      elements.push(element);
      if (tag === 'button') buttons.push(element);
      return element;
    }
  };
  const window = {
    KEDDEH_WEB4: {
      authenticate: () => true,
      request: async (path, body) => {
        calls.push(normalized({path, body}));
        return request(path, body);
      }
    },
    addEventListener: () => {}
  };
  vm.runInNewContext(panel, {document, window}, {filename: 'web4_panel.js'});
  return {buttons, calls, document, elements};
}

test('terminal discovers only through the existing owner-authenticated estate tool', async () => {
  const f = terminalFixture();
  await f.window.runCommand('cloud mesh discover');
  assert.deepEqual(f.calls, [{
    path: '/api/web4/control',
    body: {action: 'estate', tool: 'mesh_discover', arguments: {}}
  }]);
  assert.equal(f.ledger[0][0], 'CLOUD_PROCESS_READBACK');
  assert.equal(f.ledger[0][1].command, 'mesh discover');
  assert.match(f.ledger[0][1].scope, /not Field admission/);
});

test('terminal reads existing mesh status without creating an array', async () => {
  const f = terminalFixture();
  await f.window.runCommand('cloud mesh status');
  assert.deepEqual(f.calls[0].body, {
    action: 'estate', tool: 'mesh_status', arguments: {}
  });
  assert.equal(f.ledger[0][1].command, 'mesh status');
});

test('invalid mesh commands never dispatch or report a completed readback', async () => {
  const f = terminalFixture();
  await f.window.runCommand('cloud mesh join field');
  assert.equal(f.calls.length, 0);
  assert.equal(f.ledger.length, 0);
  assert.match(f.prints.at(-1), /cloud mesh discover/);
});

test('non-cloud commands still invoke the preserved terminal', async () => {
  const f = terminalFixture();
  await f.window.runCommand('help');
  assert.deepEqual(f.originals, ['help']);
  assert.equal(f.calls.length, 0);
});

test('original HTML panel exposes discovery and status through the bounded control route', async () => {
  const f = panelFixture();
  const labels = f.buttons.map(b => b.textContent);
  assert(labels.includes('Discover mesh'));
  assert(labels.includes('Mesh status'));
  await f.buttons.find(b => b.textContent === 'Discover mesh').onclick();
  await f.buttons.find(b => b.textContent === 'Mesh status').onclick();
  assert.deepEqual(f.calls, [
    {path: '/api/web4/control', body: {action: 'estate', tool: 'mesh_discover', arguments: {}}},
    {path: '/api/web4/control', body: {action: 'estate', tool: 'mesh_status', arguments: {}}}
  ]);
  assert(f.buttons.every(b => b.disabled !== true));
});

test('panel preserves authentication and transport failure instead of inventing a mesh', async () => {
  const f = panelFixture(async () => {throw new Error('UNAUTHORIZED_EXISTING_OWNER_ROUTE');});
  const b = f.buttons.find(b => b.textContent === 'Discover mesh');
  await b.onclick();
  assert.equal(b.disabled, false);
  const output = f.elements.find(e => e.id === 'keddeh-web4-output');
  assert.equal(output.textContent, 'UNAUTHORIZED_EXISTING_OWNER_ROUTE');
});