/* Runs only inside the current user's report frame; no token or private data is embedded in the HTML. */
(async function(){
 'use strict';
 try{
  const profile=window.parent!==window?window.parent.ReceiptV2Host?.profile():null;
  if(!profile)throw Error('請先登入，再從「我的品味」開啟月報。');
  window.expenseReportData=ReceiptViewData.reportData(profile);
  if(!Object.keys(expenseReportData.months).length)throw Error('尚未上傳發票，沒有可顯示的月份。');
  for(const source of ['legacy-flow-nav.js','report-insights.js','legacy-monthly.js','report-comparison.js']){
   await new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=source;script.onload=resolve;script.onerror=()=>reject(Error('月報載入失敗，請重新載入。'));document.body.append(script);});
  }
  document.getElementById('frame-status').hidden=true;
 }catch(error){const note=document.createElement('p');note.textContent=error.message;document.body.replaceChildren(note);}
})();
