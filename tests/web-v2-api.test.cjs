const { test } = require('node:test');
const assert = require('node:assert/strict');
const { createSession, createClient, errorMessage } = require('../src/web_v2/api.js');

function setup(fetchImpl, now = () => 1000) {
  const values = new Map();
  const storage = {getItem: k => values.get(k) ?? null, setItem: (k,v) => values.set(k,v), removeItem: k => values.delete(k)};
  const session = createSession(storage, now);
  let redirected = 0;
  const api = createClient({session, fetchImpl, onUnauthorized: () => redirected++});
  return {session, api, values, storage, redirects: () => redirected};
}
const ok = data => new Response(JSON.stringify(data), {status:200, headers:{'Content-Type':'application/json'}});
const bad = (status, data) => new Response(JSON.stringify(data), {status});
const signIn = s => s.set({access_token:'token-a', expires_in:86400}, '測試使用者');

test('protected requests carry the current bearer and JSON body; public requests carry no bearer', async () => {
  const calls = [];
  const {api, session} = setup(async (path, options) => {calls.push([path,options]); return ok({ready:true});});
  signIn(session);
  await api.request('/items/classify', {method:'POST', json:{name:'虛構茶'}});
  await api.request('/health', {auth:false});
  assert.equal(calls[0][0], '/api/items/classify');
  assert.equal(calls[0][1].headers.get('Authorization'), 'Bearer token-a');
  assert.equal(calls[0][1].headers.get('Content-Type'), 'application/json');
  assert.deepEqual(JSON.parse(calls[0][1].body), {name:'虛構茶'});
  assert.equal(calls[1][1].headers.has('Authorization'), false);
});
test('missing token redirects without sending a protected request', async () => {
  let calls = 0;
  const x = setup(async () => {calls++; return ok({});});
  await assert.rejects(x.api.request('/items/classify'), {status:401});
  assert.equal(calls,0); assert.equal(x.redirects(),1);
});
test('401 clears token and redirects exactly once; login errors remain readable', async () => {
  const x = setup(async () => bad(401,{detail:'bad_credentials'}));
  signIn(x.session);
  await assert.rejects(x.api.request('/auth/login',{auth:false}), {message:'帳號或密碼錯誤。',status:401});
  assert.equal(x.session.get(),null); assert.equal(x.redirects(),1);
});
test('known errors, 422 lists and unknown details are rendered in Chinese without rejected input', () => {
  assert.equal(errorMessage(409,{detail:'username_taken'}),'這個帳號已被使用，請換一個。');
  assert.match(errorMessage(422,{detail:[{loc:['body','password'],input:'secret',msg:'english'}]}),/密碼/);
  assert.doesNotMatch(errorMessage(422,{detail:[{loc:['body','password'],input:'secret',msg:'english'}]}),/secret|english/);
  assert.equal(errorMessage(404,{detail:'Not Found'}),'暫時無法完成，請稍後再試。');
  assert.match(errorMessage(400,{detail:'invalid_csv',message:'一份檔案只能有一個月'}),/一份檔案只能有一個月/);
});
test('non-JSON failures and network failures have useful errors', async () => {
  const html = setup(async () => new Response('<html>failure</html>',{status:502}));
  await assert.rejects(html.api.request('/health',{auth:false}), /暫時無法完成/);
  const offline = setup(async () => {throw new TypeError('Failed to fetch');});
  await assert.rejects(offline.api.request('/health',{auth:false}), /無法連線/);
});
test('204 is accepted; invalid successful JSON is an explicit error', async () => {
  const x = setup(async () => new Response(null,{status:204}));
  assert.equal(await x.api.request('/health',{auth:false}),null);
  const y = setup(async () => new Response('<html>oops</html>',{status:200}));
  await assert.rejects(y.api.request('/health',{auth:false}), /回應格式/);
});
test('session is restored, expires, tolerates broken storage, and stores no password', () => {
  let now = 1000;
  const x = setup(async () => ok({}), () => now);
  x.session.set({access_token:'a',expires_in:2,password:'never-store'},'Amy');
  assert.equal(createSession(x.storage,()=>now).get().label,'Amy');
  assert.doesNotMatch([...x.values.values()].join(''), /never-store|password/);
  now=3001; assert.equal(x.session.get(),null);
  x.storage.setItem('receipt.v2.session','bad json');
  assert.equal(createSession(x.storage).get(),null);
  const denied = {getItem(){throw Error();},setItem(){throw Error();},removeItem(){throw Error();}};
  const memory = createSession(denied); signIn(memory); assert.equal(memory.get().token,'token-a');
  memory.clear(); assert.equal(memory.get(),null);
});
test('a stale success or 401 cannot affect a newly selected identity', async () => {
  for (const response of [ok({name:'old'}), bad(401,{detail:'not_authenticated'})]) {
    let resolve;
    const x = setup(() => new Promise(r => resolve=r)); signIn(x.session);
    const pending = x.api.request('/items/classify');
    x.session.set({access_token:'new',expires_in:60},'New');
    resolve(response);
    await assert.rejects(pending,{name:'AbortError'});
    assert.equal(x.session.get().token,'new'); assert.equal(x.redirects(),0);
  }
});
test('API client refuses external and parent paths before attaching credentials', async () => {
  const x = setup(async () => {throw Error('must not fetch');}); signIn(x.session);
  for (const path of ['https://example.com','//example.com','/../other','/auth/../../other']) {
    await assert.rejects(x.api.request(path), /API 路徑/);
  }
});
test('public service information survives a successful login while it is in flight', async () => {
  for(const path of ['/health','/auth/demo-users']){
    let resolve;
    const x=setup(()=>new Promise(r=>resolve=r));
    const request=x.api.request(path,{auth:false});signIn(x.session);
    resolve(ok({demo_mode:true}));
    assert.deepEqual(await request,{demo_mode:true});assert.equal(x.redirects(),0);
  }
});
test('aborting while reading a 401 body never navigates away from a new auth screen', async () => {
  let reading;
  const started=new Promise(r=>reading=r);
  const x=setup(async (_,options)=>({status:401,ok:false,json:()=>new Promise((_,reject)=>{
    reading();options.signal.addEventListener('abort',()=>reject(new DOMException('cancelled','AbortError')),{once:true});
  })}));
  const controller=new AbortController();
  const pending=x.api.request('/auth/login',{auth:false,signal:controller.signal});
  await started;controller.abort();
  await assert.rejects(pending,{name:'AbortError'});assert.equal(x.redirects(),0);
});
