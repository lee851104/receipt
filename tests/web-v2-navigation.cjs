/* Navigate through the same visible controls used by a person. */
async function go(page,name){
 await page.locator('#workspace-view').waitFor();
 if(await page.locator('#report-dialog').isVisible())await page.locator('#close-report').click();
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
 await page.locator('[data-profile-page="month-page"]').first().click();
 await page.locator('#open-report').click();
 await page.locator('#report-dialog').waitFor();
}
module.exports={go,openCalculation,openReport};
