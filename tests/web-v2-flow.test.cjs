const {test} = require('node:test');
const assert = require('node:assert/strict');
const {createSession} = require('../src/web_v2/api.js');
const {createFlow, attributeRows} = require('../src/web_v2/flow.js');
const token = {access_token:'token',expires_in:86400};
function setup(handler) {
  const calls=[];
  const api={request: async (path,options) => {calls.push([path,options]); return handler(path,options);}};
  const session=createSession(null);
  const flow=createFlow({api,session,sleep:async()=>{}});
  return {flow,session,calls};
}
test('demo list is fetched and visible only when health explicitly enables demo mode', async () => {
  for (const enabled of [false,true]) {
    const x=setup(p => p==='/health' ? {demo_mode:enabled,models:{category:'fake'}} : [{user_id:2,display_name:'虛構用戶'}]);
    await x.flow.init();
    assert.equal(x.flow.state().demoVisible,enabled);
    assert.equal(x.calls.some(([p])=>p==='/auth/demo-users'),enabled);
    assert.equal(x.flow.state().demoUsers.length, enabled?1:0);
  }
});
test('health failure is recoverable and does not reveal a demo menu', async () => {
  let fail=true;
  const x=setup(() => {if(fail) throw Error('無法連線'); return {demo_mode:false};});
  await x.flow.init(); assert.match(x.flow.state().serviceError,/無法連線/);
  assert.equal(x.flow.state().demoVisible,false);
  fail=false; await x.flow.init(); assert.equal(x.flow.state().serviceError,'');
});
test('login uses form encoding with special characters and stores only issued session', async () => {
  const x=setup(()=>token);
  await x.flow.login('Amy','a&b=+茶');
  const [path,options]=x.calls[0];
  assert.equal(path,'/auth/login'); assert.equal(options.auth,false);
  assert.equal(options.body.get('username'),'Amy'); assert.equal(options.body.get('password'),'a&b=+茶');
  assert.equal(x.flow.state().view,'workspace'); assert.equal(x.session.get().token,'token');
});
test('registration omits blank display name and returns to login with a success notice', async () => {
  const x=setup(()=>({username:'amy'}));
  await x.flow.register('amy','long-password','  ');
  assert.deepEqual(x.calls[0][1].json,{username:'amy',password:'long-password'});
  assert.equal(x.flow.state().view,'login'); assert.match(x.flow.state().notice,/註冊成功/);
  assert.equal(x.session.get(),null);
});
test('registration failure preserves the registration view and communicates error', async () => {
  const x=setup(()=>{throw Error('這個帳號已被使用');}); x.flow.showAuth('register');
  await x.flow.register('amy','long-password','Amy');
  assert.equal(x.flow.state().view,'register'); assert.match(x.flow.state().error,/已被使用/);
  assert.equal(x.flow.state().busy,false);
});
test('demo login uses a listed integer id and selected display name', async () => {
  const x=setup(p=>p==='/health'?{demo_mode:true}:p==='/auth/demo-users'?[{user_id:2,display_name:'示範 A'}]:token);
  await x.flow.init(); await x.flow.demoLogin('2');
  assert.deepEqual(x.calls.at(-1)[1].json,{user_id:2});
  assert.equal(x.session.get().label,'示範 A');
});
test('demo login is not sent for unavailable or unlisted users', async () => {
  const x=setup(()=>({demo_mode:false})); await x.flow.init(); await x.flow.demoLogin('2');
  assert.equal(x.calls.length,1); assert.equal(x.session.get(),null);
});
test('classification renders ready data and preserves unknown, false and zero', async () => {
  const result={name:'虛構茶',category:{name:'飲品',prob:0.9},attributes_status:'ready',attributes:{sugar:0,alcohol:false,fun:null}};
  const x=setup(()=>result); x.session.set(token,'Amy');
  await x.flow.classify(' 虛構茶 ');
  assert.deepEqual(x.calls[0][1].json,{name:'虛構茶'});
  assert.equal(x.flow.state().classification.result,result);
  const rows=attributeRows(result.attributes);
  assert.equal(rows.find(r=>r.key==='sugar').value,'0');
  assert.equal(rows.find(r=>r.key==='alcohol').value,'否');
  assert.equal(rows.find(r=>r.key==='fun').value,'未知');
  assert.equal(rows.length,23);
});
test('pending answers exhaust bounded retries and show 稍後再查', async () => {
  const x=setup(()=>({name:'虛構新品',category:{name:'飲品',prob:0.6},attributes:null,attributes_status:'pending'}));
  x.session.set(token,'Amy'); await x.flow.classify('虛構新品');
  assert.equal(x.flow.state().classification.status,'pending');
  assert.equal(x.flow.state().classification.message,'稍後再查'); assert.equal(x.calls.length,6);
});
test('empty, overlong, or invisible names never reach the API', async () => {
  const x=setup(()=>({})); x.session.set(token,'Amy');
  for(const name of ['', '  ', '茶'.repeat(101), '茶\u200b', '茶\n葉']) await x.flow.classify(name);
  assert.equal(x.calls.length,0); assert.equal(x.flow.state().classification.status,'error');
});
test('unauthorized or switch account removes results and returns to login', async () => {
  const x=setup(()=>({attributes_status:'pending'})); x.session.set(token,'Amy');
  await x.flow.classify('虛構茶'); x.flow.unauthorized('登入已失效');
  assert.equal(x.flow.state().view,'login'); assert.equal(x.flow.state().classification.result,null);
  assert.equal(x.session.get(),null); assert.match(x.flow.state().error,/失效/);
});
test('a slow old classification cannot overwrite the new result or return after switching accounts', async () => {
  const resolvers=[]; const x=setup(()=>new Promise(r=>resolvers.push(r))); x.session.set(token,'Amy');
  const a=x.flow.classify('第一杯'); const b=x.flow.classify('第二杯');
  resolvers[1]({name:'第二杯',attributes_status:'ready'}); await b;
  resolvers[0]({name:'第一杯',attributes_status:'pending'}); await a;
  assert.equal(x.flow.state().classification.result.name,'第二杯');
  const c=x.flow.classify('第三杯'); x.flow.switchAccount();
  resolvers[2]({name:'第三杯',attributes_status:'pending'}); await c;
  assert.equal(x.flow.state().classification.result,null);
});
test('cancelled login cannot recreate a session after returning to another auth screen', async () => {
  let resolve; const x=setup(()=>new Promise(r=>resolve=r));
  const pending=x.flow.login('amy','password'); x.flow.showAuth('register'); resolve(token); await pending;
  assert.equal(x.session.get(),null); assert.equal(x.flow.state().view,'register');
});
