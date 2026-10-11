const {test}=require('node:test');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../navixav/web/static/app.js'),'utf8').replaceAll('\r\n','\n');

function setup({remote = false, server = [], legacy = null} = {}) {
  const storage = new Map();
  if (legacy) storage.set('navixav-flight-summaries', JSON.stringify(legacy));
  const requests = [];
  let serverEntries = server.slice();
  const respond = (body) => ({ok: true, json: async () => body});
  const context = vm.createContext({
    FLIGHT_SUMMARY_KEY: 'navixav-flight-summaries',
    FLIGHT_SUMMARY_MAX_ENTRIES: 2000,
    latestStatus: {remote_client: remote},
    localStorage: {
      getItem: (k) => storage.get(k) ?? null,
      setItem: (k, v) => storage.set(k, String(v)),
      removeItem: (k) => storage.delete(k),
    },
    renderFlightSummaries() {},
    renderLogbookStats() {},
    setTimeout: () => 1,
    async fetch(url, options = {}) {
      const method = options.method || 'GET';
      const body = options.body ? JSON.parse(options.body) : null;
      requests.push({url, method, body});
      if (method === 'PUT') serverEntries = body.entries;
      if (method === 'POST' && url === '/api/logbook/import') {
        const known = new Set(serverEntries.map((e) => e.id));
        serverEntries = [...serverEntries, ...body.entries.filter((e) => !known.has(e.id))];
      }
      return respond({entries: serverEntries, stats: {flights: serverEntries.length}});
    },
  });
  const start = source.indexOf('let flightSummaries = [];');
  const end = source.indexOf('function summaryDistance(');
  vm.runInContext(source.slice(start, end), context);
  return {context, requests, storage, server: () => serverEntries};
}

test('nothing is written before the service logbook has been read', async () => {
  const {context, requests, server} = setup({server: [{id: 'old', ended_at: '1'}]});
  context.saveFlightSummaries([{id: 'new', ended_at: '2'}]);
  assert.equal(requests.length, 0);
  await context.initLogbook();
  // Le vol fait avant la lecture est fusionné, pas écrasé par-dessus le carnet.
  assert.deepEqual(server().map((e) => e.id).sort(), ['new', 'old']);
});

test('flights kept by the WebView are imported once, then forgotten locally', async () => {
  const {context, requests, storage, server} = setup({legacy: [{id: 'legacy', ended_at: '1'}]});
  await context.initLogbook();
  assert.equal(requests[1].url, '/api/logbook/import');
  assert.deepEqual(server().map((e) => e.id), ['legacy']);
  assert.equal(storage.has('navixav-flight-summaries'), false);
  assert.equal(context.loadFlightSummaries().length, 1);
});

test('once loaded, the PC window sends the whole logbook in order', async () => {
  const {context, requests, server} = setup();
  await context.initLogbook();
  context.saveFlightSummaries([{id: 'a'}]);
  context.saveFlightSummaries([{id: 'b'}, {id: 'a'}]);
  await vm.runInContext('logbookWrite', context);
  const puts = requests.filter((r) => r.method === 'PUT');
  assert.equal(puts.length, 2);
  assert.deepEqual(server().map((e) => e.id), ['b', 'a']);
});

test('a tablet never writes nor imports, it only reads', async () => {
  const {context, requests, storage} = setup({remote: true, legacy: [{id: 'tablet-local'}]});
  await context.initLogbook();
  context.saveFlightSummaries([{id: 'x'}]);
  assert.deepEqual(requests.map((r) => r.method), ['GET']);
  assert.equal(storage.has('navixav-flight-summaries'), true);
  assert.equal(context.loadFlightSummaries().length, 0);
});
