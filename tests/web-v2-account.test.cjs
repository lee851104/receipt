const {test}=require('node:test');const assert=require('node:assert/strict');
const {createSession}=require('../src/web_v2/api.js');
const {createAccount}=require('../src/web_v2/account-flow.js');
const me={user_id:301,username:'amy',display_name:'Amy',is_demo:false,months:['2026-05','2026-06']};
function setup(handler=()=>me){
 const session=createSession(null);session.set({access_token:'old',expires_in:3600},'Amy');const calls=[],changed=[],ended=[];
 const account=createAccount({session,api:{request:async(p,o)=>{calls.push([p,o]);return handler(p,o);}},onChanged:k=>changed.push(k),onEnded:k=>ended.push(k)});
 return {account,session,calls,changed,ended};
}
test('loads account and renames without extending session expiry',async()=>{
 const x=setup((p,o)=>o.method==='PATCH'?{...me,display_name:o.json.display_name}:me);await x.account.load();
 const expiry=x.session.get().expiresAt;await x.account.rename('新名字');
 assert.equal(x.session.get().label,'新名字');assert.equal(x.session.get().expiresAt,expiry);assert.equal(x.account.state().profile.display_name,'新名字');assert.deepEqual(x.changed,['name']);
});
test('password response replaces token without storing either password',async()=>{
 const x=setup(p=>p==='/me/password'?{access_token:'new',expires_in:3600}:me);await x.account.load();
 await x.account.changePassword('old-password','new-password');assert.equal(x.session.get().token,'new');assert.deepEqual(x.changed,['password']);
 assert(!JSON.stringify(x.account.state()).includes('password'));assert(!JSON.stringify(x.session.get()).includes('password'));
});
test('month deletion requires an explicit confirmation and removes only that month',async()=>{
 const x=setup();await x.account.load();await x.account.confirmDeletion();assert.equal(x.calls.length,1);
 x.account.askDeleteMonth('2026-05');x.account.cancelConfirmation();await x.account.confirmDeletion();assert.equal(x.calls.length,1);
 x.account.askDeleteMonth('2026-05');await x.account.confirmDeletion();assert.equal(x.calls[1][0],'/me/months/2026-05');assert.equal(x.calls[1][1].method,'DELETE');assert.deepEqual(x.account.state().profile.months,['2026-06']);assert.deepEqual(x.changed,['month']);
});
test('deleting an account requires a password and successful server response',async()=>{
 let fail=true;const x=setup((p,o)=>{if(o.method==='DELETE'&&fail)throw Object.assign(Error('密碼錯誤'),{status:403});return me;});await x.account.load();
 x.account.askDeleteAccount();await x.account.confirmDeletion('');assert.equal(x.calls.length,1);
 await x.account.confirmDeletion('wrong');assert(x.session.get());assert.equal(x.ended.length,0);assert(x.account.state().confirmation);
 fail=false;await x.account.confirmDeletion('correct');assert.equal(x.session.get(),null);assert.deepEqual(x.ended,['deleted']);
});
test('409 preserves the month and demo users cannot mutate through the controller',async()=>{
 const x=setup((p,o)=>{if(o.method==='DELETE')throw Error('資料仍在處理');return me;});await x.account.load();x.account.askDeleteMonth('2026-05');await x.account.confirmDeletion();assert.equal(x.account.state().profile.months.length,2);
 const demo=setup(()=>({...me,is_demo:true}));await demo.account.load();await demo.account.rename('A');await demo.account.changePassword('old','new-password');demo.account.askDeleteMonth('2026-05');demo.account.askDeleteAccount();await demo.account.confirmDeletion('p');assert.equal(demo.calls.length,1);assert.equal(demo.account.state().confirmation,null);
 await demo.account.logout();assert.equal(demo.session.get(),null);
});
test('failed logout retains session and successful logout clears it',async()=>{
 let fail=true;const x=setup(()=>{if(fail)throw Error('離線');return null;});await x.account.logout();assert(x.session.get());assert.equal(x.ended.length,0);
 fail=false;await x.account.logout();assert.equal(x.session.get(),null);assert.deepEqual(x.ended,['logout']);
});
test('reset and identity change ignore late account mutation responses',async()=>{
 let resolve;const x=setup((p,o)=>o.method==='PATCH'?new Promise(r=>resolve=r):me);await x.account.load();const request=x.account.rename('old user name');
 x.account.reset();x.session.set({access_token:'other',expires_in:3600},'Other');resolve({...me,display_name:'old user name'});await request;
 assert.equal(x.session.get().label,'Other');assert.equal(x.account.state().profile,null);assert.equal(x.changed.length,0);
});
test('invalid inputs never call mutations and duplicate submits send only one request',async()=>{
 let resolve;const x=setup((p,o)=>o.method==='PATCH'?new Promise(r=>resolve=r):me);await x.account.load();
 await x.account.rename('');await x.account.rename('a'.repeat(21));await x.account.changePassword('old','short');x.account.askDeleteMonth('../me');assert.equal(x.calls.length,1);
 const a=x.account.rename('New');await x.account.rename('Other');assert.equal(x.calls.length,2);resolve({...me,display_name:'New'});await a;
});

