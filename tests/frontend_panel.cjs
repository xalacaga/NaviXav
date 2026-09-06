const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname,
  '../navixav/msfs_panel/navixav-toolbar/html_ui/InGamePanels/NaviXavPanel/NaviXavPanel.js'), 'utf8');
function setup() {
  let Panel;
  const nodes = new Map();
  const node = () => ({ textContent: '', children: [],
    setAttribute(key, value) { this[key] = value; },
    appendChild(child) { this.children.push(child); } });
  const get = id => { if (!nodes.has(id)) nodes.set(id, node()); return nodes.get(id); };
  const context = vm.createContext({ UIElement: class {},
    window: { customElements: { define(name, type) { Panel = type; } } },
    document: { getElementById: get, createElement: node }, checkAutoload() {},
    navixavInjection: get('injection'), navixavDot: get('dot'),
  });
  vm.runInContext(source, context);
  return { panel: new Panel(), get };
}
test('the panel only lights green for confirmed active injection', () => {
  const h = setup();
  for (const state of ['loading', 'empty', 'error', 'stale']) {
    h.panel.showInjection({ traffic_enabled: true, injection_active: true,
      injection: { state, confirmed: 2, selected: 3, skipped: 1 } });
    assert.ok(!h.get('dot').class.includes('navixavDotLive'));
    assert.match(h.get('navixavInjectionDetail').textContent, /2/);
  }
  h.panel.showInjection({ traffic_enabled: true, injection: { state: 'active', confirmed: 2 } });
  assert.ok(h.get('dot').class.includes('navixavDotLive'));
  h.panel.showInjection({ traffic_enabled: true, injection_active: true });
  assert.ok(!h.get('dot').class.includes('navixavDotLive'));
});
test('an exhausted OpenSky quota is named and explained', () => {
  const h = setup();
  h.panel.showInjection({ traffic_enabled: true, injection: {
    state: 'error', error_code: 'opensky_daily_quota', confirmed: 0,
  }, flight: { labels: {
    traffic_state_opensky_quota: 'OpenSky daily quota exhausted',
    traffic_state_opensky_quota_detail: 'NaviXav waits automatically.',
  } } });
  assert.equal(h.get('injection').textContent, 'OpenSky daily quota exhausted');
  assert.equal(h.get('navixavInjectionDetail').textContent, 'NaviXav waits automatically.');
  assert.ok(!h.get('dot').class.includes('navixavDotLive'));
});
test('a stale flight hides values instead of presenting them as current', () => {
  const h = setup();
  h.panel.showFlight({ flight: { fresh: false, connected: false,
    values: { 'flight-next-fix': 'LGL' } } });
  assert.ok(h.get('navixavFlightNotice').textContent.length > 0);
  assert.equal(h.get('navixavFlightValues').children[0].children[1].textContent, '— · —');
});
test('flight values and translated labels come from the desktop snapshot', () => {
  const h = setup();
  h.panel.showFlight({ flight: { fresh: true, connected: true, route: 'LFPG → EHAM',
    labels: { panel_my_flight: 'Mein Flug', flight_next_fix: 'Nächster Wegpunkt' },
    values: { 'flight-next-fix': 'LGL', 'flight-next-distance': '12.3 NM' } } });
  assert.equal(h.get('navixavFlightTitle').textContent, 'Mein Flug');
  assert.equal(h.get('navixavFlightValues').children[0].children[1].textContent, 'LGL · 12.3 NM');
  assert.equal(h.get('navixavFlightNotice').textContent, '');
});
