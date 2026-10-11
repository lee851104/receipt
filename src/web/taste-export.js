(function(){
 'use strict';
 const get=id=>document.getElementById(id);
 const exportButton=get('export-taste');
 if(!exportButton)return;
 const panel=get('taste-export-panel'),output=get('taste-link'),notice=get('taste-export-status');
 // My taste traits come with the report build; a page opened without them exports the category counts alone.
 const exported=typeof tasteExportData==='undefined'?{traitCount:0,taste:null}:tasteExportData;
 // Every purchase name a friend will see, in signal order, each once.
 function sharedNames(taste){const names=[];for(const list of taste.items)for(const [name] of list||[])if(!names.includes(name))names.push(name);return names;}
 const taste=exported.taste,names=taste?sharedNames(taste):[],kinds=TasteProfile.categories.length+' 類消費筆數';
 const summaries='各消費訊號的彙總值（例如每餐平均花費、每月 3C 花費、每月次數）',never='店名、行政區、地址、日期、單筆金額或發票號碼';
 // The panel says only what this link holds: taste traits and summaries when the report has them, names when there are any.
 get('taste-export-about').textContent=(!taste?`連結包含暱稱、月份與 ${kinds}；不包含品味特質、品名、${never}。`
  :names.length?`連結包含暱稱、月份、${kinds}、${exported.traitCount} 項品味特質、${summaries}，以及每個訊號最常買的品名；不包含${never}。品名裡的地名會拿掉，住宿只寫「旅館住宿」。`
  :`連結包含暱稱、月份、${kinds}、${exported.traitCount} 項品味特質與${summaries}；不包含品名、${never}。`)+'拿到連結的人都讀得到這些內容；連結沒有加密。';
 function generate(){
  const profile=TasteProfile.fromReport(expenseReportData,get('taste-nickname').value,taste);
  output.value=TasteProfile.toURL(profile,location.href);
  get('taste-export-preview').textContent=`${profile.demo?'虛構示範':'這份報告'} · ${profile.months.join('、')} · ${profile.counts.reduce((a,b)=>a+b,0)} 筆已分類品項 · ${taste?exported.traitCount+' 項品味特質':'品味特質資料不足'}`;
  get('taste-export-names').textContent=!taste?'這份報告的資料還不夠算出品味特質，朋友只能看品項細節。':names.length?`朋友會看到這些品名（${names.length} 個）：${names.join('、')}`:'連結裡沒有品名。';
  get('taste-open-link').href=output.value;
  notice.textContent=location.protocol==='file:'?'這是本機連結。朋友可將完整連結貼進他的比較頁；若要直接點開，需先將這個檔案發布到網站。':'連結已產生，可複製給朋友；對方開啟後即可匯入比較。';
  return output.value;
 }
 function show(){panel.hidden=false;exportButton.setAttribute('aria-expanded','true');try{generate();}catch(error){notice.textContent=error.message;output.value='';get('taste-open-link').removeAttribute('href');} }
 exportButton.addEventListener('click',()=>{show();get('taste-nickname').focus();});
 get('taste-regenerate').addEventListener('click',show);
 get('taste-nickname').addEventListener('input',()=>{output.value='';get('taste-open-link').removeAttribute('href');notice.textContent='暱稱已變更，請按「更新連結」。';});
 get('taste-copy').addEventListener('click',async()=>{
  if(!output.value){notice.textContent='請先產生連結。';return;}
  try{await navigator.clipboard.writeText(output.value);notice.textContent='已複製完整連結，可貼到比較頁或傳給朋友。';}
  catch{output.focus();output.select();notice.textContent='已選取連結，請按 Ctrl+C（或長按複製）。';}
 });
})();
