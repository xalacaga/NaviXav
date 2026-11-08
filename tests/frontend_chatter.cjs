const {test}=require('node:test');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const STATIC=path.join(__dirname,'../navixav/web/static');
const read=(name)=>fs.readFileSync(path.join(STATIC,name),'utf8').replaceAll('\r\n','\n');

function loadChatter() {
  const storage=new Map();
  const context=vm.createContext({
    localStorage:{getItem:(k)=>(storage.has(k)?storage.get(k):null),setItem:(k,v)=>storage.set(k,String(v))},
    window:{addEventListener(){}},
    fetch:()=>Promise.resolve({ok:false}),
    setTimeout:()=>1,clearTimeout(){},
  });
  vm.runInContext(read('chatter.js')+';this.CHATTER=CHATTER;',context);
  return context.CHATTER;
}

const air=(extra={})=>({on_ground:false,altitude_ft:5000,height_above_ground_ft:4000,...extra});

test('the radio position follows the flight phase',()=>{
  const chatter=loadChatter();
  const at=chatter._positionFor;
  assert.equal(at('phase_taxi_out',air({on_ground:true})),'ground');
  assert.equal(at('phase_taxi_in',air({on_ground:true})),'ground');
  assert.equal(at('phase_takeoff',air()),'tower');
  assert.equal(at('phase_climb',air({height_above_ground_ft:1200})),'tower');
  assert.equal(at('phase_climb',air({altitude_ft:7000,height_above_ground_ft:6500})),'approach');
  assert.equal(at('phase_climb',air({altitude_ft:18000,height_above_ground_ft:17000})),'center');
  assert.equal(at('phase_cruise',air({altitude_ft:36000})),'center');
  assert.equal(at('phase_descent',air({altitude_ft:8000})),'approach');
  assert.equal(at('phase_approach',air({height_above_ground_ft:3000})),'approach');
  assert.equal(at('phase_approach',air({height_above_ground_ft:900})),'tower');
});

test('the ambience stays silent offline, paused or without an aircraft',()=>{
  const chatter=loadChatter();
  assert.equal(chatter._positionFor('phase_offline',air()),null);
  assert.equal(chatter._positionFor('phase_cruise',null),null);
  assert.equal(chatter._positionFor('phase_cruise',air({paused:true})),null);
});

test('recently heard exchanges are not picked again while others remain',()=>{
  const chatter=loadChatter();
  const entries=[{file:'a'},{file:'b'},{file:'c'}];
  for(let i=0;i<20;i++) assert.equal(chatter._pick(entries,['a','b'],Math.random).file,'c');
  assert.ok(['a','b','c'].includes(chatter._pick(entries,['a','b','c'],()=>0.5).file));
  assert.equal(chatter._pick([],[],Math.random),null);
});

test('the ambience is off by default and keeps its volume within range',()=>{
  const chatter=loadChatter();
  assert.equal(chatter.enabled(),false);
  assert.equal(chatter.volume(),0.35);
  chatter.setVolume(3);
  assert.equal(chatter.volume(),1);
  chatter.setVolume(-1);
  assert.equal(chatter.volume(),0);
});

test('the bank covers every position and every listed file exists',()=>{
  const manifest=JSON.parse(read('chatter/manifest.json'));
  for(const position of ['ground','tower','approach','center']) {
    const entries=manifest.positions[position];
    assert.ok(entries.length>=20,position);
    for(const entry of entries) {
      assert.ok(fs.existsSync(path.join(STATIC,'chatter',entry.file)),entry.file);
      assert.ok(entry.duration>1&&entry.duration<30,entry.file);
    }
  }
  const size=fs.readdirSync(path.join(STATIC,'chatter')).reduce(
    (total,name)=>total+fs.statSync(path.join(STATIC,'chatter',name)).size,0);
  assert.ok(size<15*1024*1024,String(size));
});

test('NaviXav callouts silence the ambience',()=>{
  const voice=read('voice.js');
  assert.match(voice,/navixav:voice-start/);
  assert.match(voice,/speaking: \(\) =>/);
  const html=read('index.html');
  assert.ok(html.indexOf('/static/voice.js')<html.indexOf('/static/chatter.js'));
  assert.ok(html.indexOf('/static/chatter.js')<html.indexOf('/static/app.js'));
});
