/* Navigate through the same visible controls used by a person. */
async function go(page,name){
 await page.locator('#workspace-view').waitFor();
 const target=page.locator('[data-workspace="'+name+'"]');
 if(['upload','settings','classify'].includes(name)&&!(await target.isVisible()))await page.locator('#settings-toggle').click();
 await target.click();
}
async function openCalculation(page){
 await page.locator('#explain-details').waitFor();
 await page.locator('#explain-details > summary').click();
 await page.locator('#explain-panel').waitFor();
}
module.exports={go,openCalculation};
