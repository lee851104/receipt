const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'); const path=require('node:path'); const vm=require('node:vm');
const dir=path.join(__dirname,'../src/web_v2');
function page(responder){
  class Element{
    constructor(){this.hidden=false;this.value='';this.textContent='';this.children=[];this.listeners={};this.style={};}
    setAttribute(k,v){this[k]=v;} replaceChildren(...nodes){this.children=nodes;} append(...nodes){this.children.push(...nodes);}
    addEventListener(k,v){this.listeners[k]=v;} focus(){this.focused=true;}
    async fire(type){return this.listeners[type]?.({preventDefault(){},currentTarget:this});}
  }
  const html=fs.readFileSync(path.join(dir,'index.html'),'utf8');
  const nodes=Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element()]));
  const doc={getElementById:id=>{assert.ok(nodes[id],`missing element ${id}`);return nodes[id];},createElement:()=>new Element(),querySelectorAll:()=>[]};
  const store=new Map(), events={}, calls=[];const location={hash:'#classify'};
  const context=vm.createContext({document:doc,location,history:{replaceState(_,__,hash){location.hash=hash;}},sessionStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v),removeItem:k=>store.delete(k)},addEventListener:(k,v)=>events[k]=v,Headers,URLSearchParams,AbortController,DOMException,setTimeout,clearTimeout,
    fetch:async(p,o)=>{calls.push([p,o]);const [status,body]=await responder(p,o);return new Response(JSON.stringify(body),{status});}});
  for(const file of ['api.js','flow.js','app.js'])vm.runInContext(fs.readFileSync(path.join(dir,file),'utf8'),context);
  return {nodes,store,location,calls,events};
}
const tick=()=>new Promise(r=>setImmediate(r));
test('real page starts at login with demo hidden when disabled',async()=>{
  const x=page(()=>[200,{demo_mode:false,models:{category:'fake',attributes:'fake'}}]); await tick();
  assert.equal(x.nodes['workspace-view'].hidden,true); assert.equal(x.nodes['auth-view'].hidden,false);
  assert.equal(x.nodes['demo-panel'].hidden,true); assert.equal(x.location.hash,'#login');
});
test('real page supports demo login, classification, safe result text and identity switching',async()=>{
  const x=page(p=>p.endsWith('/health')?[200,{demo_mode:true,models:{category:'fake',attributes:'fake'}}]:p.endsWith('/demo-users')?[200,[{user_id:2,display_name:'示範 A'}]]:p.endsWith('/demo-login')?[200,{access_token:'abc',expires_in:3600}]:[200,{name:'<img src=x onerror=alert(1)>',category:{name:'飲品',prob:0.9},attributes_status:'ready',attributes:{alcohol:false,sugar:0,fun:null}}]);
  await tick(); assert.equal(x.nodes['demo-panel'].hidden,false);
  x.nodes['demo-user'].value='2';await x.nodes['demo-form'].fire('submit');
  assert.equal(x.nodes['workspace-view'].hidden,false); assert.equal(x.nodes['identity-label'].textContent,'示範 A');
  x.nodes['item-name'].value='虛構茶'; await x.nodes['classify-form'].fire('submit');
  assert.equal(x.nodes['result-name'].textContent,'<img src=x onerror=alert(1)>');
  assert.equal(x.nodes['category-probability'].textContent,'90%');
  assert.equal(x.nodes['attribute-list'].children.length,23);
  assert.equal(x.nodes['model-note'].hidden,false);
  await x.nodes['switch-account'].fire('click');
  assert.equal(x.nodes['workspace-view'].hidden,true); assert.equal(x.nodes['classification-result'].hidden,true);
  assert.equal(x.nodes['attribute-list'].children.length,0);assert.equal(x.nodes['item-name'].value,'');
  assert.equal(x.store.size,0);
});
test('login error is Chinese, password is cleared and an API 401 clears prior results',async()=>{
  let authenticated=false;
  const x=page(p=>p.endsWith('/health')?[200,{demo_mode:false}]:p.endsWith('/login') && authenticated?[200,{access_token:'abc',expires_in:3600}]:[401,{detail:authenticated?'not_authenticated':'bad_credentials'}]);
  await tick();x.nodes['login-username'].value='amy';x.nodes['login-password'].value='wrong';
  await x.nodes['login-form'].fire('submit');
  assert.equal(x.nodes['auth-error'].textContent,'帳號或密碼錯誤。');assert.equal(x.nodes['login-password'].value,'');
  authenticated=true;x.nodes['login-password'].value='good';await x.nodes['login-form'].fire('submit');
  x.nodes['item-name'].value='虛構茶';await x.nodes['classify-form'].fire('submit');
  assert.equal(x.nodes['workspace-view'].hidden,true);assert.match(x.nodes['auth-error'].textContent,/失效/);
});
