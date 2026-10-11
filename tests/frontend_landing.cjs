const {test}=require('node:test');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../navixav/web/static/app.js'),'utf8').replaceAll('\r\n','\n');

function extract(context, names) {
  for (const name of names) {
    const start = source.indexOf(`function ${name}(`);
    assert.ok(start >= 0, name);
    vm.runInContext(source.slice(start, source.indexOf('\n}', start) + 2), context);
  }
}

function setup(summaries = []) {
  const storage = new Map();
  const opened = [];
  const dialog = {open: false};
  const context = vm.createContext({
    t: (key) => key,
    displayLocale: () => 'en',
    finiteOr: (value, fallback = null) => (Number.isFinite(Number(value)) && value !== null ? Number(value) : fallback),
    localStorage: {getItem: (k) => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, String(v))},
    $: () => dialog,
    currentPlan: {departure: {icao: 'LFPG'}, arrival: {icao: 'EGLL'}, callsign: 'AFR1'},
    summaries,
    saved: [],
    loadFlightSummaries: () => summaries,
    saveFlightSummaries: (entries) => context.saved.push(entries),
    renderFlightSummaries: () => {},
    openLandingDialog: (report, ctx) => opened.push({report, ctx}),
    LANDING_SEEN_KEY: 'seen',
    LANDING_SUMMARY_MATCH_MS: 180000,
  });
  vm.runInContext('var lastLandingSignature = ""; var displayedLanding = null;', context);
  extract(context, ['landingContext', 'handleLandingReport', 'attachLandingToSummary',
    'landingGradeTone', 'formatLandingNumber', 'landingMetrics']);
  return {context, opened, dialog};
}

const report = {
  touched_down_at: '2026-10-11T10:00:00Z', bounces: 0, final: false, rate_fpm: 180,
  grade: 'smooth', score: 92, airport: 'EGLL', runway: '27L', distance_from_threshold_m: 410,
  in_touchdown_zone: true, centerline_offset_m: -2.3, pitch_deg: 4.5, bank_deg: -1.2,
  indicated_airspeed_kt: 138, ground_speed_kt: 131, headwind_kt: -4, crosswind_kt: 7,
  stability: {}, rate_source: 'simulator',
};

test('a landing opens its analysis once and is attached to the flight just closed', () => {
  const summary = {ended_at: '2026-10-11T10:00:01.000Z', departure: 'LFPG', arrival: 'EGLL'};
  const older = {ended_at: '2026-10-10T08:00:00.000Z'};
  const {context, opened} = setup([summary, older]);
  context.handleLandingReport(report);
  context.handleLandingReport({...report});
  assert.equal(opened.length, 1);
  assert.equal(opened[0].ctx.arrival, 'EGLL');
  assert.equal(summary.landing.rate_fpm, 180);
  assert.equal(older.landing, undefined);
});

test('a bounce refreshes the analysis already on screen without reopening a new one', () => {
  const {context, opened, dialog} = setup([]);
  context.handleLandingReport(report);
  dialog.open = true;
  vm.runInContext('displayedLanding = {report: {touched_down_at: "2026-10-11T10:00:00Z"}, context: {arrival: "EGLL"}}', context);
  context.handleLandingReport({...report, bounces: 1});
  assert.equal(opened.length, 2);
  assert.equal(opened[1].report.bounces, 1);
});

test('metrics read side, tailwind and touchdown zone in plain words', () => {
  const {context} = setup();
  const rows = Object.fromEntries(context.landingMetrics(report));
  assert.equal(rows.landing_runway, 'EGLL 27L');
  assert.equal(rows.landing_threshold_distance, '410 m · landing_in_tdz');
  assert.equal(rows.landing_centerline, '2.3 m landing_left');
  assert.equal(rows.landing_bank, '1.2°');
  assert.equal(rows.landing_wind, 'landing_tailwind 4 kt · landing_crosswind 7 kt');
  assert.equal(rows.landing_bounces, '0');
});

test('an unknown runway leaves its lines out instead of showing blanks', () => {
  const {context} = setup();
  const rows = Object.fromEntries(context.landingMetrics({
    ...report, airport: null, runway: null, distance_from_threshold_m: null,
    centerline_offset_m: null, headwind_kt: null, crosswind_kt: null,
  }));
  assert.equal(rows.landing_runway, undefined);
  assert.equal(rows.landing_threshold_distance, undefined);
  assert.equal(rows.landing_wind, undefined);
});
