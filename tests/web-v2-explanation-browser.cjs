const {go:navigate,openCalculation}=require('./web-v2-navigation.cjs');
/* Contract-only browser check. All API data is fictional; no user records are created. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');const fs=require('node:fs');
const fixture=require('./web-v2-fixtures.cjs');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 let explanation=structuredClone(fixture.explanation),matches=structuredClone(fixture.matches),status=200;
 await page.route('**/api/**',route=>{
  const path=new URL(route.request().url()).pathname;
  let body=path.endsWith('/health')?{demo_mode:true,models:{category:'fake',attributes:'fake'}}:
   path.endsWith('/demo-users')?[{user_id:1,display_name:'虛構測試'}]:
   path.endsWith('/demo-login')?{access_token:'fictional-browser-token',expires_in:3600}:
   path.endsWith('/items/classify')?{name:'虛構茶',category:{name:'飲品',prob:.9},attributes_status:'ready',attributes:{}}:
   path.endsWith('/me/profile')?fixture.profile:path.endsWith('/explain')?explanation:matches;
  return route.fulfill({status:path.endsWith('/explain')?status:200,json:body});
 });
 const select=async()=>{await page.locator('#refresh-matches').click();await page.locator('.match-card').first().click();};
 try{
  await page.goto((process.env.RECEIPT_TEST_URL||'http://127.0.0.1:8001')+'/web/');
  await page.locator('#demo-user').selectOption('1');await page.locator('#demo-submit').click();
  await navigate(page,'matches');await page.locator('.match-card').first().click();
  await openCalculation(page);
  assert.equal(await page.locator('#explain-percent').textContent(),await page.locator('.match-card strong').first().textContent());
  assert.equal(await page.locator('#explain-panel tbody tr').count(),18);
  await page.locator('#explain-precision').selectOption('full');
  for(const cell of explanation.cells){
   const row=page.locator('[data-cell-id="'+cell.id+'"]');
   for(const key of ['mine','theirs','weight','product','part'])assert.equal(await row.locator('[data-field="'+key+'"]').textContent(),cell[key]===null?(key==='mine'||key==='theirs'?'未知':'不計入'):String(cell[key]));
  }
  for(const key of ['dot','norm_mine','norm_theirs','shrink','denominator','score'])assert.equal(await page.locator('.explain-summary [data-field="'+key+'"]').first().textContent(),String(explanation[key]));
  const graph=page.frameLocator('#network-frame');await graph.locator('#overall-score').waitFor();
  assert.equal((await graph.locator('#overall-score').textContent()).replace('+',''),String(explanation.percent));
  await page.locator('#explain-precision').selectOption('compact');
  fs.mkdirSync('runtime',{recursive:true});await page.locator('#explain-panel').evaluate(el=>el.scrollIntoView());await page.screenshot({path:'runtime/role4-explanation-desktop.png'});
  await page.setViewportSize({width:390,height:844});await page.locator('#explain-panel').evaluate(el=>el.scrollIntoView());await page.screenshot({path:'runtime/role4-explanation-mobile.png'});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.locator('#explain-precision').selectOption('full');assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  // Only presentation precision is changed: the integer comes from the API, not local rounding.
  explanation={...structuredClone(fixture.explanation),score:-.294,percent:-30};matches.people[0].percent=-30;
  await select();await openCalculation(page);await page.locator('#explain-percent').filter({hasText:'−30%'}).waitFor();
  // A newly inconsistent card/explanation invalidates both displays.
  explanation.percent=-31;await select();await page.locator('#network-status').filter({hasText:'重新查詢配對清單'}).waitFor();
  assert(await page.locator('#explain-panel').isHidden());assert.equal(await page.locator('#explain-panel').textContent(),'');assert.equal(await page.locator('#network-frame').getAttribute('src'),null);
  // Incomparable results explain why, preserving unknown rather than pretending the score is zero.
  for(const reason of ['too_few_shared','not_enough_items']){
   explanation={...structuredClone(fixture.explanation),comparable:false,reason,shared_two_sided:4};
   for(const key of ['dot','norm_mine','norm_theirs','shrink','denominator','score','percent'])explanation[key]=null;
   explanation.cells.forEach(c=>c.part=null);
   await select();await openCalculation(page);assert.equal(await page.locator('#explain-percent').count(),0);assert(await page.locator('#network-frame').isVisible());
  }
  matches=structuredClone(fixture.matches);explanation={...structuredClone(fixture.explanation),cells:[]};await select();await page.locator('#network-status').filter({hasText:'格式不正確'}).waitFor();assert(await page.locator('#explain-panel').isHidden());
  await navigate(page,'classify');await page.locator('#item-name').fill('虛構茶');await page.locator('#classify-form button').click();
  await page.getByText('分析完成',{exact:true}).waitFor();await navigate(page,'matches');
  assert.match(await page.locator('#network-status').textContent(),/格式不正確/);
  explanation=structuredClone(fixture.explanation);matches=structuredClone(fixture.matches);await select();await openCalculation(page);
  // Changing a filter clears all detail before the next selection.
  await page.locator('#match-scope').selectOption('city');assert(await page.locator('#explain-panel').isHidden());assert.equal(await page.locator('#explain-panel').textContent(),'');
  await page.locator('.match-card').first().click();await openCalculation(page);
  status=401;explanation={detail:'not_authenticated'};await page.locator('.match-card').first().click();
  await page.locator('#auth-view').waitFor({state:'visible'});assert.equal(await page.locator('#explain-panel').textContent(),'');assert.equal(await page.locator('#network-frame').getAttribute('src'),null);
  assert.deepEqual(errors,[]);console.log('EXPLANATION PASS: 18 exact cells, summary, precision, card/graph percentage, negative scores, both insufficient-data reasons, invalid response, filter/401 cleanup, desktop/mobile.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
