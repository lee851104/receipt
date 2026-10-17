/* Docker delivery acceptance: real HTTP, synthetic inputs, no mocked API. */
'use strict';
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {go,openCalculation}=require('./web-v2-navigation.cjs');
const origin=process.env.RECEIPT_TEST_URL;
if(process.env.RECEIPT_ISOLATED_DELIVERY!=='1'||!/^http:\/\/127\.0\.0\.1:\d+$/.test(origin||''))throw Error('Use an isolated loopback delivery container.');
const suffix=process.env.RECEIPT_DELIVERY_ID;
if(!/^[a-z0-9_]{1,16}$/.test(suffix||''))throw Error('Set a unique delivery id.');
const names=['delivery_'+suffix,'peer_'+suffix],password='Synthetic-delivery-2026';
async function api(path,{method='GET',token,json,body}={}){
 const r=await fetch(origin+'/api'+path,{method,headers:{...(token?{Authorization:'Bearer '+token}:{}),...(json?{'Content-Type':'application/json'}:{})},body:json?JSON.stringify(json):body});
 return {status:r.status,data:r.status===204?null:await r.json()};
}
async function until(read,test){
 for(let i=0;i<150;i++){const v=await read();if(test(v))return v;await new Promise(r=>setTimeout(r,100));}
 throw Error('Timed out waiting for worker');
}
function csv(){
 const header='發票日期,發票狀態,發票號碼,賣方名稱,賣方地址,消費明細_品名,消費明細_數量,消費明細_金額';
 const items=['虛構奶茶','虛構餅乾','虛構衛生紙','虛構雞蛋'];
 return '\ufeff'+header+'\r\n'+Array.from({length:40},(_,i)=>['202606'+String(i%28+1).padStart(2,'0'),'開立已確認','SYN-'+i,'虛構測試店','臺北市大安區測試路1號',items[i%4],1,60+i%7*10].join(',')).join('\r\n');
}
(async()=>{
 const h=await api('/health');assert.equal(h.status,200);assert.equal(h.data.demo_mode,true);assert.equal(h.data.gpu_mode,false);assert.equal(h.data.models.category,'fake');assert.equal(h.data.models.attributes,'fake');
 const demos=await api('/auth/demo-users');assert(demos.data.length>0);
 const demo=await api('/auth/demo-login',{method:'POST',json:{user_id:demos.data[0].user_id}});
 assert.equal(demo.status,200);
 const demoProfile=await api('/me/profile',{token:demo.data.access_token});
 // Record the current seed limitation, do not invent a populated demo profile.
 const seedReady=demoProfile.data.ready;
 const identities=[];
 for(const username of names){
  if(process.argv.includes('--prepare'))assert.equal((await api('/auth/register',{method:'POST',json:{username,password,display_name:'虛構交付驗收'}})).status,201);
  const login=await api('/auth/login',{method:'POST',body:new URLSearchParams({username,password})});assert.equal(login.status,200);
  const token=login.data.access_token;
  if(process.argv.includes('--prepare')){
   const form=new FormData();form.append('file',new Blob([csv()],{type:'text/csv'}),'synthetic.csv');
   const up=await api('/invoices',{method:'POST',token,body:form});assert.equal(up.status,202);
   const job=await until(()=>api('/jobs/'+up.data.job_id,{token}),x=>['done','failed'].includes(x.data.status));assert.equal(job.data.status,'done');
  }
  const profile=await until(()=>api('/me/profile',{token}),x=>!x.data.recomputing);
  assert(profile.data.ready);assert.equal(profile.data.item_count,40);assert.equal(Object.keys(profile.data.months).length,1);
  identities.push({token,id:profile.data.user_id});
 }
 const result=await api('/matches?kind=similar&scope=all',{token:identities[0].token});assert.equal(result.status,200);
 const peer=result.data.people.find(p=>p.user_id===identities[1].id);assert(peer);
 const explain=await api('/matches/'+peer.user_id+'/explain',{token:identities[0].token});assert.equal(explain.status,200);assert.equal(explain.data.percent,peer.percent);assert.equal(explain.data.cells.length,18);
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
 const errors=[];const page=await browser.newPage({viewport:{width:1366,height:768}});page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(origin+'/web/');await page.locator('#login-username').fill(names[0]);await page.locator('#login-password').fill(password);await page.locator('#login-form button').click();
  await page.locator('#home-panel').waitFor();assert.equal(await page.locator('#home-panel button').count(),2);
  await go(page,'profile');const report=page.frameLocator('#report-frame');await report.locator('#total').waitFor();assert.equal(await report.locator('#insights-month option').count(),1);
  await go(page,'matches');await page.locator('.match-card').first().click();
  const graph=page.frameLocator('#network-frame');await graph.locator('.t-score-number').waitFor();await graph.locator('.comparison-overview').waitFor();
  assert.equal(await page.locator('#explain-details').getAttribute('open'),null);
  await openCalculation(page);assert.equal(await page.locator('#explain-panel tbody tr').count(),18);
  assert.equal((await graph.locator('.t-score-number').textContent()).replace('+','').replace('%',''),String(peer.percent));
  await page.locator('#match-back').click();await page.locator('#match-browse').waitFor();
  await go(page,'settings');await page.locator('#account-content').waitFor();
  await page.locator('#logout-submit').click();await page.locator('#auth-view').waitFor();
  await page.locator('#demo-user').selectOption(String(demos.data[0].user_id));await page.locator('#demo-submit').click();await page.locator('#home-panel').waitFor();
  await go(page,'profile');await page.locator('#report-empty').waitFor();
  assert.deepEqual(errors,[]);
 }finally{await browser.close();}
 const output={phase:process.argv.includes('--prepare')?'prepare':'after-recreate',http:'real',models:h.data.models,gpu:false,demo_users:demos.data.length,seed_profile_ready:seedReady,synthetic_users:2,items_per_user:40,percent:peer.percent,cells:18,browser:'pass'};
 fs.mkdirSync('runtime',{recursive:true});fs.writeFileSync('runtime/role4-delivery-'+output.phase+'.json',JSON.stringify(output,null,2));console.log(JSON.stringify(output));
})().catch(e=>{console.error(e);process.exitCode=1;});
