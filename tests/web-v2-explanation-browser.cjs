const {go:navigate,openCalculation,openReport}=require('./web-v2-navigation.cjs');
/* Contract-only browser check. All API data is fictional; no user records are created. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');const fs=require('node:fs');
const fixture=require('./web-v2-fixtures.cjs');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 let explanation=structuredClone(fixture.explanation),matches=structuredClone(fixture.matches),status=200,delayExplain=null,explainStarted=null;
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  if(path.endsWith('/explain')&&delayExplain){explainStarted?.();await delayExplain;}
  let body=path.endsWith('/health')?{demo_mode:true,models:{category:'fake',attributes:'fake'}}:
   path.endsWith('/demo-users')?[{user_id:1,display_name:'虛構測試'}]:
   path.endsWith('/demo-login')?{access_token:'fictional-browser-token',expires_in:3600}:
   path.endsWith('/me/profile')?fixture.profile:path.endsWith('/explain')?explanation:matches;
  return route.fulfill({status:path.endsWith('/explain')?status:200,json:body});
 });
 const back=async()=>{if(await page.locator('#match-back').isVisible())await page.locator('#match-back').click();};
 const select=async()=>{await back();await page.locator('#refresh-matches').click();await page.locator('.match-card').first().click();};
 try{
  await page.goto((process.env.RECEIPT_TEST_URL||'http://127.0.0.1:8001')+'/web/');
  await page.locator('#demo-user').selectOption('1');await page.locator('#demo-submit').click();
  await navigate(page,'matches');await page.locator('.match-card').first().click();
  await page.locator('#match-result').waitFor();assert(await page.locator('#match-browse').isHidden());assert.equal(await page.locator('#matches-panel').evaluate(n=>n.scrollTop),0);
  const graph=page.frameLocator('#network-frame');
  await graph.locator('#network .t-score-number').waitFor();
  assert.equal(await graph.locator('#overall-score').count(),0);
  assert.equal(await page.locator('#explain-details').getAttribute('open'),null);
  for(const size of [{width:1366,height:768},{width:1024,height:640},{width:390,height:844},{width:320,height:568}]){
   await page.setViewportSize(size);
   await page.waitForFunction(()=>{
    const f=document.getElementById('network-frame'),d=f.contentDocument;
    return d&&parseFloat(d.querySelector('main').style.getPropertyValue('--graph-height'))>=220&&d.documentElement.scrollHeight<=f.clientHeight+2&&d.documentElement.scrollWidth<=f.clientWidth+1&&Math.abs(f.clientHeight-d.querySelector('main').getBoundingClientRect().height-2)<2&&(innerWidth<=640||document.querySelector('#explain-details > summary').getBoundingClientRect().bottom<=document.getElementById('matches-panel').getBoundingClientRect().bottom+1);
   });
   const before=await graph.locator('#network').evaluate(n=>({box:n.getAttribute('viewBox'),height:n.getBoundingClientRect().height,scale:n.getScreenCTM().a}));
   await graph.getByRole('button',{name:/這一格.*查看連線/}).first().press('Enter');
   await graph.locator('#detail').waitFor();
   await page.waitForTimeout(100);
   const after=await graph.locator('#network').evaluate(n=>({box:n.getAttribute('viewBox'),height:n.getBoundingClientRect().height,scale:n.getScreenCTM().a}));
   assert.equal(after.box,before.box);
   assert(Math.abs(after.height-before.height)<2,'selected line must not shrink graph '+JSON.stringify({size,before,after}));
   assert(Math.abs(after.scale-before.scale)<.002,'selected line must not reduce scale');
   await graph.locator('.t-signal').first().click();
   await page.waitForTimeout(100);
   const signalSize=await graph.locator('#network').evaluate(n=>({box:n.getAttribute('viewBox'),height:n.getBoundingClientRect().height,scale:n.getScreenCTM().a}));
   assert.equal(signalSize.box,before.box);
   assert(Math.abs(signalSize.height-before.height)<2,'signal selection keeps graph height');
   assert(Math.abs(signalSize.scale-before.scale)<.002,'signal selection keeps graph scale');
   assert.match(await graph.locator('#detail').textContent(),/×/);
   const noInnerScroll=await graph.locator('html').evaluate(n=>n.scrollHeight<=innerHeight+2&&n.scrollWidth<=innerWidth+1);
   assert(noInnerScroll,'selected text stays within outer scrolling surface');
   if(size.width===1366||size.width===390)await page.screenshot({path:'runtime/role4-stable-selected-'+size.width+'.png',fullPage:true});
   await graph.locator('#reset').click();
   await page.waitForTimeout(100);
   if(size.width>640){
    const fits=await page.locator('#network-frame').evaluate(f=>f.getBoundingClientRect().bottom<=document.getElementById('matches-panel').getBoundingClientRect().bottom);
    assert(fits,'graph and summary fit '+JSON.stringify(size));
    const layout=await graph.locator('#network').evaluate(svg=>{
     const labels=[...svg.querySelectorAll('.t-label')],bounds=svg.getBoundingClientRect();
     const rects=labels.map(n=>n.getBoundingClientRect());
     const font=Math.min(...labels.map(n=>parseFloat(getComputedStyle(n).fontSize)*n.getScreenCTM().a));
     const nodes=[...svg.querySelectorAll('.t-trait')].map(n=>n.getBoundingClientRect());
     return {font,spread:(Math.max(...nodes.map(n=>n.right))-Math.min(...nodes.map(n=>n.left)))/bounds.width,
      clipped:rects.some(r=>r.left<bounds.left||r.right>bounds.right||r.top<bounds.top||r.bottom>bounds.bottom)};
    });
    assert(layout.font>=(size.width>1200?15:11.5),JSON.stringify(layout));
    assert(layout.spread>.74,JSON.stringify(layout));
    assert.equal(layout.clipped,false);
    const summary=await graph.locator('.comparison-overview').evaluate(n=>{
     const r=n.getBoundingClientRect(),c=document.querySelector('.canvas').getBoundingClientRect();
     return {outside:!n.closest('.canvas'),below:r.top>=c.bottom};
    });
    assert(summary.outside&&summary.below);
    const allFits=await page.locator('#explain-details > summary').evaluate(n=>n.getBoundingClientRect().bottom<=document.getElementById('matches-panel').getBoundingClientRect().bottom+1);
    assert(allFits,'collapsed calculation also fits '+JSON.stringify(size));
   }
  }
  // Wheel over the embedded graph must reach the only scroll owner.
  await graph.locator('.toolbar').hover();await page.mouse.wheel(0,240);
  await page.waitForFunction(()=>document.getElementById('matches-panel').scrollTop>0);
  assert.equal(await graph.locator('html').evaluate(n=>n.scrollTop),0);
  await page.setViewportSize({width:1440,height:1000});
  await graph.locator('.graph-help > summary').click();
  await page.waitForFunction(()=>{const f=document.getElementById('network-frame');return f.contentDocument.documentElement.scrollHeight<=f.clientHeight+2;});
  await graph.locator('.graph-help > summary').click();
  await page.waitForTimeout(100);
  const overviewBox=await graph.locator('#network').getAttribute('viewBox');
  const beforeSignal=await graph.locator('#network').evaluate(n=>({height:n.getBoundingClientRect().height,scale:n.getScreenCTM().a}));
  await graph.locator('.t-signal').first().click();
  await page.waitForTimeout(100);
  const afterSignal=await graph.locator('#network').evaluate(n=>({height:n.getBoundingClientRect().height,scale:n.getScreenCTM().a}));
  assert(Math.abs(afterSignal.height-beforeSignal.height)<2,JSON.stringify({beforeSignal,afterSignal}));
  assert(Math.abs(afterSignal.scale-beforeSignal.scale)<.002);
  await page.screenshot({path:'runtime/role4-stable-selected-desktop.png',fullPage:true});
  assert.equal(await graph.locator('#network').getAttribute('viewBox'),overviewBox);
  assert.equal(await graph.locator('.t-buy').count(),0);
  assert.match(await graph.locator('#detail').textContent(),/×/);
  assert(await graph.locator('.selection-readout').isVisible());
  await graph.locator('#reset').click();
  assert.equal(await graph.locator('#network').getAttribute('viewBox'),overviewBox);
  await page.locator('#match-back').click();
  assert(await page.locator('#match-browse').isVisible());
  assert.equal(await page.locator('.match-card').first().evaluate(n=>n===document.activeElement),true);
  await page.locator('.match-card').first().click();
  await openCalculation(page);
  assert.equal(await page.locator('#explain-percent').textContent(),await page.locator('.match-card strong').first().textContent());
  assert.equal(await page.locator('#explain-panel tbody tr').count(),18);
  await page.locator('#explain-precision').selectOption('full');
  for(const cell of explanation.cells){
   const row=page.locator('[data-cell-id="'+cell.id+'"]');
   for(const key of ['mine','theirs','weight','product','part'])assert.equal(await row.locator('[data-field="'+key+'"]').textContent(),cell[key]===null?(key==='mine'||key==='theirs'?'未知':'不計入'):String(cell[key]));
  }
  for(const key of ['dot','norm_mine','norm_theirs','shrink','denominator','score'])assert.equal(await page.locator('.explain-summary [data-field="'+key+'"]').first().textContent(),String(explanation[key]));
  await graph.locator('.t-score-number').waitFor();
  assert.equal((await graph.locator('.t-score-number').textContent()).replace('+','').replace('%',''),String(explanation.percent));
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
  await navigate(page,'profile');await navigate(page,'matches');
  assert.match(await page.locator('#network-status').textContent(),/格式不正確/);
  explanation=structuredClone(fixture.explanation);matches=structuredClone(fixture.matches);await select();await openCalculation(page);
  // Changing a filter clears all detail before the next selection.
  await back();await page.locator('#match-scope').selectOption('city');assert(await page.locator('#explain-panel').isHidden());assert.equal(await page.locator('#explain-panel').textContent(),'');
  await page.locator('.match-card').first().click();await openCalculation(page);
  // A delayed result must not pull the user back after they leave matches.
  let release;delayExplain=new Promise(resolve=>release=resolve);
  const started=new Promise(resolve=>explainStarted=resolve);
  await back();await page.locator('.match-card').first().click();await started;
  await navigate(page,'profile');
  const before=await page.locator('#matches-panel').evaluate(n=>n.scrollTop);
  const response=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/explain'));
  release();await response;delayExplain=null;explainStarted=null;
  await page.waitForTimeout(300);
  assert.equal(new URL(page.url()).hash,'#profile');
  assert.equal(await page.locator('#matches-panel').evaluate(n=>n.scrollTop),before);
  await navigate(page,'matches');await back();await page.emulateMedia({reducedMotion:'reduce'});
  await page.locator('.match-card').first().click();
  await page.locator('#match-result').waitFor();assert(await page.locator('#match-browse').isHidden());assert.equal(await page.locator('#matches-panel').evaluate(n=>n.scrollTop),0);
  status=401;explanation={detail:'not_authenticated'};await back();await page.locator('.match-card').first().click();
  await page.locator('#auth-view').waitFor({state:'visible'});assert.equal(await page.locator('#explain-panel').textContent(),'');assert.equal(await page.locator('#network-frame').getAttribute('src'),null);
  assert.deepEqual(errors,[]);console.log('EXPLANATION PASS: 18 exact cells, summary, precision, card/graph percentage, negative scores, both insufficient-data reasons, invalid response, filter/401 cleanup, focused result, back/focus restoration, responsive single scroll, desktop/mobile.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
