/* Optional browser integration: run with Playwright available; API server on 127.0.0.1:8001. All data is fictional. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');const fs=require('node:fs');
const fixture=require('./web-v2-fixtures.cjs');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const origin=process.env.RECEIPT_TEST_URL||'http://127.0.0.1:8001';
 const csv='\ufeff發票日期,發票狀態,發票號碼,賣方名稱,賣方地址,消費明細_品名,消費明細_數量,消費明細_金額\r\n20260502,開立已確認,TEST-1,虛構店,臺北市大安區測試路1號,鮮奶茶,1,60\r\n20260503,開立已確認,TEST-2,虛構店,臺北市大安區測試路1號,衛生紙,1,100\r\n,,,匯出摘要\r\n';
 const uploadFile=()=>page.locator('#invoice-file').setInputFiles({name:'fictional.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});
 const go=pageName=>page.locator('[data-workspace="'+pageName+'"]').click();
 fs.mkdirSync('runtime',{recursive:true});
 try{
  await page.goto(origin+'/web/');await page.locator('#demo-panel').waitFor({state:'visible'});
  await page.locator('#register-tab').click();const username='week2qa_'+Date.now();
  await page.locator('#register-username').fill(username);await page.locator('#register-password').fill('Browser-check-2026');await page.locator('#register-form button').click();
  await page.locator('#auth-notice').waitFor({state:'visible'});await page.locator('#login-password').fill('Browser-check-2026');await page.locator('#login-form button').click();await page.locator('#workspace-view').waitFor({state:'visible'});
  await go('upload');await uploadFile();await page.locator('#upload-submit').click();
  await page.getByRole('heading',{name:'處理完成',exact:true}).waitFor();assert.match(await page.locator('#upload-count').textContent(),/2 \/ 2/);
  await page.screenshot({path:'runtime/role4-upload-desktop.png',fullPage:true});
  await page.locator('#open-profile').click();await page.locator('#profile-content').waitFor();assert.equal(await page.locator('.trait-value').count(),18);
  await go('classify');await page.locator('#item-name').fill('虛構新品 '+Date.now());await page.locator('#classify-form button').click();
  await page.getByText('分析完成',{exact:true}).waitFor();assert.equal(await page.locator('#attribute-list .attribute-row').count(),23);
  console.log('LIVE PASS: registration, upload -> done, real profile, classification ready with fake backend.');
  // Error screens use controlled API responses, never private invoice data.
  await go('upload');
  for(const failure of [
   {status:400,json:{detail:'invalid_csv',message:'缺少發票日期欄位'},text:'發票檔案格式不符。缺少發票日期欄位'},
   {status:413,json:{detail:'file_too_large'},text:'檔案太大，請改用較小的 CSV。'}
  ]){
   await page.route('**/api/invoices',r=>r.fulfill({status:failure.status,json:failure.json}));
   await uploadFile();await page.locator('#upload-submit').click();
   await page.locator('#upload-message').filter({hasText:failure.text}).waitFor();
   assert(await page.locator('#upload-submit').isEnabled());await page.unroute('**/api/invoices');
  }
  await page.route('**/api/invoices',r=>r.fulfill({status:202,json:{job_id:999999,month:'2026-05',rows:2}}));
  await page.route('**/api/jobs/999999',r=>r.fulfill({json:{status:'failed',done:1,total:2,message:'模型暫時無法使用'}}));
  await uploadFile();await page.locator('#upload-submit').click();
  await page.getByRole('heading',{name:'處理失敗',exact:true}).waitFor();
  assert.equal(await page.locator('#upload-message').textContent(),'模型暫時無法使用');
  await page.unroute('**/api/invoices');await page.unroute('**/api/jobs/999999');
  console.log('ERROR PASS: invalid CSV detail, size rejection and failed job are visible and allow retry.');
  // Fixtures cover deterministic display/error cases; live API coverage is in web-v2-live-browser.cjs.
  let profile=structuredClone(fixture.profile);profile.months['2026-05'].rows[0].invoice='<img src=x onerror="parent.__xss=1">';
  await page.route('**/api/me/profile',r=>r.fulfill({json:profile}));
  await page.route('**/api/matches?*',r=>{const q=new URL(r.request().url()).searchParams;const district=q.get('scope')==='district';return r.fulfill({json:{...fixture.matches,kind:q.get('kind'),scope:q.get('scope'),within:district?0:6,people:district?[]:fixture.matches.people}});});
  await page.route('**/api/matches/7/explain',r=>r.fulfill({json:fixture.explanation}));
  await go('profile');await page.locator('#refresh-profile').click();
  await page.locator('#profile-content').waitFor({state:'visible'});assert.equal(await page.locator('.trait-value').count(),18);
  const report=page.frameLocator('#report-frame');await report.locator('#total').filter({hasText:'80'}).waitFor();
  await report.locator('#insights-month').selectOption('2026-05');await report.locator('#total').filter({hasText:'160'}).waitFor();
  assert.equal(await report.locator('#audit-rows img').count(),0);assert.equal(await page.evaluate(()=>window.__xss),undefined);
  await page.screenshot({path:'runtime/role4-profile-desktop.png',fullPage:true});
  await go('matches');await page.locator('.match-card').waitFor();assert.match(await page.locator('#match-status').textContent(),/6 位/);
  await page.locator('#match-scope').selectOption('district');await page.getByText('這個距離內沒有符合條件的人，試試放寬距離。',{exact:true}).waitFor();assert.equal(await page.locator('.match-card').count(),0);
  await page.locator('#match-scope').selectOption('all');await page.locator('.match-card').click();
  const graph=page.frameLocator('#network-frame');await graph.locator('#network .t-hit').first().waitFor();
  assert.equal((await graph.locator('#overall-score').textContent()).replace('−','-').replace('+',''),String(fixture.explanation.percent));
  await graph.locator('#network .t-hit').first().press('Enter');
  await graph.locator('#network .t-signal').first().click();assert.notEqual(await graph.locator('#detail').textContent(),'點一個訊號或特質，看看它怎麼一路連到分數。');
  await page.screenshot({path:'runtime/role4-matches-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:'runtime/role4-matches-mobile.png',fullPage:true});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await go('profile');assert.equal(await report.locator('body').evaluate(el=>el.scrollWidth>innerWidth),false);
  await page.screenshot({path:'runtime/role4-profile-mobile.png',fullPage:true});
  profile={...profile,ready:false,item_count:0,months:{},traits:profile.traits.map(t=>({...t,value:null}))};
  await page.locator('#refresh-profile').click();await page.locator('#report-empty').waitFor({state:'visible'});assert(await page.locator('#report-frame').isHidden());
  await page.locator('#switch-account').click();assert.equal(await page.locator('#report-frame').getAttribute('src'),null);assert.equal(await page.locator('#network-frame').getAttribute('src'),null);
  await page.locator('#demo-user').selectOption({index:1});await page.locator('#demo-submit').click();await page.locator('#workspace-view').waitFor({state:'visible'});await go('upload');assert(await page.locator('#upload-submit').isDisabled());
  assert.deepEqual(errors,[]);console.log('CONTRACT PASS: profile/months/18 traits/empty states/matches/scopes/network/identity cleanup/mobile; no page errors or overflow.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
