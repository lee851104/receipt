const {test}=require('node:test');
const assert=require('node:assert/strict');
const {createSession}=require('../src/web_v2/api.js');
const {createFlow}=require('../src/web_v2/flow.js');
const {createWorkspace,matchStatus}=require('../src/web_v2/workspace-flow.js');
function setup(handler, options={}){
 const calls=[], waits=[];const session=createSession(null);session.set({access_token:'a',expires_in:3600},'Amy');
 const api={request:async(p,o)=>{calls.push([p,o]);return handler(p,o);}};
 const sleep=async(ms,signal)=>{waits.push(ms);if(signal.aborted)throw new DOMException('Cancelled','AbortError');};
 const work=createWorkspace({api,session,sleep,...options});return {work,calls,waits,session,api,sleep};
}
const pending={name:'虛構茶',category:{name:'飲品',prob:.9},attributes_status:'pending',attributes:null};
test('classification keeps category visible, retries every 2 seconds and stops at ready',async()=>{
 let n=0;const snapshots=[];const x=setup(()=>++n<3?pending:{...pending,attributes_status:'ready',attributes:{sugar:0}});
 const flow=createFlow({...x,onChange:s=>snapshots.push(s.classification)});await flow.classify('虛構茶');
 assert.deepEqual(x.waits,[2000,2000]);assert.equal(n,3);assert.equal(flow.state().classification.status,'ready');
 assert(snapshots.some(s=>s.result===pending && /分析中/.test(s.message)));
});
test('classification retries five times only and asks to check later',async()=>{
 const x=setup(()=>pending);const flow=createFlow(x);await flow.classify('虛構茶');
 assert.equal(x.calls.length,6);assert.deepEqual(x.waits,Array(5).fill(2000));assert.equal(flow.state().classification.message,'稍後再查');
});
test('switching identity during classification delay cancels all future checks',async()=>{
 let waiting;const started=new Promise(r=>waiting=r);const x=setup(()=>pending);
 const flow=createFlow({...x,sleep:(_,signal)=>new Promise((resolve,reject)=>{waiting();signal.addEventListener('abort',()=>reject(new DOMException('cancel','AbortError')));})});
 const call=flow.classify('虛構茶');await started;flow.switchAccount();await call;
 assert.equal(x.calls.length,1);assert.equal(flow.state().classification.result,null);
});
test('upload uses multipart, then follows queued and running through done',async()=>{
 let i=0;const jobs=['queued','running','done'];const x=setup(p=>p==='/invoices'?{job_id:12,month:'2026-05',rows:3}:{job_id:12,status:jobs[i++],done:i,total:3,message:'處理中'});
 await x.work.upload(new File(['csv'],'fictional.csv',{type:'text/csv'}));
 assert(x.calls[0][1].body instanceof FormData);assert.equal(x.calls[0][1].body.get('file').name,'fictional.csv');
 assert.equal(x.calls[0][1].json,undefined);assert.deepEqual(x.waits,[2000,2000]);
 assert.equal(x.work.state().upload.status,'done');assert.equal(x.work.state().upload.month,'2026-05');
});
test('job failure includes server reason and stops polling',async()=>{
 const x=setup(p=>p==='/invoices'?{job_id:1}:{status:'failed',done:1,total:3,message:'模型暫時無法使用'});
 await x.work.upload(new File(['a'],'month.csv'));assert.equal(x.work.state().upload.status,'failed');
 assert.match(x.work.state().upload.message,/模型暫時/);assert.equal(x.calls.length,2);
});
test('oversize files, absent files and demo uploads never call the API',async()=>{
 const x=setup(()=>{throw Error('unexpected');});
 await x.work.upload(null);assert.equal(x.work.state().upload.status,'error');
 await x.work.upload(new File([new Uint8Array(2*1024*1024+1)],'big.csv'));assert.match(x.work.state().upload.message,/2 MB/);
 x.session.set({access_token:'demo',expires_in:60},'Demo',{isDemo:true});
 await x.work.upload(new File(['a'],'month.csv'));assert.match(x.work.state().upload.message,/示範帳號/);assert.equal(x.calls.length,0);
});
test('a lost job response resumes GET rather than uploading the file again',async()=>{
 let fail=true;const x=setup(p=>{if(p==='/invoices')return {job_id:3,month:'2026-05'};if(fail)throw Error('無法連線');return {status:'done',done:1,total:1};});
 await x.work.upload(new File(['a'],'month.csv'));assert.equal(x.work.state().upload.status,'error');
 fail=false;await x.work.resumeUpload();assert.equal(x.work.state().upload.status,'done');
 assert.equal(x.calls.filter(([p])=>p==='/invoices').length,1);
});
test('reset cancels an upload response and never fetches the old job',async()=>{
 let resolve;const x=setup(()=>new Promise(r=>resolve=r));const call=x.work.upload(new File(['a'],'month.csv'));
 x.work.reset();resolve({job_id:7});await call;assert.equal(x.calls.length,1);assert.equal(x.work.state().upload.status,'idle');
});
test('profile preserves empty months, null traits and not-ready count',async()=>{
 const profile={ready:false,months:{},item_count:2,min_items:20,traits:[{id:'sport',value:null}],areas:[]};
 const x=setup(()=>profile);await x.work.loadProfile();assert.equal(x.work.state().profile.data,profile);
 assert.equal(x.work.state().profile.status,'ready');
});
test('missing profile endpoint shows unavailable rather than fabricated data',async()=>{
 const x=setup(()=>{throw Object.assign(Error('Not Found'),{status:404});});await x.work.loadProfile();
 assert.equal(x.work.state().profile.data,null);assert.match(x.work.state().profile.message,/尚未就緒/);
});
test('match API supplies displayed counts, order and percentages; scope is sent verbatim',async()=>{
 const list={ready:true,kind:'opposite',eligible:8,within:6,people:[{user_id:4,display_name:'A',percent:-31,score:-.305}]};
 const x=setup(()=>list);await x.work.loadMatches('opposite','district');
 assert.equal(x.calls[0][0],'/matches?kind=opposite&scope=district');assert.equal(x.work.state().matches.data,list);
 assert.match(matchStatus(list),/6 位/);assert.match(matchStatus(list),/前 5/);
 assert.match(matchStatus({...list,eligible:0,within:0}),/沒有/);
 assert.match(matchStatus({...list,within:0}),/放寬/);
 assert.match(matchStatus({...list,ready:false}),/不足/);
});
test('slow prior filter and reset cannot replace the latest matches or profile',async()=>{
 const resolvers=[];const x=setup(()=>new Promise(r=>resolvers.push(r)));
 const a=x.work.loadMatches('similar','all');const b=x.work.loadMatches('similar','city');
 resolvers[1]({ready:true,people:[],scope:'city'});await b;resolvers[0]({scope:'all'});await a;
 assert.equal(x.work.state().matches.data.scope,'city');
 const c=x.work.loadProfile();x.work.reset();resolvers[2]({months:{private:true}});await c;
 assert.equal(x.work.state().profile.data,null);
});
test('network request retains selected card percentage and refuses inconsistent result',async()=>{
 const card={user_id:9,display_name:'Amy',percent:62};
 const x=setup(()=>({user_id:9,comparable:true,percent:61,network:{}}));await x.work.loadNetwork(card);
 assert.equal(x.work.state().network.status,'error');assert.match(x.work.state().network.message,/重新查詢/);
});

