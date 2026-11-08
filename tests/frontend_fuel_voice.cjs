const {test}=require('node:test');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../navixav/web/static/app.js'),'utf8').replaceAll('\r\n','\n');

function load(names, globals={}) {
  const context=vm.createContext({LBS_TO_KG:0.45359237,FUEL_MONITOR_MAX_OFF_ROUTE_NM:30,flightRouteTotalNm:400,...globals});
  for(const name of names) {
    const start=source.indexOf('function '+name+'(');
    assert.ok(start>=0,name);
    vm.runInContext(source.slice(start,source.indexOf('\n}',start)+2),context);
  }
  return context;
}

const FUEL=['finiteOr','measuredFuelKg','reserveFuelKg','ofpFuelKg','plannedFuelOnboardKg','fuelMonitor'];
const plan={dispatch:{units:'kgs',route_distance_nm:400,landing_fuel:2400,trip_fuel:2600,reserve_fuel:1150,alternate_fuel:1090,contingency_fuel:150,
  fuel_profile:[[400,5000],[200,3800],[50,2700],[0,2400]]}};
const airborne=(fuel)=>({on_ground:false,configuration:{fuel_total_kg:fuel}});

test('planned fuel follows the SimBrief navlog profile between its points',()=>{
  const c=load(FUEL);
  assert.equal(c.plannedFuelOnboardKg(plan,200,400),3800);
  assert.equal(c.plannedFuelOnboardKg(plan,300,400),4400);
  assert.equal(c.plannedFuelOnboardKg(plan,0,400),2400);
});

test('the navlog profile is scaled when the flown route is longer than the OFP one',()=>{
  const c=load(FUEL);
  // 440 NM flown route: half-way is still half-way on the navlog.
  assert.equal(c.plannedFuelOnboardKg(plan,220,440),3800);
});

test('without a navlog profile the trip fuel is spread along the route',()=>{
  const c=load(FUEL);
  const flat={dispatch:{...plan.dispatch,fuel_profile:[]}};
  assert.equal(c.plannedFuelOnboardKg(flat,200,400),2400+1300);
});

test('pounds are converted before any comparison',()=>{
  const c=load(FUEL);
  const pounds={dispatch:{...plan.dispatch,units:'lbs'}};
  assert.ok(Math.abs(c.plannedFuelOnboardKg(pounds,200,400)-3800*0.45359237)<1e-6);
});

test('a fuel surplus or shortfall carries over to the destination estimate',()=>{
  const c=load(FUEL);
  const on=c.fuelMonitor(plan,airborne(3900),{remainingNm:200,crossTrackNm:1});
  assert.equal(on.deviation,100);
  assert.equal(on.destination,2500);
  assert.equal(on.minimum,2240);
  assert.equal(on.status,'good');
  assert.equal(on.deviationStatus,'good');

  const short=c.fuelMonitor(plan,airborne(3500),{remainingNm:200,crossTrackNm:1});
  assert.equal(short.destination,2100);
  assert.equal(short.status,'warning');
  assert.equal(short.deviationStatus,'warning');

  const critical=c.fuelMonitor(plan,airborne(2500),{remainingNm:200,crossTrackNm:1});
  assert.equal(critical.status,'danger');
});

test('the fuel monitor stays silent on the ground, off route or without data',()=>{
  const c=load(FUEL);
  const projection={remainingNm:200,crossTrackNm:1};
  assert.equal(c.fuelMonitor(plan,{on_ground:true,configuration:{fuel_total_kg:3800}},projection),null);
  assert.equal(c.fuelMonitor(plan,airborne(3800),{remainingNm:200,crossTrackNm:45}),null);
  assert.equal(c.fuelMonitor(plan,airborne(null),projection),null);
  assert.equal(c.fuelMonitor({dispatch:{}},airborne(3800),projection),null);
});

function voice() {
  const spoken=[];
  const c=load(['resetVoiceMemory','announceAlerts','todVoiceStage','announceTod','announceTaxi'],{
    t:(key)=>key,
    tf:(key,values)=>`${key}:${values.distance}`,
    VOICE:{announce:(parts,options={})=>{spoken.push({parts,priority:Boolean(options.priority)});return true;}},
  });
  vm.runInContext('var voiceMemory={alerts:new Set(),todRank:0,taxi:""};var TOD_VOICE_RANK={prepare:1,imminent:2,now:3};',c);
  return {c,spoken};
}

test('an alert is announced once when it appears, critical ones interrupt',()=>{
  const {c,spoken}=voice();
  const caution={id:'gear',severity:'warning',label:'Gear'};
  const warning={id:'stall',severity:'danger',label:'Stall'};
  c.announceAlerts([caution]);
  c.announceAlerts([caution]);
  c.announceAlerts([caution,warning]);
  assert.deepEqual(JSON.parse(JSON.stringify(spoken)),[
    {parts:[{key:'master_caution'},{key:'alert_gear'}],priority:false},
    {parts:[{key:'master_warning'},{key:'alert_stall'}],priority:true},
  ]);
  // Cleared then raised again: it is a new event and is spoken again.
  c.announceAlerts([]);
  c.announceAlerts([caution]);
  assert.equal(spoken.length,3);
});

