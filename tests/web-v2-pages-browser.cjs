const {refreshReport}=require('./web-v2-navigation.cjs');
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const fixture=require('./web-v2-fixtures.cjs');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_EXECUTABLE});
 const page=await browser.newPage({viewport:{width:1366,height:768},reducedMotion:'reduce'}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 let profile=structuredClone(fixture.profile);
 await page.route('**/api/**',r=>{
  const p=new URL(r.request().url()).pathname;
  return r.fulfill({json:p.endsWith('/health')?{demo_mode:true,models:{category:'fake',attributes:'fake'}}:p.endsWith('/demo-users')?[{user_id:1,display_name:'虛構示範'}]:p.endsWith('/demo-login')?{access_token:'fictional',expires_in:3600}:p.endsWith('/me/profile')?profile:fixture.matches});
 });
 try{
  await page.goto(process.env.RECEIPT_TEST_URL+'/web/');
  await page.locator('#demo-user').selectOption('1');await page.locator('#demo-submit').click();await page.locator('[data-entry="profile"]').click();
  const report=page.frameLocator('#report-frame');await report.locator('#total').filter({hasText:'80'}).waitFor();await report.locator('#frame-status').waitFor({state:'hidden'});
  assert.equal(await page.locator('#taste-page,.trait-value,#report-dialog,#classify-panel').count(),0);
  assert.equal(await page.locator('.workspace-nav button').count(),1);
  assert.match(await report.locator('#total').textContent(),/80/);
  assert.equal(await report.locator('#report-pages > section').count(),5);
  assert.equal(await report.locator('.audit').getAttribute('open'),null);
  for(const size of [{width:1366,height:768},{width:1024,height:640},{width:558,height:510},{width:390,height:844}]){
   await page.setViewportSize(size);await report.locator('.flow-links a[href="#items"]').click();
   const fit=await report.locator('#items').evaluate(n=>{
    const area=n.parentElement.getBoundingClientRect();
    return {overflow:n.ownerDocument.documentElement.scrollWidth>n.ownerDocument.defaultView.innerWidth,chartBottom:n.querySelector('.item-overview').getBoundingClientRect().bottom,viewBottom:area.bottom};
   });
   assert.equal(fit.overflow,false,JSON.stringify(size));assert(fit.chartBottom<=fit.viewBottom+2,JSON.stringify({size,fit}));
  }
  // Every default chapter must fit the same viewport, not just the first chart.
  const fitIssues=[];
  for(const size of [{width:1366,height:768},{width:1024,height:640},{width:558,height:510},{width:390,height:844}]){
   await page.setViewportSize(size);
   for(const id of ['items','insights','cloud-page','rhythm-page','compare']){
    await report.locator('.flow-links a[href="#'+id+'"]').click();
    const fit=await report.locator('#'+id).evaluate(n=>{
     const area=n.parentElement.getBoundingClientRect(),box=n.getBoundingClientRect();
     return {height:box.height,available:area.height,overflow:n.scrollWidth>n.clientWidth+1};
    });
    assert.equal(fit.overflow,false,JSON.stringify({size,id,fit}));
    if(fit.height>fit.available+2){fitIssues.push({size,id,fit});await page.screenshot({path:'runtime/role4-ux-overflow-'+id+'.png'});console.log('CHAPTER OVERFLOW',await report.locator('#'+id).evaluate(n=>[...n.children].map(c=>({tag:c.tagName,cls:c.className,height:c.getBoundingClientRect().height}))));}
   }
  }
  assert.deepEqual(fitIssues,[]);
  await report.locator('.flow-links a[href="#items"]').click();
  await page.setViewportSize({width:1366,height:768});await page.emulateMedia({reducedMotion:'no-preference'});
  await report.locator('#report-pages').hover();await page.mouse.wheel(0,120);
  await page.waitForFunction(()=>{const d=document.getElementById('report-frame').contentDocument;return Math.abs(d.getElementById('insights').getBoundingClientRect().top-d.getElementById('report-pages').getBoundingClientRect().top)<2&&!d.getElementById('report-pages').classList.contains('is-turning');});
  await report.locator('.flow-links a[href="#items"]').click();
  await page.waitForFunction(()=>{const n=document.getElementById('report-frame').contentDocument.getElementById('report-pages');return n.scrollTop<2&&!n.classList.contains('is-turning');});
  await page.emulateMedia({reducedMotion:'reduce'});
  await report.locator('#insights-month').selectOption('2026-05');
  assert.match(await report.locator('#total').textContent(),/160/);
  await report.locator('.category-bar[data-category="1"]').click();
  assert.match(await report.locator('#item-chart').textContent(),/虛構茶.*60/);
  await report.locator('.flow-links a[href="#cloud-page"]').click();
  await report.locator('.flow-links a[href="#cloud-page"][aria-current]').waitFor();
  assert.equal(await report.locator('#cloud-motion').getAttribute('aria-pressed'),'false');
  await report.locator('#cloud-motion').click();
  await page.locator('.workspace-nav').hover();
  await report.locator('.cloud-in-view').waitFor();
  const read=()=>report.locator('.cloud-float').first().evaluate(n=>({duration:parseFloat(getComputedStyle(n).animationDuration),name:getComputedStyle(n).animationName,state:getComputedStyle(n).animationPlayState,transform:getComputedStyle(n).transform}));
  const a=await read();await page.waitForTimeout(350);const b=await read();
  assert(a.duration>=4&&a.duration<=6.5);assert.equal(a.name,'cloud-drift');assert.equal(a.state,'running');assert.notEqual(a.transform,b.transform);
  await report.locator('.cloud-word').first().hover();
  assert.equal(await report.locator('.cloud-float').first().evaluate(n=>getComputedStyle(n).animationPlayState),'paused');
  assert.equal(await report.locator('.cloud-float').nth(1).evaluate(n=>getComputedStyle(n).animationPlayState),'running');
  await report.locator('.cloud-word').first().click();assert.match(await report.locator('#cloud-detail').textContent(),/次.*NT\$/);
  await report.locator('#cloud-motion').click();assert.equal(await report.locator('#cloud-motion').getAttribute('aria-pressed'),'false');
  await report.locator('#insights-month').selectOption('2026-06');assert.equal(await report.locator('.cloud-word').count(),1);
  // Item names are untrusted; top-six disclosure preserves the hidden remainder.
  profile.months['2026-06'].rows=Array.from({length:8},(_,i)=>({day:2,invoice:'fictional-'+i,merchant:'虛構店',name:i===0?'<img src=x onerror=alert(1)>':'虛構品項'+i,amount:(i+1)*10,quantity:1,category:1}));
  await refreshReport(page);await report.locator('#total').filter({hasText:'360'}).waitFor();
  assert.equal(await report.locator('.item-bar-row').count(),6);assert.match(await report.locator('#item-chart-note').textContent(),/其餘 2 項合計 NT\$ 30/);
  await report.locator('#item-chart-more').click();assert.equal(await report.locator('.item-bar-row').count(),8);assert.equal(await report.locator('#item-chart img').count(),0);
  await report.locator('#item-chart-more').click();assert.equal(await report.locator('.item-bar-row').count(),6);
  await page.setViewportSize({width:320,height:568});
  await report.locator('.flow-links a[href="#compare"]').click();await report.locator('#compare-title').waitFor();
  assert.equal(await report.locator('body').evaluate(n=>n.scrollWidth>n.ownerDocument.defaultView.innerWidth),false);
  // A dense month can grow, but every word and count must remain inside its stage.
  profile.months['2026-06'].rows=Array.from({length:11},(_,i)=>({day:2,invoice:'dense-'+i,merchant:'虛構店',name:'虛構品項'+i,amount:20,quantity:1,category:i}));
  await refreshReport(page);await report.locator('#total').filter({hasText:'220'}).waitFor();
  for(const size of [{width:1366,height:768},{width:558,height:510},{width:390,height:844},{width:320,height:568}]){
   await page.setViewportSize(size);await report.locator('.flow-links a[href="#cloud-page"]').click();
   assert.equal(await report.locator('.cloud-word').count(),11);
   await report.locator('.cloud-organic .cloud-word[style*="left"]').first().waitFor();
   const spread=await report.locator('.cloud-word').evaluateAll(words=>({x:new Set(words.map(n=>n.style.left)).size,y:new Set(words.map(n=>n.style.top)).size,depth:new Set(words.map(n=>n.dataset.depth)).size}));
   assert(spread.x>3&&spread.y>3&&spread.depth>3,JSON.stringify(spread));
   const clipped=await report.locator('#category-cloud').evaluate(n=>{
    const b=n.getBoundingClientRect();return n.ownerDocument.documentElement.scrollWidth>n.ownerDocument.defaultView.innerWidth||n.parentElement.scrollWidth>n.parentElement.clientWidth+1||[...n.querySelectorAll('.cloud-word')].some(w=>{const r=w.getBoundingClientRect();return r.top<b.top||r.bottom>b.bottom||r.left<b.left||r.right>b.right;});
   });assert.equal(clipped,false,JSON.stringify(size));
   await report.locator('.chapter-details summary').filter({hasText:'查看次數'}).click();
   await report.locator('.chapter-details[open] .card-footnote').waitFor();
   await report.locator('.chapter-details summary').filter({hasText:'查看次數'}).click();
  }
  profile={...profile,months:{}};await refreshReport(page);await page.locator('#report-empty').waitFor();
  assert.equal(await page.locator('#report-frame').getAttribute('src'),null);
  assert.deepEqual(errors,[]);console.log('REPORT HOME PASS: direct monthly entry, item/category totals, four viewport proportions, five chapters, eleven-category cloud bounds, cloud animation/pause/reduced-motion, item disclosure/XSS and empty cleanup.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
