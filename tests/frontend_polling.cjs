const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../navixav/web/static/app.js'), 'utf8').replaceAll('\r\n', '\n');
function functionSource(name) {
  const start = source.indexOf(`async function ${name}()`);
  return source.slice(start, source.indexOf('\n}\n', start) + 2);
}
function setup() {
  const timers = new Map();
  let nextTimer = 0;
  const badge = {};
  const state = { traffic: [], writes: 0, requests: [], visible: true, hidden: false, resized: 0 };
  const context = vm.createContext({
    AbortController, URLSearchParams, console,
    currentChart: {}, currentPlan: {},
    setLiveState() {}, updateProcedures() {}, pollTaxiGuidance() {},
    applyAircraftState(aircraft) { state.aircraft = aircraft; },
    setTimeout(fn) { timers.set(++nextTimer, fn); return nextTimer; },
    clearTimeout(id) { timers.delete(id); },
    latestStatus: { traffic_enabled: true },
    document: { get hidden() { return state.hidden; } },
    $: id => id.startsWith('panel-') ? { getClientRects: () => state.visible ? [{}] : [] } : badge,
    t: key => key, show: (el, visible) => { el.visible = visible; },
    GROUND: {
      resize() { state.resized++; },
      setTraffic(list) { state.traffic = list; state.writes++; },
      clearTraffic() { state.traffic = []; state.writes++; },
    },
    MAP: { resize() { state.resized++; }, setTraffic(list) { state.traffic = list; state.writes++; } },
    fetch(url, options) {
      return new Promise((resolve, reject) => {
        state.requests.push({ resolve, reject, url });
        options.signal.addEventListener('abort', () => reject(new Error('aborted')));
      });
    },
  });
  vm.runInContext(source.slice(0, source.indexOf('const $ ='))
    + functionSource('refreshGroundTraffic') + '\n' + functionSource('refreshTraffic')
    + '\n' + functionSource('pollLive'), context);
  const run = code => vm.runInContext(code, context);
  const reply = (traffic, enabled = true) => state.requests.at(-1).resolve({
    ok: true, json: async () => ({ enabled, available: true, traffic }),
  });
  return { run, state, timers, badge, reply };
}

test('a slow traffic request does not overlap, and polling resumes after completion', async () => {
  const h = setup();
  const first = h.run('refreshTraffic()');
  await h.run('refreshTraffic()');
  assert.equal(h.state.requests.length, 1);
  h.reply([{ object_id: 1 }]);
  await first;
  const second = h.run('refreshTraffic()');
  assert.equal(h.state.requests.length, 2);
  h.reply([]);
  await second;
});

test('a response from a previous traffic selection cannot repopulate the view', async () => {
  const h = setup();
  const request = h.run('refreshGroundTraffic()');
  h.run('trafficGeneration++; resetGroundTraffic()');
  const writes = h.state.writes;
  h.reply([{ object_id: 1 }]);
  await request;
  assert.equal(h.state.writes, writes);
});

test('temporary errors retain positions without refreshing their expiry; success recovers', async () => {
  const h = setup();
  let request = h.run('refreshGroundTraffic()');
  h.reply([{ object_id: 1 }]);
  await request;
  const expiry = [...h.timers.values()][0];
  request = h.run('refreshGroundTraffic()');
  h.state.requests.at(-1).resolve({ ok: false, status: 503 });
  await request;
  assert.equal(h.state.traffic.length, 1);
  assert.equal(h.badge.textContent, 'taxi_traffic_held');
  assert.equal([...h.timers.values()][0], expiry);
  expiry();
  assert.equal(h.state.traffic.length, 0);
  assert.equal(h.badge.textContent, 'taxi_traffic_expired');
  request = h.run('refreshGroundTraffic()');
  h.reply([{ object_id: 2 }]);
  await request;
  assert.equal(h.badge.visible, false);
  assert.equal(h.state.traffic[0].object_id, 2);
});

test('a confirmed empty or disabled response clears immediately', async () => {
  for (const enabled of [true, false]) {
    const h = setup();
    let request = h.run('refreshGroundTraffic()');
    h.reply([{ object_id: 1 }]);
    await request;
    request = h.run('refreshGroundTraffic()');
    h.reply([], enabled);
    await request;
    assert.equal(h.state.traffic.length, 0);
    assert.equal(h.badge.visible, false);
  }
});

test('a timed out request releases its slot for the next refresh', async () => {
  const h = setup();
  let request = h.run('refreshGroundTraffic()');
  [...h.timers.values()][0]();
  await request;
  assert.equal(h.badge.textContent, 'taxi_traffic_expired');
  request = h.run('refreshGroundTraffic()');
  assert.equal(h.state.requests.length, 2);
  h.reply([]);
  await request;
});

test('live position reads serialize and discard a response for the previous chart', async () => {
  const h = setup();
  const request = h.run('pollLive()');
  await h.run('pollLive()');
  assert.equal(h.state.requests.length, 1);
  h.run('currentChart = {}');
  h.state.requests[0].resolve({ ok: true, json: async () => ({ connected: true, aircraft: { latitude: 48 } }) });
  await request;
  assert.equal(h.state.aircraft, undefined);
  const next = h.run('pollLive()');
  h.state.requests[1].resolve({ ok: true, json: async () => ({ connected: true, aircraft: { latitude: 49 } }) });
  await next;
  assert.equal(h.state.aircraft.latitude, 49);
});

test('hidden views perform no traffic reads; becoming visible resumes both views', async () => {
  const h = setup();
  h.state.visible = false;
  await h.run('refreshTraffic()');
  await h.run('refreshGroundTraffic()');
  assert.equal(h.state.requests.length, 0);
  h.state.visible = true;
  h.state.hidden = true;
  await h.run('refreshTraffic()');
  await h.run('refreshGroundTraffic()');
  assert.equal(h.state.requests.length, 0);
  h.state.hidden = false;
  h.run('refreshVisibleTraffic()');
  assert.equal(h.state.requests.length, 2);
  assert.equal(h.state.resized, 2);
  for (const request of h.state.requests) {
    request.resolve({ ok: true, json: async () => ({ enabled: true, available: true, traffic: [] }) });
  }
  await new Promise(resolve => setImmediate(resolve));
});

test('a traffic response arriving after the view is hidden cannot redraw it', async () => {
  const h = setup();
  const request = h.run('refreshGroundTraffic()');
  h.state.visible = false;
  h.reply([{ object_id: 1 }]);
  await request;
  assert.equal(h.state.writes, 0);
});
