const {test}=require('node:test');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../navixav/web/static/app.js'),'utf8').replaceAll('\r\n','\n');

function constant(name) {
  const match=source.match(new RegExp(`^const ${name} = ([^;]+);`,'m'));
  assert.ok(match,name);
  return vm.runInNewContext(match[1]);
}

const CONSTANTS=['STABLE_GATE_IMC_FT','STABLE_GATE_VMC_FT','STABLE_FLOOR_FT','STABLE_WATCH_FT',
  'STABLE_MAX_SINK_FPM','STABLE_SPEED_WINDOW_MS','STABLE_SPEED_MIN_SPAN_MS','STABLE_SPEED_BAND_KT',
  'STABLE_MAX_DOTS','ILS_FULL_SCALE_DOTS','CDI_FULL_SCALE','GSI_FULL_SCALE',
  'SIGMET_LOOKAHEAD_NM','SIGMET_LOOKAHEAD_STEP_NM','SIGMET_VERTICAL_MARGIN_FT'];

function load(names, globals={}) {
  const context=vm.createContext({
    ...Object.fromEntries(CONSTANTS.map((name)=>[name,constant(name)])),
    stabilityMemory:{imc:false,speeds:[],gateCalled:false},
    t:(key)=>key,
    ...globals,
  });
  for(const name of names) {
    const start=source.indexOf('function '+name+'(');
    assert.ok(start>=0,name);
    vm.runInContext(source.slice(start,source.indexOf('\n}',start)+2),context);
  }
  return context;
}

const STABILITY=['finiteOr','ilsDots','stabilityFaults','stabilityGateFt','resetStabilityMemory','stabilityState'];
const configured={gear_extended_pct:100,flaps_handle_index:4,ils_receiver_index:1,
  nav1_has_localizer:true,nav1_has_glide_slope:true,nav1_cdi:10,nav1_gsi:-12};
const capabilities={retractable_gear:true,flaps:true};
const steady=[[0,140],[3000,138],[6000,141]];

test('a configured, steady approach on the ILS has no fault',()=>{
  const c=load(STABILITY);
  assert.deepEqual([...c.stabilityFaults({configuration:configured,capabilities,verticalSpeed:-750,speeds:steady})],[]);
});

test('each stabilisation criterion is reported in cockpit notation',()=>{
  const c=load(STABILITY);
  const faults=c.stabilityFaults({
    configuration:{...configured,gear_extended_pct:40,flaps_handle_index:0,nav1_cdi:90,nav1_gsi:-80},
    capabilities,verticalSpeed:-1400,speeds:[[0,160],[6000,141]],
  });
  assert.deepEqual([...faults],['GEAR','FLAPS','V/S -1400','IAS Δ19 kt','LOC 1.4 DOT','G/S 1.3 DOT']);
});

test('missing data or another ILS receiver is never counted as a fault',()=>{
  const c=load(STABILITY);
  assert.deepEqual([...c.stabilityFaults({
    configuration:{flaps_handle_index:0,gear_extended_pct:0,nav1_has_localizer:true,nav1_cdi:120,ils_receiver_index:3},
    capabilities:null,verticalSpeed:NaN,speeds:[[0,160],[1000,130]],
  })],[]);
});

test('the gate is 1000 ft in IMC and 500 ft in VMC',()=>{
  const c=load(STABILITY);
  assert.equal(c.stabilityGateFt({weather:{arrival:{flight_category:'VFR'}}},false),500);
  assert.equal(c.stabilityGateFt({weather:{arrival:{flight_category:'IFR'}}},false),1000);
  assert.equal(c.stabilityGateFt({weather:{arrival:{flight_category:'VFR'}}},true),1000);
});

test('criteria are only judged between the gate and 50 ft',()=>{
  const c=load(STABILITY);
  const context=(aglFt)=>({onGround:false,phase:'phase_approach',aglFt,airspeed:140,
    plan:{weather:{arrival:{flight_category:'VFR'}}},configuration:{...configured,gear_extended_pct:0},
    capabilities,verticalSpeed:-700});
  assert.equal(c.stabilityState(context(800),0).below,false);
  const below=c.stabilityState(context(450),1000);
  assert.equal(below.below,true);
  assert.deepEqual([...below.faults],['GEAR']);
  assert.equal(c.stabilityState(context(30),2000).below,false);
  assert.equal(c.stabilityState({...context(450),phase:'phase_cruise'},3000),null);
});

const SIGMET=['finiteOr','pointAlong','insideRing','sigmetAhead'];
const square=(lat,lon,size=1)=>[[lat,lon],[lat+size,lon],[lat+size,lon+size],[lat,lon+size]];
const flying=(heading,level=35000)=>({on_ground:false,latitude:45,longitude:0,heading_true_deg:heading,
  altitude_ft:level,configuration:{pressure_altitude_ft:level}});

test('a SIGMET crossed at the current level is found ahead on the current heading',()=>{
  const c=load(SIGMET);
  const sigmet={hazard:'TS',base_ft:null,top_ft:38000,polygons:[square(44.5,0.5)]};
  const hit=c.sigmetAhead(flying(90),[sigmet]);
  assert.equal(hit.sigmet,sigmet);
  assert.ok(hit.distanceNm>=20&&hit.distanceNm<=30,String(hit.distanceNm));
  assert.equal(c.sigmetAhead(flying(270),[sigmet]),null);
});

test('a SIGMET above or below the aircraft is not announced',()=>{
  const c=load(SIGMET);
  const high={hazard:'TURB',base_ft:39000,top_ft:45000,polygons:[square(44.5,0.5)]};
  assert.equal(c.sigmetAhead(flying(90,35000),[high]),null);
  assert.ok(c.sigmetAhead(flying(90,38500),[high]));
});

test('ring containment works across the antimeridian',()=>{
  const c=load(SIGMET);
  const ring=[[10,179],[12,179],[12,-179],[10,-179]];
  assert.equal(c.insideRing(ring,11,179.5),true);
  assert.equal(c.insideRing(ring,11,-179.5),true);
  assert.equal(c.insideRing(ring,11,170),false);
});

test('the new alerts have a translation and a voice clip in every bank',()=>{
  for(const key of ['alert_unstable_approach','alert_sigmet_ahead','voice_stabilized']) {
    for(const bank of ['fr','en','de','es','it','pt','nl','pl']) {
      const manifest=JSON.parse(fs.readFileSync(path.join(__dirname,`../navixav/web/static/voice/${bank}/manifest.json`),'utf8'));
      assert.ok(manifest.clips[key],`${bank}:${key}`);
    }
  }
});
