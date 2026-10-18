const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {go,openReport}=require('./web-v2-navigation.cjs');
const fixture=require('./web-v2-fixtures.cjs');
const base=process.env.RECEIPT_TEST_URL;
if(!base)throw Error('Use tests/run_web_v2_live.py to provide RECEIPT_TEST_URL.');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
 const page=await browser.newPage({viewport:{width:1366,height:768}});page.setDefaultTimeout(5000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const gates=new Map();
 function hold(key){let release;const promise=new Promise(r=>release=r);gates.set(key,promise);return ()=>{gates.delete(key);release();};}
 let failProfile=false,failNetwork=false,failReport=false,recomputing=false,jobState='queued',jobTotal=20,demoMode=false;
 let account={username:'fictional',display_name:'虛構測試',is_demo:false,months:['2026-05']};
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname,method=route.request().method();
  await gates.get(path);
  let status=200,body=path.endsWith('/health')?{demo_mode:demoMode,models:{category:'fake',attributes:'fake'}}:
   path.endsWith('/demo-users')?[{user_id:1,display_name:'虛構示範'}]:(path.endsWith('/login')||path.endsWith('/demo-login')||path.endsWith('/password'))?{access_token:'fictional-only',expires_in:3600}:
   path.endsWith('/invoices')?{job_id:42,month:'2026-05',rows:20}:path.endsWith('/jobs/42')?{status:jobState,total:jobState==='queued'?0:jobTotal,done:jobState==='done'?jobTotal:5}:path.endsWith('/me/profile')?(recomputing?{recomputing:true}:fixture.profile):path.endsWith('/explain')?fixture.explanation:
   path.endsWith('/me')?account:fixture.matches;
  if(path.endsWith('/me/profile')&&failProfile){status=503;body={detail:'internal_error'};}
  if(path.endsWith('/explain')&&failNetwork){status=503;body={detail:'internal_error'};}
  if(path.endsWith('/me')&&method==='PATCH'){account={...account,display_name:route.request().postDataJSON().display_name};body=account;}
  await route.fulfill({status,json:body});
 });
 await page.route('**/report-bootstrap.js?*',async route=>{await gates.get('report-script');await route.continue();});
 await page.route('**/report-overview.js?*',async route=>{if(failReport)await route.abort();else await route.continue();});
 await page.route('**/network-view.js?*',async route=>{await gates.get('network-script');await route.continue();});
 try{
  const health=hold('/api/health');await page.goto(base+'/web/');
  assert.match(await page.locator('#auth-status').textContent(),/連線/);health();
  await page.locator('#register-tab').click();const register=hold('/api/auth/register');
  await page.locator('#register-username').fill('fictional_new');await page.locator('#register-password').fill('fictional-password');await page.locator('#register-submit').click();
  assert.equal(await page.locator('#register-submit').getAttribute('aria-busy'),'true');register();await page.locator('#auth-notice').waitFor();
  const login=hold('/api/auth/login');await page.locator('#login-username').fill('fictional');await page.locator('#login-password').fill('fictional-password');await page.locator('#login-form button').click();
  assert.equal(await page.locator('#login-form button').getAttribute('aria-busy'),'true');assert(await page.locator('#login-form button').isDisabled());login();await page.locator('#home-panel').waitFor();
  let profile=hold('/api/me/profile');await go(page,'profile');
  await page.locator('#profile-message.status-loading').waitFor();assert.equal(await page.locator('#profile-content').getAttribute('aria-busy'),'true');
  const report=hold('report-script');profile();await page.locator('#profile-message').filter({hasText:'準備月報圖表'}).waitFor();
  await page.screenshot({path:'runtime/role4-loading-report.png'});
  await page.setViewportSize({width:390,height:844});assert.equal(await page.locator('body').evaluate(n=>n.scrollWidth>innerWidth),false);await page.screenshot({path:'runtime/role4-loading-mobile.png'});await page.setViewportSize({width:1366,height:768});report();await openReport(page);await page.locator('#profile-feedback').waitFor({state:'hidden'});
  await go(page,'matches');await page.locator('.match-card').first().waitFor();
  let matches=hold('/api/matches');await page.locator('#refresh-matches').click();await page.locator('#match-loading').waitFor();assert(await page.locator('#refresh-matches').isDisabled());matches();await page.locator('#match-loading').waitFor({state:'hidden'});
  let explain=hold('/api/matches/7/explain');await page.locator('.match-card').first().click();await page.locator('#network-status.status-loading').waitFor();
  const net=hold('network-script');explain();await page.locator('#network-status').filter({hasText:'繪製品味連線'}).waitFor();await page.screenshot({path:'runtime/role4-loading-network.png'});
  net();await page.frameLocator('#network-frame').locator('.t-score-number').waitFor();await page.locator('#network-feedback').waitFor({state:'hidden'});
  await go(page,'settings');await page.locator('#account-content').waitFor();
  const rename=hold('/api/me');await page.locator('#account-name').fill('虛構新名稱');await page.locator('#account-name-submit').click();await page.locator('#account-loading.status-loading').waitFor();assert.equal(await page.locator('#account-name-submit').getAttribute('aria-busy'),'true');
  rename();await page.locator('#account-notice').filter({hasText:'已更新'}).waitFor();
  failProfile=true;await go(page,'profile');await page.locator('#profile-retry').waitFor();assert.equal(await page.locator('#profile-message').getAttribute('class'),'');
  failProfile=false;await page.locator('#profile-retry').click();await openReport(page);
  failNetwork=true;await go(page,'matches');await page.locator('.match-card').first().click();await page.locator('#network-retry').waitFor();
  failNetwork=false;await page.locator('#network-retry').click();await page.locator('.match-card').first().waitFor();await page.locator('.match-card').first().click();await page.frameLocator('#network-frame').locator('.t-score-number').waitFor();
  // A missing frame script times out with a usable retry; its late ready cannot clear that error.
  await page.locator('#match-back').click();const lateFrame=hold('network-script');await page.locator('.match-card').first().click();
  await page.locator('#network-retry').waitFor({timeout:25000});assert.match(await page.locator('#network-status').textContent(),/載入時間較長/);lateFrame();
  await page.waitForTimeout(150);assert(await page.locator('#network-retry').isVisible());await page.locator('#network-retry').click();await page.locator('.match-card').first().click();await page.frameLocator('#network-frame').locator('.t-score-number').waitFor();
  // Leaving a slow result must not reopen it after the response arrives.
  await page.locator('#match-back').click();explain=hold('/api/matches/7/explain');await page.locator('.match-card').first().click();await page.locator('#network-status.status-loading').waitFor();
  await page.locator('[data-workspace="home"]').click();explain();await page.waitForTimeout(150);assert.equal(new URL(page.url()).hash,'#home');
  await go(page,'profile');await openReport(page);
  await page.emulateMedia({reducedMotion:'reduce'});profile=hold('/api/me/profile');await page.locator('#settings-toggle').click();await page.locator('#refresh-profile').click();await go(page,'profile');await page.locator('#profile-message.status-loading').waitFor();
  assert.equal(await page.locator('#profile-message').evaluate(n=>getComputedStyle(n,'::before').animationName),'none');profile();await openReport(page);

  // A failed report script surfaces a retry, then recovers without a reload.
  failReport=true;await page.locator('#settings-toggle').click();await page.locator('#refresh-profile').click();await page.locator('#profile-retry').waitFor();
  failReport=false;await page.locator('#profile-retry').click();await openReport(page);
  // Recalculation is visibly distinct from an empty report.
  recomputing=true;await page.locator('#settings-toggle').click();await page.locator('#refresh-profile').click();await page.locator('#profile-message').filter({hasText:'更新品味資料'}).waitFor();
  recomputing=false;await openReport(page);
  // Upload uses indeterminate progress until the backend returns a real total.
  await go(page,'upload');const sending=hold('/api/invoices'),job=hold('/api/jobs/42');
  await page.locator('#invoice-file').setInputFiles({name:'fictional.csv',mimeType:'text/csv',buffer:Buffer.from('fictional,test')});
  await page.locator('#upload-submit').click();assert.equal(await page.locator('#upload-submit').getAttribute('aria-busy'),'true');sending();
  await page.locator('#upload-state').filter({hasText:'排隊中'}).waitFor();assert.equal(await page.locator('#upload-progress').getAttribute('value'),null);assert.match(await page.locator('#upload-count').textContent(),/確認待分析筆數/);
  await page.locator('[data-workspace="home"]').click();await page.locator('#upload-background').waitFor();
  await page.setViewportSize({width:320,height:568});assert.equal(await page.locator('body').evaluate(n=>n.scrollWidth>innerWidth),false,'background progress fits mobile header');
  assert(await page.locator('.brand').evaluate(n=>n.getBoundingClientRect().height<=n.closest('header').getBoundingClientRect().height),'brand remains within header');
  await page.screenshot({path:'runtime/role4-upload-background-mobile.png'});await page.locator('#upload-background').click();await page.setViewportSize({width:1366,height:768});
  jobState='running';job();await page.locator('#upload-state').filter({hasText:'分析中'}).waitFor();assert.equal(await page.locator('#upload-progress').evaluate(n=>n.value),5);
  await go(page,'home');jobState='done';await page.locator('#upload-state').filter({hasText:'處理完成'}).waitFor({state:'attached'});assert.equal(await page.locator('#open-profile').getAttribute('hidden'),null);assert.equal(await page.locator('#upload-submit').getAttribute('aria-busy'),'false');
  await page.locator('#upload-background').filter({hasText:'分析完成'}).waitFor();await page.locator('#upload-background').click();await openReport(page);assert(await page.locator('#upload-background').isHidden());
  jobTotal=0;await go(page,'upload');await page.locator('#invoice-file').setInputFiles({name:'fictional-empty.csv',mimeType:'text/csv',buffer:Buffer.from('fictional,test')});await page.locator('#upload-submit').click();
  await page.locator('#upload-count').filter({hasText:'沒有需要分析的品項'}).waitFor();assert(await page.locator('#upload-progress').isHidden());
  await go(page,'settings');await page.locator('#account-content').waitFor();
  const password=hold('/api/me/password');await page.locator('#current-password').fill('fictional-password');await page.locator('#new-password').fill('fictional-next-password');await page.locator('#password-submit').click();
  assert.equal(await page.locator('#password-submit').getAttribute('aria-busy'),'true');password();await page.locator('#account-notice').filter({hasText:'密碼已更新'}).waitFor();
  const deletion=hold('/api/me/months/2026-05');await page.getByRole('button',{name:'刪除 2026-05',exact:true}).click();await page.locator('#confirm-submit').click();await page.locator('#confirm-progress.status-loading').waitFor();assert(await page.locator('#confirm-submit').isDisabled());
  deletion();await page.locator('#account-confirm').waitFor({state:'hidden'});
  await go(page,'settings');const logout=hold('/api/auth/logout');await page.locator('#logout-submit').click();assert.equal(await page.locator('#logout-submit').getAttribute('aria-busy'),'true');logout();await page.locator('#auth-view').waitFor();
  demoMode=true;await page.reload();await page.locator('#demo-user').selectOption('1');const demo=hold('/api/auth/demo-login');await page.locator('#demo-submit').click();assert.equal(await page.locator('#demo-submit').getAttribute('aria-busy'),'true');demo();await page.locator('#home-panel').waitFor();
  assert.deepEqual(errors,[]);console.log('FEEDBACK PASS: service/auth/API/frame loading, skeleton, duplicate prevention, account operations, errors/retry, recompute, upload progress/background, leave-during-load, reduced motion.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
