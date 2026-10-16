/* 可控制延遲的契約測試；實際 HTTP 全流程另見 live-browser。 */
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const fixture=require('./web-v2-fixtures.cjs');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
 const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 let removed=false,checks=0,matches=0,recomputing=true;const profileTokens=[];
 await page.route('**/api/**',async r=>{
  const path=new URL(r.request().url()).pathname,method=r.request().method();
  let json={},status=200;
  if(path.endsWith('/health'))json={demo_mode:false,models:{category:'fake',attributes:'fake'}};
  else if(path.endsWith('/login'))json={access_token:'synthetic-token',expires_in:3600};
  else if(path.endsWith('/me'))json={user_id:3,username:'synthetic',display_name:'虛構使用者',is_demo:false,months:removed?['2026-06']:['2026-05','2026-06']};
  else if(path.endsWith('/password')){
   if(r.request().postDataJSON().current_password==='incorrect'){status=403;json={detail:'wrong_password'};}
   else json={access_token:'new-synthetic-token',expires_in:3600};
  }
  else if(method==='DELETE'){removed=true;status=204;}
  else if(path.endsWith('/profile')){
   checks++;
   profileTokens.push(r.request().headers().authorization);
   json={...fixture.profile,recomputing,item_count:recomputing?80:40};
  }else if(path.endsWith('/matches')){matches++;json=fixture.matches;}
  return r.fulfill({status,...(status===204?{body:''}:{json})});
 });
 try{
  await page.goto(process.env.RECEIPT_TEST_URL+'/web/');
  await page.locator('#login-username').fill('synthetic');await page.locator('#login-password').fill('synthetic-password');await page.locator('#login-form button').click();
  await page.locator('[data-workspace="settings"]').click();await page.locator('#account-content').waitFor();
  await page.getByRole('button',{name:'刪除 2026-05',exact:true}).click();await page.locator('#confirm-submit').click();await page.locator('#account-confirm').waitFor({state:'hidden'});
  await page.locator('[data-workspace="profile"]').click();await page.locator('#profile-message').filter({hasText:'重新計算中'}).waitFor();
  assert(await page.locator('#profile-content').isHidden());assert(await page.locator('#report-frame').isHidden());
  await page.locator('[data-workspace="matches"]').click();await page.locator('#match-status').filter({hasText:'重新計算中'}).waitFor();
  await page.locator('#refresh-matches').click();assert.equal(matches,0);
  // 改名不能中斷已知的背景重算，或重新開放舊配對查詢。
  await page.locator('[data-workspace="settings"]').click();
  await page.locator('#account-name').fill('虛構新名稱');await page.locator('#account-name-submit').click();
  await page.locator('#account-notice').filter({hasText:'顯示名稱已更新'}).waitFor();
  await page.locator('[data-workspace="matches"]').click();
  await page.locator('#match-status').filter({hasText:'重新計算中'}).waitFor({timeout:3000});
  assert.equal(matches,0);
  // 密碼變更失敗與成功都不能讓重算中的配對提早解鎖。
  await page.locator('[data-workspace="settings"]').click();
  await page.locator('#current-password').fill('incorrect');await page.locator('#new-password').fill('synthetic-next-password');await page.locator('#password-submit').click();
  await page.locator('#account-error').waitFor();
  await page.locator('[data-workspace="matches"]').click();await page.locator('#match-status').filter({hasText:'重新計算中'}).waitFor();assert.equal(matches,0);
  await page.locator('[data-workspace="settings"]').click();
  await page.locator('#current-password').fill('synthetic-password');await page.locator('#new-password').fill('synthetic-next-password');await page.locator('#password-submit').click();
  await page.locator('#account-notice').filter({hasText:'密碼已更新'}).waitFor();
  await page.locator('[data-workspace="matches"]').click();await page.locator('#match-status').filter({hasText:'重新計算中'}).waitFor();assert.equal(matches,0);
  assert(profileTokens.includes('Bearer new-synthetic-token'));recomputing=false;
  await page.locator('.match-card').first().waitFor();assert.equal(matches,1);
  await page.locator('[data-workspace="profile"]').click();await page.locator('#profile-content').waitFor();
  assert.match(await page.locator('#profile-overview').textContent(),/40 個有效品項/);
  assert(checks>=4);assert.deepEqual(errors,[]);
  console.log('RECOMPUTE CONTRACT PASS: old profile hidden, two-second polling, matches blocked, rename/password success/failure preserve polling, completion refreshes active matches.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
