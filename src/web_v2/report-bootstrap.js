/* Runs only inside the current user's report frame; no token or private data is embedded in the HTML. */
(async function(){
 'use strict';
 try{
  const profile=window.parent!==window?window.parent.ReceiptV2Host?.profile():null;
  if(!profile)throw Error('請先登入，再從「我的月報」查看報告。');
  window.expenseReportData=ReceiptViewData.reportData(profile);
  if(!Object.keys(expenseReportData.months).length)throw Error('尚未上傳發票，沒有可顯示的月份。');
  for(const source of ['report-overview.js','report-motion.js','report-paging.js','report-insights.js','legacy-monthly.js','report-comparison.js']){
   await new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=source+'?v=20261017-layout2';script.onload=resolve;script.onerror=()=>reject(Error('月報載入失敗，請重新載入。'));document.body.append(script);});
  }
  const requested=new URLSearchParams(location.search).get('month');
  const select=document.getElementById('insights-month');
  if(requested&&Object.hasOwn(expenseReportData.months,requested)){
   select.value=requested;select.dispatchEvent(new Event('change',{bubbles:true}));
  }
  document.getElementById('frame-status').hidden=true;
 }catch(error){const note=document.createElement('p');note.textContent=error.message;document.body.replaceChildren(note);}
})();