test('upload completion invalidates all pre-upload reads even if they ignore abort',async()=>{
 const reads={};const x=setup((path,options)=>{
  if(path==='/invoices')return {job_id:2};
  if(path==='/jobs/2')return {status:'done',done:1,total:1};
  return new Promise(resolve=>reads[path]={resolve,signal:options.signal});
 });
 const matches=x.work.loadMatches();const network=x.work.loadNetwork({user_id:9,percent:62});
 const profile=x.work.loadProfile();
 await x.work.upload(new File(['csv'],'month.csv'));
 for(const key of ['profile','matches','network'])assert.equal(x.work.state()[key].status,'idle');
 for(const read of Object.values(reads)){assert.equal(read.signal.aborted,true);read.resolve({comparable:true,percent:62,months:{old:true}});}
 await Promise.all([profile,matches,network]);
 for(const key of ['profile','matches','network'])assert.equal(x.work.state()[key].data,null);
});

test('profile recomputation polls every two seconds and clears stale matches until complete',async()=>{
 let n=0;const seen=[];
 const x=setup(p=>p==='/me/profile'?{ready:true,recomputing:++n<3,item_count:n,months:{}}:{ready:true,people:[]},{onChange:s=>seen.push(s)});
 await x.work.loadMatches();await x.work.loadProfile();
 assert.deepEqual(x.waits,[2000,2000]);assert.equal(n,3);
 assert(seen.some(s=>s.profile.status==='recomputing'&&s.matches.data===null));
 assert.equal(x.work.state().profile.status,'ready');assert.equal(x.work.state().profile.data.item_count,3);
});
test('reset during recomputation cancels polling and a delayed response cannot restore old data',async()=>{
 let release,started;const waiting=new Promise(r=>started=r);
 const x=setup(()=>({ready:true,recomputing:true}),{sleep:(_,signal)=>new Promise(r=>{release=r;started();})});
 const call=x.work.loadProfile();await waiting;x.work.reset();release();await call;
 assert.equal(x.calls.length,1);assert.equal(x.work.state().profile.data,null);
});
test('recomputation invalidates in-flight matches and failures allow manual retry',async()=>{
 let finish,fail=false;
 const x=setup(p=>{if(p.startsWith('/matches'))return new Promise(r=>finish=r);if(fail)throw Error('offline');return {ready:true,recomputing:true};},{sleep:async()=>{fail=true;}});
 const match=x.work.loadMatches();await x.work.loadProfile();finish({people:[{user_id:2}]});await match;
 assert.equal(x.work.state().matches.data,null);assert.equal(x.work.state().profile.status,'error');
});

test('known recomputation blocks stale match and graph queries until the new profile arrives',async()=>{
 let release,started,n=0;const waiting=new Promise(r=>started=r);
 const x=setup(()=>({ready:true,recomputing:++n===1}),{sleep:()=>new Promise(r=>{release=r;started();})});
 const call=x.work.loadProfile();await waiting;
 await x.work.loadMatches();await x.work.loadNetwork({user_id:7,percent:82});
 assert.equal(x.calls.length,1);
 release();await call;await x.work.loadMatches();assert.equal(x.calls.length,3);
});
