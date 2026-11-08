const {test}=require('node:test');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const STATIC=path.join(__dirname,'../navixav/web/static');
const read=(name)=>fs.readFileSync(path.join(STATIC,name),'utf8').replaceAll('\r\n','\n');

function loadGuide() {
  const context=vm.createContext({});
  vm.runInContext(read('guide.js')+';this.GUIDE=GUIDE;',context);
  return context.GUIDE;
}

function loadI18n() {
  const storage=new Map();
  const window={
    localStorage:{getItem:(k)=>(storage.has(k)?storage.get(k):null),setItem:(k,v)=>storage.set(k,String(v))},
    dispatchEvent(){},addEventListener(){},CustomEvent:function CustomEvent(){},
    document:{documentElement:{},title:'',querySelector:()=>null,querySelectorAll:()=>[],addEventListener(){}},
    navigator:{languages:[]},
  };
  window.window=window;
  const context=vm.createContext(window);
  vm.runInContext(read('i18n.js'),context);
  return context.window.I18N;
}

const LANGUAGES=['fr','en','de','es','it','pt','nl','pl'];

test('the guide exists in the eight interface languages with the same entries',()=>{
  const guide=loadGuide();
  assert.deepEqual([...guide.languages()].sort(),[...LANGUAGES].sort());
  const reference=guide.text('fr');
  for(const language of LANGUAGES) {
    const text=guide.text(language);
    assert.ok(text.title&&text.intro&&text.contents,language);
    for(const section of guide.sections) {
      assert.ok(text.sections[section]?.title,`${language}:${section}`);
      assert.deepEqual(Object.keys(text.sections[section].items),Object.keys(reference.sections[section].items),`${language}:${section}`);
      for(const [id,[term,body]] of Object.entries(text.sections[section].items)) {
        assert.ok(term&&body&&body.length>20,`${language}:${section}.${id}`);
      }
    }
  }
});

test('every module and every settings group is described',()=>{
  const html=read('index.html');
  const guide=loadGuide().text('fr');
  const tabs=[...html.matchAll(/<button data-tab="([a-z]+)"/g)].map((m)=>m[1]);
  assert.ok(tabs.length>=10);
  assert.deepEqual(Object.keys(guide.sections.modules.items).sort(),[...tabs].sort());
  const groups=[...html.matchAll(/<strong id="settings-section-([a-z-]+)">/g)].map((m)=>m[1].replaceAll('-','_'));
  assert.ok(groups.length>=7);
  for(const group of groups) assert.ok(guide.sections.settings.items[group],group);
  assert.ok(guide.sections.settings.items.aircraft_procedures);
  assert.ok(guide.sections.settings.items.changelog);
});

test('every interface label the guide refers to exists in every language',()=>{
  const guide=loadGuide();
  const I18N=loadI18n();
  const app=read('app.js');
  const block=app.slice(app.indexOf('const GUIDE_TERM_KEYS = {'),app.indexOf('};',app.indexOf('const GUIDE_TERM_KEYS = {')));
  const termKeys=[...block.matchAll(/: "([a-z_]+)"/g)].map((m)=>m[1]);
  assert.ok(termKeys.length>20);
  for(const language of LANGUAGES) {
    I18N.setLanguage(language);
    const text=JSON.stringify(guide.text(language));
    const keys=new Set([...text.matchAll(/\{([a-z_]+)\}/g)].map((m)=>m[1]).concat(termKeys));
    for(const key of keys) assert.notEqual(I18N.t(key),key,`${language}:${key}`);
  }
});

test('the guide is loaded before the application and opened from the settings',()=>{
  const html=read('index.html');
  assert.ok(html.indexOf('/static/guide.js')<html.indexOf('/static/app.js'));
  assert.match(html,/id="guide-open"/);
  assert.match(html,/id="guide-dialog"/);
});
