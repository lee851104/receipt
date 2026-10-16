const {chromium}=require('playwright');const assert=require('node:assert/strict');
const {go}=require('./web-v2-navigation.cjs');const fixture=require('./web-v2-fixtures.cjs');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_EXECUTABLE});
 const page=await browser.newPage({viewport:{width:1366,height:768}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/**',r=>{
  const p=new URL(r.request().url()).pathname;
  const json=p.endsWith('/health')?{demo_mode:true,models:{category:'fake',attributes:'fake'}}:p.endsWith('/demo-users')?[{user_id:1,display_name:'虛構示範'}]:p.endsWith('/demo-login')?{access_token:'fictional',expires_in:3600}:p.endsWith('/me/profile')?fixture.profile:fixture.matches;
  return r.fulfill({json});
 });
 try{
  await page.goto(process.env.RECEIPT_TEST_URL+'/web/');
  await page.locator('#demo-user').selectOption('1');await page.locator('#demo-submit').click();await page.locator('#profile-content').waitFor();
  assert.equal(await page.locator('#classify-panel').count(),0);
  assert.equal(await page.locator('[data-workspace="classify"]').count(),0);
  for(const size of [{width:1366,height:768},{width:1024,height:640},{width:558,height:510},{width:390,height:844}]){
   await page.setViewportSize(size);await page.locator('[data-profile-page="taste-page"]').last().click();
   await page.waitForFunction(()=>Math.abs(document.getElementById('profile-pages').scrollTop)<2);
   const fit=await page.evaluate(()=>{
    const cards=[...document.querySelectorAll('.trait-value'),document.querySelector('#taste-page .page-turn')].map(n=>n.getBoundingClientRect()),area=document.getElementById('profile-pages').getBoundingClientRect();
    return {count:cards.length-1,fit:cards.every(r=>r.top>=area.top-1&&r.bottom<=area.bottom+1),overflow:document.documentElement.scrollWidth>innerWidth};
   });assert.deepEqual(fit,{count:18,fit:true,overflow:false},JSON.stringify(size));
   await page.locator('[data-profile-page="month-page"]').first().click();
   await page.waitForFunction(()=>Math.abs(document.getElementById('month-page').getBoundingClientRect().top-document.getElementById('profile-pages').getBoundingClientRect().top)<2);
   assert.match(await page.locator('#month-total').textContent(),/80/);
   await page.locator('#month-select').selectOption('2026-05');assert.match(await page.locator('#month-total').textContent(),/160/);
   await page.locator('#month-select').selectOption('2026-06');
  }
  await page.setViewportSize({width:1366,height:768});await page.locator('[data-profile-page="taste-page"]').last().click();
  await page.waitForFunction(()=>document.getElementById('profile-pages').scrollTop<2);
  await page.locator('#profile-pages').hover();await page.mouse.wheel(0,120);
  await page.waitForFunction(()=>Math.abs(document.getElementById('month-page').getBoundingClientRect().top-document.getElementById('profile-pages').getBoundingClientRect().top)<2);
  await page.locator('#month-select').selectOption('2026-05');
  await page.locator('#open-report').click();await page.locator('#report-dialog').waitFor();await page.frameLocator('#report-frame').locator('#total').filter({hasText:'160'}).waitFor();
  await page.keyboard.press('Escape');assert(await page.locator('#report-dialog').isHidden());
  await page.goto(process.env.RECEIPT_TEST_URL+'/web/#classify');await page.locator('#profile-content').waitFor();assert.equal(new URL(page.url()).hash,'#profile');
  await page.setViewportSize({width:320,height:568});await page.emulateMedia({reducedMotion:'reduce'});
  await page.locator('[data-profile-page="month-page"]').click();
  await page.waitForFunction(()=>Math.abs(document.getElementById('month-page').getBoundingClientRect().top-document.getElementById('profile-pages').getBoundingClientRect().top)<2);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await go(page,'matches');assert(await page.locator('#matches-panel').isVisible());
  assert.deepEqual(errors,[]);console.log('PAGES PASS: classification removed; 18 traits fit four viewports; month summary, one-gesture wheel paging, modal report/Escape, retired URL redirect.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