test('the top of descent is announced at 50, 10 and 0 NM, each step once',()=>{
  const {c,spoken}=voice();
  for(const distance of [80,48,45,9,8,1,0]) c.announceTod({todInNm:distance,leftCruise:false},'phase_cruise');
  assert.deepEqual(JSON.parse(JSON.stringify(spoken.map((item)=>item.parts))),[
    [{key:'voice_tod_prepare',values:{distance:48}}],
    [{key:'voice_tod_imminent',values:{distance:9}}],
    [{key:'voice_tod_now'}],
  ]);
});

test('no top of descent call once the descent has started or on the ground',()=>{
  const {c,spoken}=voice();
  c.announceTod({todInNm:20,leftCruise:true},'phase_cruise');
  c.announceTod({todInNm:20,leftCruise:false},'phase_descent');
  c.announceTod({todInNm:20,leftCruise:false},'phase_taxi_out');
  assert.equal(spoken.length,0);
});

test('a taxi instruction is spoken when it changes, not at every refresh',()=>{
  const {c,spoken}=voice();
  const hold={key:'taxi_hold_short',values:{runway:'32R'}};
  for(const call of [hold,{...hold},null,{key:'taxi_turn_left',values:{taxiway:'B'}}]) c.announceTaxi(call);
  assert.deepEqual(JSON.parse(JSON.stringify(spoken.map((item)=>item.parts[0].key))),['taxi_hold_short','taxi_turn_left']);
});

/* ------------------------------------------------ voice.js : la banque */

function voiceModule() {
  const voiceSource=fs.readFileSync(path.join(__dirname,'../navixav/web/static/voice.js'),'utf8');
  const window={I18N:{getLanguage:()=>'fr',t:(key)=>key}};
  const context=vm.createContext({window,localStorage:{getItem:()=>null,setItem(){}},fetch:()=>Promise.reject(new Error('offline'))});
  vm.runInContext(voiceSource+';globalThis.VOICE=VOICE;',context);
  return context.VOICE;
}

const BANK={language:'fr',voice:'ff_siwis',
  clips:Object.fromEntries([
    'master_caution','alert_gear','voice_tod_now','taxi_hold_short.0','taxi_turn_left.0','voice_tod_imminent.0','voice_tod_imminent.2',
    'number_9','digit_0','digit_3','digit_2','digit_9','runway_R','letter_B','letter_N','digit_1',
  ].map((id)=>[id,`${id}.ogg`])),
  templates:{
    taxi_hold_short:[{clip:'taxi_hold_short.0'},{slot:'runway'}],
    taxi_turn_left:[{clip:'taxi_turn_left.0'},{slot:'taxiway'}],
    voice_tod_imminent:[{clip:'voice_tod_imminent.0'},{slot:'distance'},{clip:'voice_tod_imminent.2'}],
  }};
const names=(urls)=>urls&&[...urls].map((url)=>url.split('/').pop().replace('.ogg',''));

test('fixed phrases and alerts map to their recorded files',()=>{
  const V=voiceModule();
  assert.deepEqual(names(V._plan(BANK,[{key:'master_caution'},{key:'alert_gear'}])),['master_caution','alert_gear']);
  assert.equal(V._plan(BANK,[{key:'alert_gear'}])[0],'/static/voice/fr/alert_gear.ogg');
});

test('runways are read digit by digit with their side, taxiways letter by letter',()=>{
  const V=voiceModule();
  assert.deepEqual(names(V._plan(BANK,[{key:'taxi_hold_short',values:{runway:'32R'}}])),['taxi_hold_short.0','digit_3','digit_2','runway_R']);
  assert.deepEqual(names(V._plan(BANK,[{key:'taxi_hold_short',values:{runway:'9'}}])),['taxi_hold_short.0','digit_0','digit_9']);
  assert.deepEqual(names(V._plan(BANK,[{key:'taxi_turn_left',values:{taxiway:'N1'}}])),['taxi_turn_left.0','letter_N','digit_1']);
  assert.deepEqual(names(V._plan(BANK,[{key:'voice_tod_imminent',values:{distance:9.4}}])),['voice_tod_imminent.0','number_9','voice_tod_imminent.2']);
});

test('anything the bank cannot say falls back to the Windows voice',()=>{
  const V=voiceModule();
  assert.equal(V._plan(BANK,[{key:'unknown_key'}]),null);
  assert.equal(V._plan(BANK,[{key:'taxi_turn_left',values:{taxiway:'Z9'}}]),null);
  assert.equal(V._plan(BANK,[{key:'voice_tod_imminent',values:{distance:75}}]),null);
  assert.equal(V._plan(null,[{key:'alert_gear'}]),null);
});

test('weather briefing warnings are translated outside French',()=>{
  const start=source.indexOf('function warningText(');
  const context=vm.createContext({displayLocale:()=>'en'});
  vm.runInContext(source.slice(start,source.indexOf('\n}',start)+2),context);
  assert.equal(context.warningText('LFPO en conditions LIFR.'),'LFPO in LIFR conditions.');
  assert.equal(context.warningText('Météo indisponible pour LFBO.'),'Weather unavailable for LFBO.');
});
