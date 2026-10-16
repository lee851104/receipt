const {go:navigate,openCalculation,openReport}=require('../tests/web-v2-navigation.cjs');
/* Capture only the local frontend with fictional contract fixtures. No real API requests. */
const {chromium}=require('playwright');const fs=require('node:fs');
const fixture=require('../tests/web-v2-fixtures.cjs');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
 const page=await browser.newPage({viewport:{width:1000,height:740}});let index=0;
 fs.mkdirSync('runtime/v2-demo-frames',{recursive:true});
 await page.route('**/api/**',r=>{
  const p=new URL(r.request().url()).pathname;
  const json=p.endsWith('/health')?{demo_mode:false,models:{category:'fake',attributes:'fake'}}:
   p.endsWith('/auth/login')?{access_token:'fictional-demo-token',expires_in:3600}:
   p.endsWith('/invoices')?{job_id:1,month:'2026-05',rows:2}:
   p.endsWith('/jobs/1')?{status:'done',done:2,total:2,message:'處理完成'}:
   p.endsWith('/me/profile')?fixture.profile:
   p.endsWith('/explain')?fixture.explanation:
   p.endsWith('/me')?{user_id:301,username:'fictional_demo',display_name:'虛構展示者',is_demo:false,months:['2026-05','2026-06']}:fixture.matches;
  return r.fulfill({json});
 });
 const capture=async(label,target)=>{
  if(target)await page.locator(target).evaluate(el=>el.scrollIntoView({block:'start'}));else await page.evaluate(()=>scrollTo(0,0));
  await page.evaluate(text=>{
   let banner=document.getElementById('capture-label');if(!banner){banner=document.createElement('div');banner.id='capture-label';banner.style.cssText='pointer-events:none;position:fixed;bottom:0;left:0;right:0;z-index:9999;padding:10px 18px;background:#ef8588;color:#101010;font:bold 14px Microsoft JhengHei,sans-serif;box-shadow:0 -4px 20px #0005';document.body.append(banner);}banner.textContent='v2 前端契約展示 · 虛構資料／模擬 API ｜ '+text;
  },label);
  await page.screenshot({path:'runtime/v2-demo-frames/'+String(index++).padStart(2,'0')+'.png'});
 };
 try{
  await page.goto((process.env.RECEIPT_TEST_URL||'http://127.0.0.1:8001')+'/web/');await page.locator('#login-form').waitFor();await capture('登入');
  await page.locator('#login-username').fill('fictional_demo');await page.locator('#login-password').fill('fake-password');await page.locator('#login-form button').click();
  await page.locator('#profile-content').waitFor();await capture('首屏：完整品味');
  await navigate(page,'upload');await page.locator('#invoice-file').setInputFiles({name:'fictional.csv',mimeType:'text/csv',buffer:Buffer.from('fictional demo only')});await page.locator('#upload-submit').click();await page.getByRole('heading',{name:'處理完成',exact:true}).waitFor();await capture('上傳完成');
  await navigate(page,'profile');await page.locator('.trait-value').first().waitFor();await capture('18 格品味');
  await openReport(page);
  await page.frameLocator('#report-frame').locator('#total').waitFor();await capture('每月消費回顧','#report-frame');
  await navigate(page,'matches');await page.locator('.match-card').first().waitFor();await capture('配對與距離篩選');
  await page.locator('.match-card').first().click();await openCalculation(page);await capture('計算過程','#explain-panel');
  await page.frameLocator('#network-frame').locator('#overall-score').waitFor();await capture('雙方品味關係圖','#network-frame');
  await navigate(page,'settings');await page.locator('#account-content').waitFor();await capture('帳號與資料管理');
  console.log('Captured '+index+' fictional frames.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