test('batch deletion requires confirmation, validates every month and deduplicates selections',async()=>{
 const x=setup();await x.account.load();
 x.account.askDeleteMonths([]);x.account.askDeleteMonths(['2026-05','../me']);assert.equal(x.account.state().confirmation,null);
 x.account.askDeleteMonths(['2026-05','2026-05','2026-06']);assert.equal(x.calls.length,1);
 x.account.cancelConfirmation();await x.account.confirmDeletion();assert.equal(x.calls.length,1);
 x.account.askDeleteMonths(['2026-05','2026-06']);await x.account.confirmDeletion();
 assert.deepEqual(x.calls.slice(1).map(c=>c[0]),['/me/months/2026-05','/me/months/2026-06']);
 assert.deepEqual(x.account.state().profile.months,[]);assert.deepEqual(x.changed,['month']);
});
test('batch deletion retains failures, treats absent months as removed, and invalidates once',async()=>{
 const x=setup((p,o)=>{if(o.method==='DELETE')throw Object.assign(Error('月份仍在處理'),{status:p.endsWith('05')?404:409,detail:p.endsWith('05')?'month_not_found':'job_in_progress'});return me;});
 await x.account.load();x.account.askDeleteMonths(me.months);await x.account.confirmDeletion();
 assert.deepEqual(x.account.state().profile.months,['2026-06']);assert.equal(x.account.state().deletion.failed[0].month,'2026-06');
 assert.deepEqual(x.changed,['month']);assert.equal(x.account.state().confirmation,null);assert.equal(x.account.state().busy,false);
 x.account.askDeleteMonth('2026-06');await x.account.confirmDeletion();assert.equal(x.account.state().deletion,null,'single deletion does not reuse old batch progress');
});
test('batch deletion is sequential, cannot duplicate, and reset stops remaining requests',async()=>{
 let resolve;const x=setup((p,o)=>o.method==='DELETE'?new Promise(r=>resolve=r):me);await x.account.load();
 x.account.askDeleteMonths(me.months);const run=x.account.confirmDeletion();await x.account.confirmDeletion();
 assert.equal(x.calls.length,2);assert.equal(x.account.state().deletion.total,2);
 x.account.cancelConfirmation();assert(x.account.state().confirmation);
 x.account.reset();x.session.set({access_token:'other',expires_in:3600},'Other');resolve();await run;
 assert.equal(x.calls.length,2);assert.equal(x.changed.length,0);assert.equal(x.account.state().profile,null);
});
test('demo cannot batch delete and authentication failures stop the batch',async()=>{
 const demo=setup(()=>({...me,is_demo:true}));await demo.account.load();demo.account.askDeleteMonths(me.months);await demo.account.confirmDeletion();assert.equal(demo.calls.length,1);
 const x=setup((p,o)=>{if(o.method==='DELETE')throw Object.assign(Error('請重新登入'),{status:401});return me;});
 await x.account.load();x.account.askDeleteMonths(me.months);await x.account.confirmDeletion();assert.equal(x.calls.length,2);assert.equal(x.account.state().busy,false);
});
