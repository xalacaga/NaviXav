const {test}=require('node:test');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../navixav/web/static/map.js'),'utf8').replaceAll('\r\n','\n')
  // Seule la liste interne du trafic est exposée au test, rien d'autre ne change.
  .replace('let traffic = [];','let traffic = []; globalThis.__traffic = () => traffic;');

function setup() {
  const clock={now:1000,wall:1_800_000_000_000};
  const timers=[];
  const canvas={
    getContext:()=>new Proxy({},{get:()=>()=>({})}),
    getClientRects:()=>[{}],addEventListener(){},
    clientWidth:800,clientHeight:600,width:800,height:600,style:{},
  };
  const context=vm.createContext({
    document:{hidden:false,body:{},getElementById:()=>canvas,createElement:()=>canvas,addEventListener(){}},
    window:{addEventListener(){},devicePixelRatio:1,matchMedia:()=>({matches:false,addEventListener(){}})},
    getComputedStyle:()=>({getPropertyValue:()=>''}),
    performance:{now:()=>clock.now},
    Date:{now:()=>clock.wall},
    setInterval:(fn)=>{timers.push(fn);return timers.length;},
    clearInterval:(id)=>{timers[id-1]=null;},
    setTimeout:()=>0,clearTimeout(){},requestAnimationFrame:()=>0,
    ResizeObserver:class{observe(){}},Image:class{},Map,Math,Number,Object,Array,
  });
  vm.runInContext(source+'\nglobalThis.MAP = MAP;',context);
  const tick=(ms)=>{clock.now+=ms;clock.wall+=ms;timers.forEach((fn)=>fn&&fn());};
  return {map:context.MAP,list:context.__traffic,clock,tick,timers};
}
const report=(longitude,extra={})=>({uid:'opensky:abc',callsign:'AFR123',latitude:0,longitude,
  ground_speed_kt:480,heading_deg:90,on_ground:false,position_timestamp:null,...extra});

test('an airborne aircraft keeps moving along its vector between two reports',()=>{
  const {map,list,tick}=setup();
  map.setTraffic([report(0)]);
  tick(60_000);
  // 480 kt during one minute: 8 NM, i.e. 8/60 deg of longitude at the equator.
  assert.ok(Math.abs(list()[0].displayLongitude-8/60)<0.002);
});

test('the same cached report does not send the aircraft back in time',()=>{
  const {map,list,tick}=setup();
  map.setTraffic([report(0)]);
  tick(30_000);
  map.setTraffic([report(0)]);
  assert.ok(Math.abs(list()[0].displayLongitude-4/60)<0.002);
});

test('a new report is blended in rather than teleported',()=>{
  const {map,list,tick}=setup();
  map.setTraffic([report(0)]);
  tick(60_000);
  const before=list()[0].displayLongitude;
  map.setTraffic([report(0.2)]);
  assert.ok(Math.abs(list()[0].displayLongitude-before)<1e-9);
  tick(15_000);
  // After five blend constants, the estimate follows the new report.
  assert.ok(Math.abs(list()[0].displayLongitude-(0.2+2/60))<0.001);
});

test('the report age is taken from the position timestamp',()=>{
  const {map,list,clock}=setup();
  map.setTraffic([report(0,{position_timestamp:clock.wall/1000-30})]);
  assert.ok(Math.abs(list()[0].displayLongitude-4/60)<0.002);
});

test('ground traffic stops quickly and parked traffic does not drift',()=>{
  const {map,list,tick}=setup();
  map.setTraffic([report(0,{uid:'taxi',on_ground:true,ground_speed_kt:15}),
    report(0,{uid:'parked',on_ground:true,ground_speed_kt:0})]);
  tick(60_000);
  const [taxi,parked]=list();
  // Three seconds at 15 kt at most, never a minute of straight-line taxi.
  assert.ok(Math.abs(taxi.displayLongitude-15*3/3600/60)<1e-6);
  assert.equal(parked.displayLongitude,0);
});

test('clearing the traffic stops the animation timer',()=>{
  const {map,timers}=setup();
  map.setTraffic([report(0)]);
  assert.ok(timers.some(Boolean));
  map.clearTraffic();
  assert.ok(!timers.some(Boolean));
});

test('a measured turn is continued then damped on the map',()=>{
  const {map,list,tick}=setup();
  map.setTraffic([report(0,{turn_rate_dps:3})]);
  tick(5_000);
  assert.ok(list()[0].displayHeading>90&&list()[0].displayHeading<105);
  tick(295_000);
  assert.ok(Math.abs(list()[0].displayHeading-135)<0.5);
  // Turning right from east, the aircraft ends south of a straight track.
  assert.ok(list()[0].displayLatitude<-0.05);
});

test('a new report blends the heading instead of snapping the silhouette',()=>{
  const {map,list,tick}=setup();
  map.setTraffic([report(0)]);
  tick(10_000);
  map.setTraffic([report(0.02,{heading_deg:120})]);
  assert.ok(Math.abs(list()[0].displayHeading-90)<1e-6);
  tick(15_000);
  assert.ok(Math.abs(list()[0].displayHeading-120)<1);
});
