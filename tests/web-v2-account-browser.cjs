/* Fictional contract responses; does not modify any real account. */
const {chromium}=require('playwright');const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],calls=[];
 page.on('pageerror',e=>errors.push(e.message));
 let me={user_id:301,username:'fictional',display_name:'虛構使用者',is_demo:false,months:['2026-05','2026-06']},failMonth=true,failLogout=false,holdPassword=false,releasePassword,failJob=true,releaseProfile,profileStarted;
 const profilePending=new Promise(resolve=>profileStarted=resolve);
 await page.route('**/api/**',async r=>{
  const req=r.request(),path=new URL(req.url()).pathname,method=req.method();calls.push({path,method,auth:req.headers().authorization});
  let status=200,json={};
  if(path.endsWith('/health'))json={demo_mode:true,models:{category:'fake',attributes:'fake'}};
  else if(path.endsWith('/demo-users'))json=[{user_id:1,display_name:'唯讀示範'}];
  else if(path.endsWith('/demo-login')){me={...me,is_demo:true};json={access_token:'demo-token',expires_in:3600};}
  else if(path.endsWith('/auth/login')){me={...me,is_demo:false};json={access_token:'old-token',expires_in:3600};}
  else if(path.endsWith('/me/profile')){await new Promise(resolve=>{releaseProfile=resolve;profileStarted();});status=401;json={detail:'not_authenticated'};}
  else if(path.endsWith('/invoices'))json={job_id:1,month:'2026-05',rows:1};
  else if(path.endsWith('/jobs/1')){status=failJob?503:200;json=failJob?{detail:'internal_error'}:{status:'done',done:1,total:1};}
  else if(path.endsWith('/auth/logout')){status=failLogout?503:204;json={detail:'internal_error'};}
  else if(path.endsWith('/me/password')){const body=req.postDataJSON();if(body.current_password!=='correct-password'){status=403;json={detail:'wrong_password'};}else {if(holdPassword)await new Promise(resolve=>releasePassword=resolve);json={access_token:'new-token',expires_in:3600};}}
  else if(path.includes('/me/months/')){if(failMonth){status=409;json={detail:'job_in_progress'};}else{me.months=me.months.filter(m=>!path.endsWith(m));status=204;}}
  else if(path.endsWith('/me')){
   if(method==='DELETE'){if(req.postDataJSON().password!=='correct-password'){status=403;json={detail:'wrong_password'};}else status=204;}
   else {if(method==='PATCH')me={...me,display_name:req.postDataJSON().display_name};json=me;}
  }else{status=404;json={detail:'not_found'};}
  await r.fulfill(status===204?{status,body:''}:{status,json});
 });
 async function login(){await page.locator('#login-username').fill('fictional');await page.locator('#login-password').fill('correct-password');await page.locator('#login-form button').click();await page.locator('[data-workspace="settings"]').click();await page.locator('#account-content').waitFor({state:'visible'});}
 try{
  await page.goto((process.env.RECEIPT_TEST_URL||'http://127.0.0.1:8001')+'/web/');await login();
  await page.locator('#account-name').fill('<b>安全文字</b>');await page.locator('#account-name-submit').click();await page.locator('#account-notice').filter({hasText:'顯示名稱已更新'}).waitFor();assert.equal(await page.locator('#identity-label').textContent(),'<b>安全文字</b>');assert.equal(await page.locator('#identity-label b').count(),0);
  await page.locator('#current-password').fill('wrong-password');await page.locator('#new-password').fill('fresh-password');await page.locator('#password-submit').click();await page.locator('#account-error').filter({hasText:'目前密碼不正確'}).waitFor();assert.equal(await page.locator('#current-password').inputValue(),'');assert.equal(await page.locator('#new-password').inputValue(),'');
  await page.locator('[data-workspace="profile"]').click();await profilePending;await page.locator('[data-workspace="settings"]').click();
  holdPassword=true;await page.locator('#current-password').fill('correct-password');await page.locator('#new-password').fill('fresh-password');
  const sent=page.waitForRequest('**/api/me/password');await page.locator('#password-submit').click();await sent;
  assert(await page.locator('[data-workspace="upload"]').isDisabled());assert(await page.locator('#upload-submit').isDisabled());
  const before=calls.length;
  await page.evaluate(()=>{history.replaceState(null,'','#profile');dispatchEvent(new HashChangeEvent('hashchange'));});
  assert(await page.locator('#settings-panel').isVisible());assert.equal(calls.length,before);
  releaseProfile();assert(await page.locator('#workspace-view').isVisible());
  releasePassword();holdPassword=false;await page.locator('#account-notice').filter({hasText:'密碼已更新'}).waitFor();await page.locator('#account-refresh').click();await page.locator('#account-content').waitFor();
  assert.equal(calls.filter(c=>c.path==='/api/me').at(-1).auth,'Bearer new-token');
  await page.locator('[data-workspace="upload"]').click();await page.locator('#invoice-file').setInputFiles({name:'fictional.csv',mimeType:'text/csv',buffer:Buffer.from('fictional')});await page.locator('#upload-submit').click();await page.locator('#retry-job').waitFor({state:'visible'});
  await page.locator('[data-workspace="settings"]').click();assert(await page.locator('#password-submit').isDisabled());
  await page.locator('[data-workspace="upload"]').click();failJob=false;await page.locator('#retry-job').click();await page.getByRole('heading',{name:'處理完成',exact:true}).waitFor();
  await page.locator('[data-workspace="settings"]').click();assert(await page.locator('#password-submit').isEnabled());
  await page.getByRole('button',{name:'刪除 2026-05',exact:true}).click();await page.locator('#account-confirm').waitFor();await page.locator('#confirm-cancel').click();assert.equal(calls.filter(c=>c.method==='DELETE').length,0);
  await page.getByRole('button',{name:'刪除 2026-05',exact:true}).click();await page.locator('#confirm-submit').click();await page.locator('#confirm-error').filter({hasText:'仍在處理'}).waitFor();assert.equal(await page.locator('.account-month').count(),2);
  failMonth=false;await page.locator('#confirm-submit').click();await page.locator('#account-confirm').waitFor({state:'hidden'});assert.equal(await page.locator('.account-month').count(),1);assert.match(await page.locator('#account-months').textContent(),/2026-06/);
  await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);await page.screenshot({path:'runtime/role4-account-mobile.png',fullPage:true});
  await page.locator('#delete-account').click();assert(await page.locator('#delete-password').isVisible());await page.locator('#delete-password').fill('wrong-password');await page.locator('#confirm-submit').click();await page.locator('#confirm-error').filter({hasText:'目前密碼不正確'}).waitFor();assert.equal(await page.locator('#delete-password').inputValue(),'');assert(await page.locator('#workspace-view').isVisible());
  await page.locator('#delete-password').fill('correct-password');await page.locator('#confirm-submit').click();await page.locator('#auth-view').waitFor({state:'visible'});assert.equal(await page.evaluate(()=>sessionStorage.getItem('receipt.v2.session')),null);assert.equal(await page.locator('#account-username').textContent(),'');assert.equal(await page.locator('#account-confirm').evaluate(el=>el.open),false);
  await login();failLogout=true;await page.locator('#logout-submit').click();await page.locator('#account-error').waitFor({state:'visible'});assert(await page.locator('#workspace-view').isVisible());failLogout=false;await page.locator('#logout-submit').click();await page.locator('#auth-view').waitFor({state:'visible'});
  await page.evaluate(()=>{history.pushState(null,'','#settings');dispatchEvent(new HashChangeEvent('hashchange'));});assert(await page.locator('#workspace-view').isHidden());
  await page.locator('#demo-user').selectOption('1');await page.locator('#demo-submit').click();await page.locator('[data-workspace="settings"]').click();await page.locator('#account-content').waitFor();
  for(const id of ['account-name-submit','password-submit','delete-account'])assert(await page.locator('#'+id).isDisabled());assert(await page.getByRole('button',{name:'刪除 2026-06',exact:true}).isDisabled());assert(await page.locator('#logout-submit').isEnabled());
  await page.locator('#logout-submit').click();await page.locator('#auth-view').waitFor({state:'visible'});assert.deepEqual(errors,[]);
  console.log('ACCOUNT PASS: name/password/new token, cancel/confirm month deletion, 409, wrong password, account deletion, failed/successful logout, history protection, demo readonly, mobile.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
