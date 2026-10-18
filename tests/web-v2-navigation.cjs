/* Navigate through the same visible controls used by a person. */
async function go(page,name){
 await page.locator('#workspace-view').waitFor();
 if(['profile','matches'].includes(name)){
  if(!(await page.locator('#home-panel').isVisible()))await page.locator('[data-workspace="home"]').click();
  await page.locator('[data-entry="'+name+'"]').click();return;
 }
 if(['upload','settings'].includes(name)&&await page.locator('body').evaluate(n=>n.classList.contains('network-fullscreen')))await page.locator('[data-workspace="home"]').click();
 const target=page.locator('[data-workspace="'+name+'"]');
 if(['upload','settings'].includes(name)&&!(await target.isVisible()))await page.locator('#settings-toggle').click();
 await target.click();
}
async function openCalculation(page){
 await page.locator('#explain-details').waitFor();
 await page.locator('#explain-details > summary').click();
 await page.locator('#explain-panel').waitFor();
}
async function openReport(page){
 await page.locator('#report-frame').waitFor();
 await page.frameLocator('#report-frame').locator('#total').filter({hasText:'NT$'}).waitFor();
 await page.frameLocator('#report-frame').locator('#frame-status').waitFor({state:'hidden'});
}
async function refreshReport(page){
 await page.locator('#settings-toggle').click();await page.locator('#refresh-profile').click();
}
module.exports={go,openCalculation,openReport,refreshReport};
