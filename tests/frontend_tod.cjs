const {test}=require('node:test');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../navixav/web/static/app.js'),'utf8').replaceAll('\r\n','\n');
function setup() {
  const context=vm.createContext({EARTH_RADIUS_M:6371000,activeFlightSummary:null,latestFms:null,
    flightGeometry:[{ident:'START',lat:0,lon:0,stage:'enroute'},{ident:'CEIL',lat:0,lon:1,stage:'star'},{ident:'END',lat:0,lon:2,stage:'approach'}]});
  for(const name of ['haversineNm','projectPointOnFlightPath','constraintAltitudeFt','finiteOr','standardAltitude','descentCeilings','simbriefTodFromDestination','fmsPointDistanceNm','descentGuidance']) {
    const start=source.indexOf('function '+name+'(');
    vm.runInContext(source.slice(start,source.indexOf('\n}',start)+2),context);
  }
  const plan={enroute:{cruise_altitude_ft:34000,simbrief_tod:{lat:0,lon:0.5}},arrival:{glide_intercept_altitude:'3000 ft'}};
  const aircraft={latitude:0,longitude:0.1,ground_speed_kt:450,configuration:{pressure_altitude_ft:34000}};
  return {context,plan,aircraft};
}
test('SimBrief TOD uses along-route distance and remains anchored as the aircraft moves',()=>{
  const {context:c,plan,aircraft:a}=setup();
  const first=c.descentGuidance(plan,a,c.projectPointOnFlightPath(a));
  assert.equal(first.source,'simbrief');
  assert.ok(Math.abs(first.todInNm-c.haversineNm(a,plan.enroute.simbrief_tod))<0.01);
  a.longitude=0.2;
  const next=c.descentGuidance(plan,a,c.projectPointOnFlightPath(a));
  assert.equal(next.anchorFromDestination,first.anchorFromDestination);
  assert.ok(next.todInNm<first.todInNm);
});
test('a constraint-adjusted TOD is identified as calculated rather than SimBrief',()=>{
  const {context:c,plan,aircraft:a}=setup();
  plan.arrival.star_constraints=[{is_fix:true,label:'CEIL',altitude:'5000 ft'}];
  const result=c.descentGuidance(plan,a,c.projectPointOnFlightPath(a));
  assert.equal(result.source,'calculated');
  assert.ok(result.anchorFromDestination>c.simbriefTodFromDestination(plan));
});
test('an off-route SimBrief point falls back to the calculated profile',()=>{
  const {context:c,plan,aircraft:a}=setup();
  plan.enroute.simbrief_tod.lat=1;
  assert.equal(c.descentGuidance(plan,a,c.projectPointOnFlightPath(a)).source,'calculated');
});
test('the T/D published by the aircraft FMGC overrides SimBrief and follows the FMS legs',()=>{
  const {context:c,plan,aircraft:a}=setup();
  // Active waypoint 0.4 deg ahead (~24 NM), then 30 NM of FMS legs to the T/D.
  c.latestFms={available:true,active:{ident:'ABC',lat:0,lon:0.5},tod:{ident:'(T/D)',lat:0,lon:1,to_distance_nm:null,distance_from_active_nm:30}};
  const result=c.descentGuidance(plan,a,c.projectPointOnFlightPath(a));
  assert.equal(result.source,'fms');
  const expected=c.haversineNm(a,{lat:0,lon:0.5})+30;
  assert.ok(Math.abs(result.todInNm-expected)<0.01);
  // The FMGC's own distance to the active waypoint wins over the geodesic one.
  c.latestFms.tod.to_distance_nm=20;
  assert.ok(Math.abs(c.descentGuidance(plan,a,c.projectPointOnFlightPath(a)).todInNm-50)<0.01);
  // Without an active waypoint the FMS point is unusable and SimBrief returns.
  c.latestFms={available:true,active:null,tod:{lat:0,lon:1,distance_from_active_nm:30}};
  assert.equal(c.descentGuidance(plan,a,c.projectPointOnFlightPath(a)).source,'simbrief');
});

function todDisplay(descent, phase) {
  const values = {}, element = {title:'old estimate'};
  const context = vm.createContext({
    t: key => key, tf: (key, args) => `${key}:${args.distance}`,
    liveValue: (id, text, status) => { values[id] = {text, status}; },
    $: () => element,
  });
  const start = source.indexOf('function updateTodDisplay(');
  vm.runInContext(source.slice(start, source.indexOf('\n}', start)+2), context);
  context.updateTodDisplay(descent, phase);
  return {...values['flight-tod'], title:element.title};
}

test('descent replaces an upcoming TOD even without a route projection', () => {
  for (const descent of [null, {todInNm:52, source:'simbrief', leftCruise:false}]) {
    const result = todDisplay(descent, 'phase_descent');
    assert.equal(result.text, 'tod_descent_active');
    assert.equal(result.status, 'good');
    assert.equal(result.title, 'tod_descent_active');
  }
});

test('descent level segments and approach do not restore the countdown', () => {
  const descent = {todInNm:17, leftCruise:true};
  assert.equal(todDisplay(descent, 'phase_enroute').text, 'tod_descent_active');
  assert.equal(todDisplay(descent, 'phase_approach').text, 'phase_approach');
});

test('cruise and climb retain estimates, ground and disconnected states clear TOD', () => {
  const descent = {todInNm:52, source:'simbrief', leftCruise:false};
  for (const phase of ['phase_cruise', 'phase_climb', 'phase_enroute']) {
    assert.match(todDisplay(descent, phase).text, /tod_in:52.*tod_source_simbrief/);
  }
  assert.match(todDisplay({todInNm:52, source:'fms', leftCruise:false}, 'phase_cruise').text, /tod_in:52.*tod_source_fms/);
  for (const phase of ['phase_offline', 'phase_landing', 'phase_taxi_in', 'phase_taxi_out', 'phase_takeoff']) {
    assert.equal(todDisplay(descent, phase).text, '—');
    assert.equal(todDisplay(descent, phase).title, '');
  }
});
