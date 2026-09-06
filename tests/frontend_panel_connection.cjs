const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname,
  '../navixav/msfs_panel/navixav-toolbar/html_ui/InGamePanels/NaviXavPanel/NaviXavPanel.js'), 'utf8');
const flush = () => new Promise(resolve => setImmediate(resolve));
function setup() {
  let Panel;
  const requests = [], timers = new Map(), nodes = new Map();
  const get = id => {
    if (!nodes.has(id)) nodes.set(id, { listeners: [], setAttribute() {}, addEventListener(_, f) { this.listeners.push(f); } });
    return nodes.get(id);
  };
  class XHR {
    open(method, url) { this.url = url; }
    send() { requests.push(this); }
    respond(payload, status = 200) { this.status = status; this.responseText = JSON.stringify(payload); this.onload(); }
  }
  vm.runInNewContext(source, {
    UIElement: class { connectedCallback() {} disconnectedCallback() {} },
    XMLHttpRequest: XHR, console,
    window: { customElements: { define(_, value) { Panel = value; } } },
    document: { getElementById: get },
    setInterval(fn) { const id = {}; timers.set(id, fn); return id; },
    clearInterval(id) { timers.delete(id); },
    navixavControls: get('controls'), navixavOffline: get('offline'), checkAutoload() {},
  });
  const panel = new Panel();
  panel.showControls = state => { panel.state = state; };
  panel.connectedCallback();
  return { panel, requests, timers, get };
}

test('an unavailable service is retried without reopening the panel', async () => {
  const h = setup();
  for (let i = 0; i < 11; i++) { h.requests[i].onerror(); await flush(); }
  assert.equal(h.panel.base, '');
  assert.equal(h.timers.size, 1);
  [...h.timers.values()][0]();
  h.requests[11].respond({ running: true });
  await flush();
  assert.equal(h.panel.base, 'http://127.0.0.1:8765');
});

test('timeout releases polling and discovery follows a changed port', async () => {
  const h = setup();
  h.requests[0].respond({ running: true }); await flush();
  h.panel.refresh(); h.panel.refresh();
  assert.equal(h.requests.length, 2);
  h.requests[1].ontimeout(); await flush();
  h.panel.refresh();
  h.requests[2].onerror(); await flush();
  h.requests[3].respond({ running: true }); await flush();
  assert.equal(h.panel.base, 'http://127.0.0.1:8766');
});

test('old discovery responses cannot revive a closed or reopened panel', async () => {
  const h = setup();
  h.panel.disconnectedCallback(); h.panel.connectedCallback();
  h.requests[0].respond({ running: true, version: 'old' }); await flush();
  assert.equal(h.panel.base, '');
  h.requests[1].respond({ running: true, version: 'new' }); await flush();
  assert.equal(h.panel.state.version, 'new');
  assert.equal(h.get('trafficToggle').listeners.length, 1);
});

test('an unrelated HTTP service is skipped and display errors do not disconnect', async () => {
  const h = setup();
  h.requests[0].respond({ healthy: true }); await flush();
  h.panel.showControls = () => { throw new Error('display failure'); };
  h.requests[1].respond({ running: true }); await flush();
  assert.equal(h.panel.base, 'http://127.0.0.1:8766');
  assert.equal(h.timers.size, 1);
});
