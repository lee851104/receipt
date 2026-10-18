const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {go,openReport}=require('./web-v2-navigation.cjs');
const fixture=require('./web-v2-fixtures.cjs');
const base=process.env.RECEIPT_TEST_URL;
if(!base)throw Error('Use tests/run_web_v2_live.py to provide RECEIPT_TEST_URL.');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
 const page=await browser.newPage();page.setDefaultTimeout(5000);
 let jobId=40,status='done',pollError=false,release;
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  if(path.includes('/jobs/')){
   if(release)await release.promise;
   return route.fulfill({status:pollError?503:200,json:pollError?{detail:'internal_error'}:{status,total:1,done:status==='done'?1:0}});
  }
  const body=path.endsWith('/health')?{demo_mode:false}:
   path.endsWith('/login')?{access_token:'fictional-only',expires_in:3600}:
   path.endsWith('/invoices')?{job_id:++jobId,month:'2026-05',rows:1}:
   path.endsWith('/me/profile')?fixture.profile:
   path.endsWith('/me')?{username:'fictional',display_name:'虛構測試',is_demo:false}:fixture.matches;
  await route.fulfill({json:body});
 });
 async function upload(next='done',background=false){
  status=next;await go(page,'upload');
  if(background){let resolve;const promise=new Promise(r=>resolve=r);release={promise,resolve};}
  await page.locator('#invoice-file').setInputFiles({name:'fictional.csv',mimeType:'text/csv',buffer:Buffer.from('fictional,test')});
  await page.locator('#upload-submit').click();
  if(background){await page.locator('#upload-state').filter({hasText:'排隊中'}).waitFor();await go(page,background==='profile'?'profile':'home');if(background==='profile')await openReport(page);const gate=release;release=null;gate.resolve();}
  await page.locator('#upload-state').filter({hasText:pollError?'暫時無法完成':next==='done'?'處理完成':'處理失敗'}).waitFor({state:'attached'});
  await page.waitForFunction(()=>['處理完成','處理失敗','暫時無法完成'].includes(document.getElementById('upload-state').textContent));
 }
 try{
  await page.goto(base+'/web/');await page.locator('#login-username').fill('fictional');await page.locator('#login-password').fill('fictional-password');await page.locator('#login-submit').click();await page.locator('#home-panel').waitFor();
  await upload();await page.locator('#open-profile').click();await openReport(page);
  assert(await page.locator('#upload-background').isHidden(),'direct report entry acknowledges completed upload');
  await go(page,'home');assert(await page.locator('#upload-background').isHidden());
  await upload('done',true);await page.locator('#upload-background').waitFor();await go(page,'profile');await openReport(page);
  assert(await page.locator('#upload-background').isHidden(),'home report entry also acknowledges');
  await upload('done',true);await page.locator('#upload-background').click();await openReport(page);assert(await page.locator('#upload-background').isHidden(),'notification entry acknowledges');
  await upload('done','profile');await openReport(page);assert(await page.locator('#upload-background').isHidden(),'completion on current report refreshes and acknowledges');
  await upload('failed',true);await page.locator('#upload-background').waitFor();await page.locator('#upload-background').click();await go(page,'home');
  assert(await page.locator('#upload-background').isHidden(),'viewed failed result acknowledges');
  await upload('failed');await go(page,'home');assert(await page.locator('#upload-background').isHidden(),'failure while upload page visible acknowledges');
  pollError=true;await upload('done',true);await page.locator('#upload-background').click();await page.locator('#retry-job').waitFor();await go(page,'home');
  assert(await page.locator('#upload-background').isVisible(),'unknown job status remains actionable until retried');
  await page.locator('#upload-background').click();pollError=false;await page.locator('#retry-job').click();await page.locator('#open-profile').waitFor();await page.locator('#open-profile').click();await openReport(page);
  assert(await page.locator('#upload-background').isHidden(),'resolved retry clears notification');
  assert.deepEqual(errors,[]);console.log('UPLOAD ACK PASS: direct/home/notification report entry, new jobs, foreground/background failure, polling error retry.');
 }finally{release?.resolve();await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
