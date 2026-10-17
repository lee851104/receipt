const {go:navigate,openCalculation,openReport}=require('./web-v2-navigation.cjs');
/* 真 HTTP + 正式 API／SQLite／worker；無 route.fulfill，只有合成 CSV 與 fake 模型。 */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const origin=process.env.RECEIPT_TEST_URL;
if(!origin)throw Error('Use tests/run_web_v2_live.py with its isolated database.');
const password='Fictional-pass-2026',nextPassword='Fictional-next-2026';
const columns='發票日期,發票狀態,發票號碼,賣方名稱,賣方地址,消費明細_品名,消費明細_數量,消費明細_金額';
function csv(month){
 const names=['虛構奶茶','虛構餅乾','虛構衛生紙','虛構雞蛋'];
 return Buffer.from('\ufeff'+columns+'\r\n'+Array.from({length:40},(_,i)=>[
 month.replace('-','')+String(i%28+1).padStart(2,'0'),'開立已確認','SYN-'+i,'虛構測試店','臺北市大安區測試路1號',names[i%4],1,60+i%7*10
 ].join(',')).join('\r\n')+'\r\n,,,匯出摘要\r\n');
}
async function request(path,{token,method='GET',json,body}={}){
 const response=await fetch(origin+'/api'+path,{method,headers:{...(token?{Authorization:'Bearer '+token}:{}),...(json?{'Content-Type':'application/json'}:{})},body:json?JSON.stringify(json):body});
 return {status:response.status,data:response.status===204?null:await response.json()};
}
async function poll(read,check){
 for(let i=0;i<150;i++){const value=await read();if(check(value))return value;await new Promise(r=>setTimeout(r,100));}
 throw Error('Polling did not complete');
}
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.setDefaultTimeout(15000);
 const go=name=>navigate(page,name);
 const login=async(name,pw)=>{await page.locator('#login-username').fill(name);await page.locator('#login-password').fill(pw);await page.locator('#login-form button').click();await page.locator('#workspace-view').waitFor();};
 const upload=async month=>{await go('upload');await page.locator('#invoice-file').setInputFiles({name:'synthetic-'+month+'.csv',mimeType:'text/csv',buffer:csv(month)});await page.locator('#upload-submit').click();await page.getByRole('heading',{name:'處理完成',exact:true}).waitFor();};
 try{
  const health=await request('/health');assert.equal(health.data.models.category,'fake');assert.equal(health.data.models.attributes,'fake');assert.equal(health.data.gpu_mode,false);
  // 概念範例走真正 login / matches / explain HTTP，沒有改寫端點回應。
  const demo=await request('/auth/demo-login',{method:'POST',json:{user_id:1}});
  const math=(await request('/matches/2/explain',{token:demo.data.access_token})).data;
  assert.equal(math.percent,82);assert(Math.abs(math.dot-1.88)<1e-12);assert(Math.abs(math.denominator-2.29)<1e-12);
  assert.equal(math.cells.length,18);assert.equal(math.cells.filter(c=>c.part===null).length,13);
  await page.goto(origin+'/web/');
  await page.locator('#demo-user').selectOption('1');await page.locator('#demo-submit').click();
  await page.locator('#profile-panel').waitFor({timeout:3000});
  assert.equal(new URL(page.url()).hash,'#profile');
  assert.equal(await page.locator('.workspace-nav [data-workspace]').count(),2);
  assert(await page.locator('[data-workspace="upload"]').isHidden());
  await page.locator('#settings-toggle').click();
  assert(await page.locator('[data-workspace="upload"]').isVisible());
  await page.locator('#settings-toggle').press('Escape');
  assert.equal(await page.locator('#settings-toggle').getAttribute('aria-expanded'),'false');
  await page.locator('#settings-toggle').press('Enter');
  await page.locator('.workspace-nav').click();
  assert(await page.locator('#settings-options').isHidden());
  await go('matches');
  await page.locator('.match-card').first().click();
  await page.locator('#network-frame').waitFor();
  assert(await page.locator('#explain-panel').isHidden());
  assert.equal(await page.locator('#explain-panel').textContent(),'');
  await openCalculation(page);
  assert.equal(await page.locator('#explain-percent').textContent(),'+82%');
  await page.frameLocator('#network-frame').locator('#views-note').filter({hasText:'重新計算中'}).waitFor();
  await go('settings');await page.locator('#account-content').waitFor();
  assert.equal(await page.locator('#logout-submit').textContent(),'登出此瀏覽器');
  await page.locator('#logout-submit').click();await page.locator('#auth-view').waitFor();
  assert.equal((await request('/me',{token:demo.data.access_token})).status,200);
  console.log('LIVE concepts: explain API dot=1.88 denominator=2.29 percent=82; demo logout preserves other sessions.');

  const username='live_'+Date.now(),peer='peer_'+Date.now();
  await page.locator('#register-tab').click();await page.locator('#register-username').fill(username);await page.locator('#register-password').fill(password);await page.locator('#register-form button').click();await page.locator('#auth-notice').waitFor();
  await login(username,password);
  await page.locator('#profile-content').waitFor();
  assert(await page.locator('#report-empty').isVisible());
  assert.match(await page.locator('#report-empty').textContent(),/設定 → 上傳檔案/);
  await page.reload();await page.locator('#profile-content').waitFor();
  assert.equal(new URL(page.url()).hash,'#profile');
  await upload('2026-05');await upload('2026-06');
  await go('profile');await page.locator('#profile-content').waitFor();
  await openReport(page);assert.equal(await page.frameLocator('#report-frame').locator('#insights-month option').count(),2);
  assert.equal(await page.locator('.trait-value').count(),0);
  await openReport(page);
  const report=page.frameLocator('#report-frame');await report.locator('#total').waitFor();
  await report.locator('#insights-month').selectOption('2026-05');
  assert(!(await report.locator('body').textContent()).includes('月報資料格式不正確'));
  // 第二位虛構使用者也透過正式上傳管線建立，沒有直接寫 profile。
  assert.equal((await request('/auth/register',{method:'POST',json:{username:peer,password,display_name:'虛構同好'}})).status,201);
  const peerToken=(await request('/auth/login',{method:'POST',body:new URLSearchParams({username:peer,password})})).data.access_token;
  for(const month of ['2026-05','2026-06']){
   const body=new FormData();body.append('file',new Blob([csv(month)],{type:'text/csv'}),'synthetic.csv');
   const job=await request('/invoices',{method:'POST',token:peerToken,body});assert.equal(job.status,202);
   const done=await poll(()=>request('/jobs/'+job.data.job_id,{token:peerToken}),r=>['done','failed'].includes(r.data.status));assert.equal(done.data.status,'done');
  }
  const second=(await request('/auth/login',{method:'POST',body:new URLSearchParams({username,password})})).data.access_token;
  const me=(await request('/me',{token:second})).data;
  const list=(await request('/matches',{token:second})).data;
  const card=list.people.find(p=>p.display_name==='虛構同好');assert(card,'uploaded fake-model profiles must produce a match');
  await go('matches');const peerCard=page.locator('.match-card').filter({hasText:'虛構同好'});await peerCard.click();
  await openCalculation(page);assert.equal(await page.locator('#explain-percent').textContent(),await peerCard.locator('strong').textContent());
  assert.equal(await page.locator('#explain-panel tbody tr').count(),18);
  const graph=page.frameLocator('#network-frame');await graph.locator('#network .t-signal').first().waitFor();
  assert.equal(await graph.locator('#overall-score').textContent(),(card.percent>0?'+':'')+card.percent);
  const explanation=(await request('/matches/'+card.user_id+'/explain',{token:second})).data;
  assert.equal(explanation.percent,card.percent);
  await page.locator('#explain-precision').selectOption('full');
  for(const cell of explanation.cells)for(const key of ['mine','theirs','weight','product','part']){
   assert.equal(await page.locator('[data-cell-id="'+cell.id+'"] [data-field="'+key+'"]').textContent(),cell[key]===null?(['mine','theirs'].includes(key)?'未知':'不計入'):String(cell[key]));
  }
  fs.mkdirSync('runtime',{recursive:true});await page.screenshot({path:'runtime/role4-live-matches-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.screenshot({path:'runtime/role4-live-matches-mobile.png',fullPage:true});
  console.log('LIVE uploads: two months -> 80 items -> direct monthly report -> matches / 18 explanation cells / real network; desktop/mobile.');

  await page.locator('#settings-toggle').click();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.locator('#settings-toggle').press('Escape');
  await go('settings');await page.locator('#account-content').waitFor();
  await page.getByRole('button',{name:'刪除 2026-05',exact:true}).click();await page.locator('#confirm-cancel').click();
  assert((await request('/me',{token:second})).data.months.includes('2026-05'));
  await page.getByRole('button',{name:'刪除 2026-05',exact:true}).click();await page.locator('#confirm-submit').click();await page.locator('#account-confirm').waitFor({state:'hidden'});
  await go('profile');await page.locator('#profile-content').waitFor();await openReport(page);assert.equal(await page.frameLocator('#report-frame').locator('#insights-month option').count(),1);
  assert.deepEqual((await request('/me',{token:second})).data.months,['2026-06']);
  await go('settings');await page.locator('#account-name').fill('虛構更名');await page.locator('#account-name-submit').click();await page.locator('#account-notice').filter({hasText:'顯示名稱已更新'}).waitFor();
  await page.locator('#current-password').fill(password);await page.locator('#new-password').fill(nextPassword);await page.locator('#password-submit').click();await page.locator('#account-notice').filter({hasText:'密碼已更新'}).waitFor();
  assert.equal((await request('/me',{token:second})).status,401);
  const rotated=(await request('/auth/login',{method:'POST',body:new URLSearchParams({username,password:nextPassword})})).data.access_token;
  assert.equal((await request('/me',{token:rotated})).status,200);
  await page.locator('#logout-submit').click();await page.locator('#auth-view').waitFor();
  assert.equal((await request('/me',{token:rotated})).status,401);
  await login(username,nextPassword);await go('settings');await page.locator('#account-content').waitFor();
  await page.locator('#delete-account').click();await page.locator('#delete-password').fill('incorrect-password');await page.locator('#confirm-submit').click();await page.locator('#confirm-error').waitFor();
  await page.locator('#delete-password').fill(nextPassword);await page.locator('#confirm-submit').click();await page.locator('#auth-view').waitFor();
  assert.equal((await request('/auth/login',{method:'POST',body:new URLSearchParams({username,password:nextPassword})})).status,401);
  assert(!(await request('/matches',{token:peerToken})).data.people.some(p=>p.user_id===me.user_id));
  assert.equal((await request('/matches/'+me.user_id+'/explain',{token:peerToken})).status,404);
  assert.deepEqual(errors,[]);
  console.log('LIVE account: cancel/delete month -> recomputed 40 items -> rename -> password rotation/old token 401 -> logout/all tokens 401 -> login/new password -> wrong-password rejection -> delete/no login/no match.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
