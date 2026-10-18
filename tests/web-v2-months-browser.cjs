const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {go,openReport}=require('./web-v2-navigation.cjs');
const fixture=require('./web-v2-fixtures.cjs');
const base=process.env.RECEIPT_TEST_URL;
if(!base)throw Error('Use tests/run_web_v2_live.py with its isolated database.');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
 const page=await browser.newPage({viewport:{width:1366,height:768}});page.setDefaultTimeout(6000);
 let months=['2026-05','2026-06'],demo=false,failLoad=false,failJune=true,unauthorized=false,releaseDelete=null,releaseLoad=null,recomputing=0,matchCalls=0;
 const deletes=[],errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname,method=route.request().method();
  let status=200,json={};
  if(path.endsWith('/health'))json={demo_mode:true};
  else if(path.endsWith('/demo-users'))json=[{user_id:1,display_name:'虛構唯讀示範'}];
  else if(path.endsWith('/demo-login')){demo=true;json={access_token:'fictional-demo',expires_in:3600};}
  else if(path.endsWith('/login')){demo=false;json={access_token:'fictional',expires_in:3600};}
  else if(method==='DELETE'){
   const month=path.split('/').at(-1);deletes.push(month);
   if(releaseDelete)await releaseDelete.promise;
   if(unauthorized){status=401;json={detail:'not_authenticated'};}
   else if(month==='2026-06'&&failJune){status=409;json={detail:'job_in_progress'};}
   else{months=months.filter(m=>m!==month);recomputing=1;status=204;}
  }else if(path.endsWith('/me')){
   if(releaseLoad)await releaseLoad.promise;
   if(failLoad){status=503;json={detail:'internal_error'};}
   else json={username:'fictional',display_name:'虛構使用者',is_demo:demo,months};
  }else if(path.endsWith('/me/profile')){
   if(recomputing-->0)json={recomputing:true};
   else json={...fixture.profile,months:Object.fromEntries(Object.entries(fixture.profile.months).filter(([m])=>months.includes(m)))};
  }else if(path.endsWith('/explain'))json=fixture.explanation;
  else{matchCalls++;json=months.length?fixture.matches:{...fixture.matches,ready:false,people:[],within:0,eligible:0};}
  await route.fulfill(status===204?{status,body:''}:{status,json});
 });
 function gate(){let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};}
 async function open(){await page.locator('#settings-toggle').click();await page.locator('#settings-options [data-months-open]').click();await page.locator('#months-content').waitFor();}
 try{
  await page.goto(base+'/web/');await page.locator('#login-username').fill('fictional');await page.locator('#login-password').fill('fictional-password');await page.locator('#login-submit').click();await page.locator('#home-panel').waitFor();
  await go(page,'matches');await page.locator('.match-card').first().waitFor();
  await go(page,'profile');await openReport(page);
  releaseLoad=gate();await page.locator('#settings-toggle').click();await page.locator('#settings-options [data-months-open]').click();
  await page.locator('#months-status.status-loading').waitFor();assert(await page.locator('#months-delete').isDisabled());releaseLoad.resolve();releaseLoad=null;
  await page.locator('#months-content').waitFor();assert.equal(await page.locator('#months-list input').count(),2);
  await page.getByRole('checkbox',{name:'選取 2026-05',exact:true}).check();assert(await page.locator('#months-all').evaluate(n=>n.indeterminate));
  await page.locator('#months-all').check();assert.equal(await page.locator('#months-list input:checked').count(),2);
  await page.locator('#months-delete').click();await page.locator('#account-confirm').waitFor();assert.match(await page.locator('#confirm-description').textContent(),/2026-05、2026-06/);
  await page.locator('#confirm-cancel').press('Escape');assert.deepEqual(deletes,[]);assert.equal(await page.locator('#months-list input:checked').count(),2);
  await page.screenshot({path:'runtime/role4-months-desktop.png'});
  releaseDelete=gate();await page.locator('#months-delete').click();await page.locator('#confirm-submit').click();
  await page.locator('#confirm-progress.status-loading').waitFor();assert(await page.locator('#confirm-cancel').isDisabled());assert(await page.locator('#confirm-submit').isDisabled());
  await page.locator('#account-confirm').press('Escape');assert(await page.locator('#account-confirm').isVisible());
  releaseDelete.resolve();releaseDelete=null;
  await page.locator('#account-confirm').waitFor({state:'hidden'});await page.locator('.month-failure').filter({hasText:'仍在處理'}).waitFor();
  assert.deepEqual(deletes,['2026-05','2026-06']);assert.equal(await page.locator('#months-list input').count(),1);assert.equal(await page.locator('#months-list input:checked').count(),1);
  await page.locator('#months-close').click();await openReport(page);
  assert.equal(await page.frameLocator('#report-frame').locator('#insights-month option').count(),1);
  const before=matchCalls;await go(page,'matches');await page.locator('.match-card').first().waitFor();assert(matchCalls>before,'matches refreshed after partial deletion');
  await open();await page.locator('#months-delete-all').click();await page.locator('#confirm-cancel').click();assert.equal(deletes.length,2);
  failJune=false;await page.locator('#months-delete-all').click();await page.locator('#confirm-submit').click();await page.locator('#months-empty').waitFor();assert(await page.locator('#months-dialog').evaluate(n=>n.contains(document.activeElement)),'focus remains in manager after delete all');assert(await page.locator('#months-delete-all').isDisabled());
  await page.locator('#months-close').click();await page.locator('#match-status').filter({hasText:'資料還不足'}).waitFor();assert.equal(await page.locator('.match-card').count(),0);
  await go(page,'profile');await page.locator('#report-empty').waitFor();assert(await page.locator('#report-frame').isHidden());
  // Load errors expose retry; many rows fit desktop/mobile with only list scrolling.
  failLoad=true;await page.locator('#settings-toggle').click();await page.locator('#settings-options [data-months-open]').click();await page.locator('#months-error').waitFor();assert(await page.locator('#months-content').isHidden());
  failLoad=false;months=Array.from({length:24},(_,i)=>(2025+Math.floor(i/12))+'-'+String(i%12+1).padStart(2,'0'));
  await page.locator('#months-refresh').click();await page.locator('#months-content').waitFor();
  for(const size of [{width:1366,height:768},{width:390,height:844},{width:320,height:568}]){
   await page.setViewportSize(size);
   assert(await page.locator('#months-dialog').evaluate(n=>{const r=n.getBoundingClientRect();return r.left>=0&&r.top>=0&&r.right<=innerWidth+1&&r.bottom<=innerHeight+1&&n.scrollWidth<=n.clientWidth+1&&n.scrollHeight<=n.clientHeight+1;}),'dialog fits '+JSON.stringify(size));
   assert(await page.locator('#months-list').evaluate(n=>n.scrollHeight>n.clientHeight),'long list scrolls');
   const bounds=await page.locator('#months-delete-all').boundingBox();assert(bounds.y+bounds.height<=size.height);
   await page.screenshot({path:'runtime/role4-months-'+size.width+'.png'});
  }
  await page.locator('#months-delete-all').click();assert(await page.locator('#account-confirm').evaluate(n=>{const r=n.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight+1;}),'long confirmation fits mobile');await page.locator('#confirm-cancel').click();
  await page.locator('#months-close').press('Escape');assert(await page.locator('#settings-toggle').evaluate(n=>document.activeElement===n));
  await go(page,'upload');await page.locator('#upload-panel [data-months-open]').click();await page.locator('#months-content').waitFor();await page.locator('#months-close').click();
  assert(await page.locator('#upload-panel [data-months-open]').evaluate(n=>document.activeElement===n));
  // An expired session closes both modal layers and stops remaining deletes.
  months=['2026-05','2026-06'];unauthorized=true;await open();await page.locator('#months-delete-all').click();const count=deletes.length;await page.locator('#confirm-submit').click();await page.locator('#auth-view').waitFor();
  assert.equal(deletes.length,count+1);assert.equal(await page.locator('#months-dialog').evaluate(n=>n.open),false);assert.equal(await page.locator('#account-confirm').evaluate(n=>n.open),false);
  await page.locator('#demo-user').selectOption('1');await page.locator('#demo-submit').click();await page.locator('#home-panel').waitFor();await open();
  assert(await page.locator('#months-demo').isVisible());assert(await page.locator('#months-all').isDisabled());assert(await page.locator('#months-delete-all').isDisabled());
  assert.deepEqual(errors,[]);console.log('MONTHS PASS: loading/retry, confirmation/cancel, progress, partial failures, refreshed report/matches, delete all/empty, responsive scrolling/focus, expired session and demo readonly.');
 }finally{releaseDelete?.resolve();releaseLoad?.resolve();await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
